"""Tiger Brokers adapter.

Implements :class:`brokers.base.BrokerAdapter` for Tiger Brokers via
the ``tigeropen`` Python SDK (TradeClient for REST, PushClient for streaming).
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, List, Optional

from brokers.base import (
    AmendRequest,
    BrokerAdapter,
    ConnectionState,
    ConnectionStatus,
    KillSwitchResult,
    OrderCallback,
    OrderRequest,
    OrderSide,
    OrderSnapshot,
    OrderStatus,
    OrderType,
)
from brokers.exceptions import (
    BrokerConnectionError,
    BrokerSafetyError,
    BrokerValidationError,
    OrderNotFoundError,
)
from brokers.tiger.constants import (
    DEFAULT_CURRENCY,
    MARKET_CURRENCY,
    ORDER_TYPE_TO_TIGER,
    SUPPORTED_MARKETS,
    TIGER_STATUS_MAP,
    TIGER_TO_ORDER_TYPE,
)
from brokers.tiger.session import TigerSession
from brokers.tiger.stream import TigerOrderStream

logger = logging.getLogger(__name__)

# Lazy SDK imports for graceful degradation
try:
    from tigeropen.common.util.contract_utils import stock_contract
    from tigeropen.common.util.order_utils import limit_order, market_order
    from tigeropen.trade.domain.order import Order

    _SDK_UTILS_AVAILABLE = True
except ImportError:
    stock_contract = None  # type: ignore[assignment]
    limit_order = None  # type: ignore[assignment]
    market_order = None  # type: ignore[assignment]
    Order = None  # type: ignore[assignment]
    _SDK_UTILS_AVAILABLE = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TigerBrokerAdapter(BrokerAdapter):
    """Adapt Tiger Brokers to the BrokerAdapter interface.

    Environment Variables
    ---------------------
    TIGER_ID:
        Tiger developer ID (required).
    TIGER_PRIVATE_KEY:
        Path to RSA private key PEM file (required).
    TIGER_ACCOUNT:
        Account number (required).
    TIGER_LICENSE:
        License type (default ``"TBNZ"``).
    """

    def __init__(self) -> None:
        # Kill switch
        self._kill_switch_active = False
        self._kill_lock = threading.RLock()

        # Sub-components
        try:
            self._session = TigerSession()
            account = os.environ.get("TIGER_ACCOUNT", "")
            self._stream = TigerOrderStream(self._session.config, account)
            self._available = True
        except Exception:
            logger.warning(
                "Tiger Brokers not available; adapter in UNAVAILABLE state",
                exc_info=True,
            )
            self._session = None  # type: ignore[assignment]
            self._stream = None  # type: ignore[assignment]
            self._available = False

    def close(self) -> None:
        """Release resources."""
        if self._stream:
            self._stream.stop()

    # -- identity -----------------------------------------------------------

    @property
    def broker_name(self) -> str:  # noqa: D401
        return "tiger"

    @property
    def supported_markets(self) -> List[str]:
        return list(SUPPORTED_MARKETS)

    # -- connection ---------------------------------------------------------

    def get_connection_status(self) -> ConnectionStatus:
        if not self._available:
            return ConnectionStatus(
                broker="tiger",
                status=ConnectionState.UNAVAILABLE,
                updated_at=_now_iso(),
            )

        try:
            self._session.check_connection()
            state = ConnectionState.CONNECTED
        except BrokerConnectionError:
            return ConnectionStatus(
                broker="tiger",
                status=ConnectionState.DISCONNECTED,
                updated_at=_now_iso(),
            )

        # Discover accounts
        accounts: list[str] = []
        is_paper: Optional[bool] = None
        try:
            acct_list = self._session.get_accounts()
            accounts = [a["account_id"] for a in acct_list]
            is_paper = any(a["is_paper"] for a in acct_list) if acct_list else None
        except Exception:
            logger.debug("Tiger account discovery failed", exc_info=True)

        return ConnectionStatus(
            broker="tiger",
            status=state,
            is_paper_trading=is_paper,
            accounts=accounts,
            updated_at=_now_iso(),
        )

    # -- order lifecycle ----------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderSnapshot:
        self._ensure_available()
        self._check_kill_switch()

        if not _SDK_UTILS_AVAILABLE:
            raise BrokerConnectionError("tigeropen SDK is not installed")

        currency = self._resolve_currency(request.ticker)
        contract = stock_contract(symbol=request.ticker, currency=currency)

        account = request.account_id or os.environ.get("TIGER_ACCOUNT", "")

        if request.order_type == OrderType.LIMIT:
            if request.price is None:
                raise BrokerValidationError("price is required for LIMIT orders")
            order = limit_order(
                account=account,
                contract=contract,
                action="BUY" if request.side == OrderSide.BUY else "SELL",
                limit_price=request.price,
                quantity=request.quantity,
            )
        else:
            order = market_order(
                account=account,
                contract=contract,
                action="BUY" if request.side == OrderSide.BUY else "SELL",
                quantity=request.quantity,
            )

        try:
            self._session.client.place_order(order)
        except BrokerConnectionError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if any(kw in error_msg for kw in ("timeout", "connection", "network", "socket")):
                raise BrokerConnectionError(
                    f"Tiger order failed (network): {exc}"
                ) from exc
            raise BrokerValidationError(
                f"Tiger order rejected: {exc}"
            ) from exc

        order_id = str(getattr(order, "id", "") or getattr(order, "order_id", "") or "PENDING")

        return OrderSnapshot(
            order_id=order_id,
            broker="tiger",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            price=request.price,
            status=OrderStatus.RECEIVED,
            created_at=_now_iso(),
        )

    def get_orders(self) -> List[OrderSnapshot]:
        self._ensure_available()

        try:
            orders = self._session.client.get_orders()
        except Exception as exc:
            raise BrokerConnectionError(
                f"Failed to fetch Tiger orders: {exc}"
            ) from exc

        if not orders:
            return []

        result: list[OrderSnapshot] = []
        for order in orders:
            try:
                result.append(self._order_to_snapshot(order))
            except Exception:
                logger.debug("Skipping unparsable Tiger order: %s", order, exc_info=True)

        return result

    def cancel_order(self, order_id: str) -> None:
        self._ensure_available()

        try:
            self._session.client.cancel_order(id=int(order_id))
        except (ValueError, TypeError) as exc:
            raise OrderNotFoundError(
                f"Invalid order ID: {order_id}"
            ) from exc
        except Exception as exc:
            error_msg = str(exc).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise OrderNotFoundError(
                    f"Order {order_id} not found"
                ) from exc
            raise BrokerConnectionError(
                f"Failed to cancel Tiger order: {exc}"
            ) from exc

    def amend_order(self, order_id: str, request: AmendRequest) -> None:
        self._ensure_available()
        self._check_kill_switch()

        try:
            order_int_id = int(order_id)
        except (ValueError, TypeError) as exc:
            raise OrderNotFoundError(
                f"Invalid order ID: {order_id}"
            ) from exc

        if not _SDK_UTILS_AVAILABLE:
            raise BrokerConnectionError("tigeropen SDK is not installed")

        try:
            order = Order()
            order.id = order_int_id
            if request.quantity is not None:
                order.quantity = request.quantity
            if request.price is not None:
                order.limit_price = request.price

            self._session.client.modify_order(order)
        except (BrokerConnectionError, OrderNotFoundError):
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise OrderNotFoundError(
                    f"Order {order_id} not found"
                ) from exc
            if any(kw in error_msg for kw in ("timeout", "connection", "network", "socket")):
                raise BrokerConnectionError(
                    f"Tiger amend failed (network): {exc}"
                ) from exc
            raise BrokerValidationError(
                f"Failed to amend Tiger order: {exc}"
            ) from exc

    # -- emergency ----------------------------------------------------------

    def activate_kill_switch(self) -> KillSwitchResult:
        self._ensure_available()

        with self._kill_lock:
            self._kill_switch_active = True

        cancelled = 0
        try:
            orders = self.get_orders()
            open_statuses = {OrderStatus.RECEIVED, OrderStatus.CONFIRMED, OrderStatus.PARTIAL}
            for order in orders:
                if order.status in open_statuses:
                    try:
                        self.cancel_order(order.order_id)
                        cancelled += 1
                    except Exception:
                        logger.warning(
                            "Failed to cancel order %s during kill switch",
                            order.order_id,
                            exc_info=True,
                        )
        except Exception:
            logger.warning("Failed to fetch orders during kill switch", exc_info=True)

        logger.warning("Tiger kill switch activated, cancelled %d orders", cancelled)
        return KillSwitchResult(activated=True, cancelled_orders=cancelled)

    # -- subscriptions ------------------------------------------------------

    def subscribe_orders(self, callback: OrderCallback) -> None:
        self._ensure_available()
        self._stream.add_callback(callback)
        self._stream.start()

    def unsubscribe_orders(self, callback: OrderCallback) -> None:
        if self._stream:
            self._stream.remove_callback(callback)

    # -- internal helpers ---------------------------------------------------

    def _ensure_available(self) -> None:
        if not self._available:
            raise BrokerConnectionError("Tiger Brokers not available")

    def _check_kill_switch(self) -> None:
        with self._kill_lock:
            if self._kill_switch_active:
                raise BrokerSafetyError(
                    "Kill switch is active; new orders are blocked"
                )

    @staticmethod
    def _resolve_currency(ticker: str) -> str:
        """Infer currency from ticker suffix convention.

        HK-listed tickers typically end with ``.HK`` (e.g. ``0700.HK``),
        SG-listed tickers end with ``.SI``.  Everything else defaults to USD.
        """
        upper = ticker.upper()
        if upper.endswith(".HK"):
            return MARKET_CURRENCY["HK"]
        if upper.endswith(".SI"):
            return MARKET_CURRENCY["SG"]
        return DEFAULT_CURRENCY

    def _order_to_snapshot(self, order: Any) -> OrderSnapshot:
        """Convert a Tiger SDK Order object to an ``OrderSnapshot``."""
        order_id = str(
            getattr(order, "id", "") or getattr(order, "order_id", "") or ""
        )

        # Ticker
        contract = getattr(order, "contract", None)
        ticker = ""
        if contract:
            ticker = str(getattr(contract, "symbol", "") or "")
        if not ticker:
            ticker = str(getattr(order, "symbol", "") or "")

        # Side
        raw_action = str(getattr(order, "action", "") or "").upper()
        if raw_action in ("BUY", "B"):
            side = OrderSide.BUY
        elif raw_action in ("SELL", "S"):
            side = OrderSide.SELL
        else:
            logger.warning("Unknown Tiger order action '%s', defaulting to BUY", raw_action)
            side = OrderSide.BUY

        # Quantities
        quantity = self._safe_int(getattr(order, "quantity", 0))
        filled_qty = self._safe_int(getattr(order, "filled", 0))
        remaining = self._safe_int(getattr(order, "remaining", quantity - filled_qty))

        # Order type
        raw_order_type = str(getattr(order, "order_type", "MKT") or "MKT")
        order_type = TIGER_TO_ORDER_TYPE.get(raw_order_type, OrderType.MARKET)

        # Prices
        limit_price = self._safe_float(getattr(order, "limit_price", None))
        filled_price = self._safe_float(getattr(order, "avg_fill_price", None))

        # Status
        raw_status = str(getattr(order, "status", "") or "")
        status = TIGER_STATUS_MAP.get(raw_status, OrderStatus.RECEIVED)

        return OrderSnapshot(
            order_id=order_id,
            broker="tiger",
            ticker=ticker,
            side=side,
            quantity=quantity,
            filled_quantity=filled_qty,
            unfilled_quantity=remaining,
            order_type=order_type,
            price=limit_price,
            filled_price=filled_price,
            status=status,
            created_at=_now_iso(),
        )

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
