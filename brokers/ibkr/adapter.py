"""IBKR Client Portal broker adapter.

Implements :class:`brokers.base.BrokerAdapter` for Interactive Brokers via
the Client Portal Gateway REST API and WebSocket streaming.
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
from brokers.ibkr.client import IBKRClient
from brokers.ibkr.constants import (
    DEFAULT_GATEWAY_URL,
    IBKR_STATUS_MAP,
    IBKR_TO_ORDER_TYPE,
    MAX_CONFIRM_ROUNDS,
    ORDER_TYPE_TO_IBKR,
    DEFAULT_TIF,
)
from brokers.ibkr.contract_cache import ContractCache
from brokers.ibkr.session import IBKRSessionManager
from brokers.ibkr.stream import IBKROrderStream

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IBKRBrokerAdapter(BrokerAdapter):
    """Adapt the IBKR Client Portal Gateway to the BrokerAdapter interface.

    Environment Variables
    ---------------------
    IBKR_GATEWAY_URL:
        Gateway base URL (default ``https://localhost:5000``).
    IBKR_ACCOUNT_ID:
        Default account ID. If not set, the first discovered account is used.
    """

    def __init__(self) -> None:
        self._gateway_url = os.environ.get("IBKR_GATEWAY_URL", DEFAULT_GATEWAY_URL)
        self._account_id: Optional[str] = os.environ.get("IBKR_ACCOUNT_ID")

        # Kill switch
        self._kill_switch_active = False
        self._kill_lock = threading.RLock()

        # Sub-components
        try:
            self._client = IBKRClient(self._gateway_url)
            self._session = IBKRSessionManager(self._client)
            self._cache = ContractCache(self._client)
            self._stream = IBKROrderStream(self._gateway_url)
            self._available = True
        except Exception:
            logger.warning(
                "IBKR gateway not available at %s; adapter in UNAVAILABLE state",
                self._gateway_url,
                exc_info=True,
            )
            self._client = None  # type: ignore[assignment]
            self._session = None  # type: ignore[assignment]
            self._cache = None  # type: ignore[assignment]
            self._stream = None  # type: ignore[assignment]
            self._available = False

    def close(self) -> None:
        """Release resources."""
        if self._stream:
            self._stream.stop()
        if self._session:
            self._session.stop_keepalive()
        if self._client:
            self._client.close()

    # -- identity -----------------------------------------------------------

    @property
    def broker_name(self) -> str:  # noqa: D401
        return "ibkr"

    @property
    def supported_markets(self) -> List[str]:
        return ["US"]

    # -- connection ---------------------------------------------------------

    def get_connection_status(self) -> ConnectionStatus:
        if not self._available:
            return ConnectionStatus(
                broker="ibkr",
                status=ConnectionState.UNAVAILABLE,
                updated_at=_now_iso(),
            )

        try:
            auth = self._session.check_auth_status()
        except BrokerConnectionError:
            return ConnectionStatus(
                broker="ibkr",
                status=ConnectionState.DISCONNECTED,
                updated_at=_now_iso(),
            )

        if self._session.is_disconnected:
            state = ConnectionState.DISCONNECTED
        elif auth.get("authenticated") and auth.get("connected"):
            state = ConnectionState.CONNECTED
        else:
            state = ConnectionState.DISCONNECTED

        # Discover accounts
        accounts: list[str] = []
        is_paper: Optional[bool] = None
        try:
            acct_list = self._session.discover_accounts()
            accounts = [a["account_id"] for a in acct_list]
            is_paper = any(a["is_paper"] for a in acct_list) if acct_list else None
        except Exception:
            logger.debug("Account discovery failed", exc_info=True)

        return ConnectionStatus(
            broker="ibkr",
            status=state,
            is_paper_trading=is_paper,
            accounts=accounts,
            updated_at=_now_iso(),
        )

    # -- order lifecycle ----------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderSnapshot:
        self._ensure_available()
        self._check_kill_switch()

        account_id = request.account_id or self._resolve_account()
        conid = self._cache.resolve(request.ticker)

        order_payload = {
            "acctId": account_id,
            "conid": conid,
            "orderType": ORDER_TYPE_TO_IBKR[request.order_type],
            "side": request.side.value,
            "quantity": request.quantity,
            "tif": DEFAULT_TIF,
        }
        if request.order_type == OrderType.LIMIT and request.price is not None:
            order_payload["price"] = request.price

        body = {"orders": [order_payload]}
        data = self._client.post(f"/iserver/account/{account_id}/orders", json=body)

        # Handle confirmation flow
        data = self._handle_order_confirmation(data)

        # Parse the response
        return self._parse_place_order_response(data, request)

    def get_orders(self) -> List[OrderSnapshot]:
        self._ensure_available()

        data = self._client.get("/iserver/account/orders")

        if not isinstance(data, dict):
            return []

        orders_raw = data.get("orders", [])
        result: list[OrderSnapshot] = []

        for raw in orders_raw:
            try:
                result.append(self._raw_to_snapshot(raw))
            except Exception:
                logger.debug("Skipping unparsable order: %s", raw, exc_info=True)

        return result

    def cancel_order(self, order_id: str) -> None:
        self._ensure_available()
        account_id = self._resolve_account()

        data = self._client.delete(
            f"/iserver/account/{account_id}/order/{order_id}"
        )

        if isinstance(data, dict) and data.get("error"):
            error_msg = data["error"]
            if "not found" in str(error_msg).lower():
                raise OrderNotFoundError(f"Order {order_id} not found")
            raise BrokerConnectionError(f"Cancel failed: {error_msg}")

    def amend_order(self, order_id: str, request: AmendRequest) -> None:
        self._ensure_available()
        self._check_kill_switch()
        account_id = self._resolve_account()

        # Build the amendment payload from current order + requested changes
        modify_payload: dict[str, Any] = {}
        if request.quantity is not None:
            modify_payload["quantity"] = request.quantity
        if request.price is not None:
            modify_payload["price"] = request.price

        if not modify_payload:
            raise BrokerValidationError("No fields to amend")

        data = self._client.post(
            f"/iserver/account/{account_id}/order/{order_id}",
            json=modify_payload,
        )

        # Handle confirmation flow (amendments can also trigger warnings)
        data = self._handle_order_confirmation(data)

        if isinstance(data, dict) and data.get("error"):
            error_msg = data["error"]
            if "not found" in str(error_msg).lower():
                raise OrderNotFoundError(f"Order {order_id} not found")
            raise BrokerValidationError(f"Amend failed: {error_msg}")

    # -- emergency ----------------------------------------------------------

    def activate_kill_switch(self) -> KillSwitchResult:
        self._ensure_available()

        with self._kill_lock:
            self._kill_switch_active = True

        # Cancel all open orders
        cancelled = 0
        try:
            orders = self.get_orders()
            open_statuses = {OrderStatus.RECEIVED, OrderStatus.CONFIRMED}
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

        logger.warning("IBKR kill switch activated, cancelled %d orders", cancelled)
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
            raise BrokerConnectionError(
                f"IBKR gateway not available at {self._gateway_url}"
            )

    def _check_kill_switch(self) -> None:
        with self._kill_lock:
            if self._kill_switch_active:
                raise BrokerSafetyError(
                    "Kill switch is active; new orders are blocked"
                )

    def _resolve_account(self) -> str:
        """Return the configured or first discovered account ID."""
        if self._account_id:
            return self._account_id

        accounts = self._session.discover_accounts()
        if not accounts:
            raise BrokerConnectionError("No IBKR accounts discovered")

        acct = accounts[0]["account_id"]
        self._account_id = acct
        return acct

    def _handle_order_confirmation(self, data: Any) -> Any:
        """Handle IBKR's order confirmation/warning flow.

        When IBKR returns a response with ``id`` (messageId), it requires
        confirmation via ``POST /iserver/reply/{id}``.  This can repeat
        up to ``MAX_CONFIRM_ROUNDS`` times.
        """
        for _ in range(MAX_CONFIRM_ROUNDS):
            if not isinstance(data, list):
                return data

            # Check if any item needs confirmation
            needs_confirm = False
            for item in data:
                if isinstance(item, dict) and "id" in item:
                    message_id = item["id"]
                    logger.info(
                        "IBKR order confirmation required (id=%s): %s",
                        message_id,
                        item.get("message", ""),
                    )
                    data = self._client.post(
                        f"/iserver/reply/{message_id}",
                        json={"confirmed": True},
                    )
                    needs_confirm = True
                    break

            if not needs_confirm:
                return data

        return data

    def _parse_place_order_response(
        self, data: Any, request: OrderRequest
    ) -> OrderSnapshot:
        """Parse the gateway response after placing an order."""
        # Successful placement returns a list with order_id
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                order_id = str(first.get("order_id", first.get("orderId", "")))
                status_str = first.get("order_status", "")
                status = IBKR_STATUS_MAP.get(status_str, OrderStatus.RECEIVED)

                return OrderSnapshot(
                    order_id=order_id or "PENDING",
                    broker="ibkr",
                    ticker=request.ticker,
                    side=request.side,
                    quantity=request.quantity,
                    order_type=request.order_type,
                    price=request.price,
                    status=status,
                    created_at=_now_iso(),
                )

        # Dict response (some gateway versions)
        if isinstance(data, dict):
            order_id = str(data.get("order_id", data.get("orderId", "PENDING")))
            status_str = data.get("order_status", "")
            status = IBKR_STATUS_MAP.get(status_str, OrderStatus.RECEIVED)

            if data.get("error"):
                raise BrokerValidationError(
                    f"Order rejected: {data['error']}"
                )

            return OrderSnapshot(
                order_id=order_id,
                broker="ibkr",
                ticker=request.ticker,
                side=request.side,
                quantity=request.quantity,
                order_type=request.order_type,
                price=request.price,
                status=status,
                created_at=_now_iso(),
            )

        raise BrokerValidationError(
            f"Unexpected order response: {data!r}"
        )

    @staticmethod
    def _raw_to_snapshot(raw: dict[str, Any]) -> OrderSnapshot:
        """Convert an IBKR order dict to an ``OrderSnapshot``."""
        raw_status = raw.get("status", raw.get("orderStatus", ""))
        status = IBKR_STATUS_MAP.get(raw_status, OrderStatus.RECEIVED)

        raw_side = raw.get("side", "").upper()
        if raw_side in ("BUY", "B"):
            side = OrderSide.BUY
        elif raw_side in ("SELL", "S"):
            side = OrderSide.SELL
        else:
            logger.warning("Unknown order side '%s', defaulting to BUY", raw_side)
            side = OrderSide.BUY

        raw_type = raw.get("orderType", "MKT")
        order_type = IBKR_TO_ORDER_TYPE.get(raw_type, OrderType.MARKET)

        filled_qty = int(raw.get("filledQuantity", raw.get("filled_quantity", 0)))
        total_qty = int(raw.get("totalSize", raw.get("quantity", 0)))
        remaining = int(raw.get("remainingQuantity", raw.get("unfilled_quantity", total_qty - filled_qty)))

        filled_price: Optional[float] = None
        raw_price = raw.get("avgPrice", raw.get("filled_price"))
        if raw_price is not None:
            try:
                filled_price = float(raw_price)
            except (TypeError, ValueError):
                pass

        limit_price: Optional[float] = None
        raw_limit = raw.get("price", raw.get("auxPrice"))
        if raw_limit is not None:
            try:
                limit_price = float(raw_limit)
            except (TypeError, ValueError):
                pass

        return OrderSnapshot(
            order_id=str(raw.get("orderId", raw.get("order_id", ""))),
            broker="ibkr",
            ticker=raw.get("ticker", raw.get("symbol", "")),
            side=side,
            quantity=total_qty,
            filled_quantity=filled_qty,
            unfilled_quantity=remaining,
            order_type=order_type,
            price=limit_price,
            filled_price=filled_price,
            status=status,
            created_at=raw.get("created_at", _now_iso()),
            updated_at=raw.get("lastExecutionTime"),
        )
