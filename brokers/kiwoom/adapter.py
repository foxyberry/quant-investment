"""Kiwoom OpenAPI+ broker adapter.

Wraps :class:`api.services.kiwoom_service.KiwoomService` behind the
:class:`brokers.base.BrokerAdapter` ABC so that callers interact with a
vendor-agnostic interface.  ``KiwoomService`` code is **not** modified --
all translation between broker-specific dicts and canonical DTOs happens
here.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from api.services.kiwoom_service import KiwoomService
from brokers.base import (
    AmendRequest,
    BrokerAdapter,
    ConnectionState,
    ConnectionStatus,
    KillSwitchResult,
    OrderCallback,
    OrderEvent,
    OrderRequest,
    OrderSnapshot,
    OrderStatus,
)
from brokers.exceptions import (
    BrokerConnectionError,
    BrokerError,
    BrokerSafetyError,
    BrokerValidationError,
    OrderNotFoundError,
)
from kiwoom.safety import SafetyViolation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chejan status string -> canonical OrderStatus mapping
# ---------------------------------------------------------------------------

_CHEJAN_STATUS_MAP: Dict[str, OrderStatus] = {
    "CANCELLED": OrderStatus.CANCELED,
    "PLACED": OrderStatus.CONFIRMED,
    "PENDING": OrderStatus.RECEIVED,
}


def _resolve_order_status(raw: str) -> OrderStatus:
    """Map a chejan status string to the canonical :class:`OrderStatus`.

    Falls back to ``RECEIVED`` if the value is unrecognised.
    """
    if raw in _CHEJAN_STATUS_MAP:
        return _CHEJAN_STATUS_MAP[raw]
    try:
        return OrderStatus(raw)
    except ValueError:
        return OrderStatus.RECEIVED


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class KiwoomBrokerAdapter(BrokerAdapter):
    """Adapt :class:`KiwoomService` to the :class:`BrokerAdapter` interface.

    Instantiation obtains the ``KiwoomService`` singleton and subscribes to
    chejan (order execution) events so that registered callbacks receive
    :class:`OrderEvent` objects in real-time.
    """

    def __init__(self) -> None:
        self._service: KiwoomService = KiwoomService.get_instance()
        self._callbacks: List[OrderCallback] = []
        self._cb_lock: threading.RLock = threading.RLock()

        # Subscribe to the chejan handler's observer pipeline.
        self._service._chejan.add_observer(self._on_chejan_event)

    def close(self) -> None:
        """Unsubscribe from chejan events and release resources."""
        self._service._chejan.remove_observer(self._on_chejan_event)
        with self._cb_lock:
            self._callbacks.clear()

    # -- Properties --------------------------------------------------------

    @property
    def broker_name(self) -> str:  # noqa: D401
        """Return ``\"kiwoom\"``."""
        return "kiwoom"

    @property
    def supported_markets(self) -> List[str]:
        """Return ``[\"KRX\"]``."""
        return ["KRX"]

    # -- Connection --------------------------------------------------------

    def get_connection_status(self) -> ConnectionStatus:
        """Query the underlying service and return a canonical DTO."""
        raw: Dict[str, Any] = self._service.get_connection_status()

        return ConnectionStatus(
            status=ConnectionState(raw["status"]),
            is_paper_trading=raw.get("is_mock_trading"),
            broker="kiwoom",
            user_id=raw.get("user_id"),
            accounts=raw.get("accounts", []),
            updated_at=raw.get("updated_at"),
        )

    # -- Orders ------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderSnapshot:
        """Place a new order via ``KiwoomService`` and return a snapshot."""
        try:
            raw: Dict[str, Any] = self._service.place_order(
                ticker=request.ticker,
                side=request.side.value,
                quantity=request.quantity,
                order_type=request.order_type.value,
                price=request.price,
            )
        except ValueError as exc:
            raise BrokerValidationError(str(exc)) from exc
        except SafetyViolation as exc:
            raise BrokerSafetyError(str(exc)) from exc
        except RuntimeError as exc:
            if "no accounts" in str(exc).lower():
                raise BrokerConnectionError(str(exc)) from exc
            raise BrokerError(str(exc)) from exc

        return self._raw_order_to_snapshot(raw)

    def get_orders(self) -> List[OrderSnapshot]:
        """Return all tracked orders as canonical snapshots."""
        raw_list: List[Dict[str, Any]] = self._service.get_orders()
        return [self._raw_order_to_snapshot(r) for r in raw_list]

    def cancel_order(self, order_id: str) -> None:
        """Cancel an open order by its ID."""
        try:
            self._service.cancel_order(order_id)
        except KeyError as exc:
            raise OrderNotFoundError(str(exc)) from exc
        except SafetyViolation as exc:
            raise BrokerSafetyError(str(exc)) from exc
        except RuntimeError as exc:
            raise BrokerError(str(exc)) from exc

    def amend_order(self, order_id: str, request: AmendRequest) -> None:
        """Amend (modify) an open order."""
        try:
            self._service.amend_order(
                order_id=order_id,
                quantity=request.quantity,
                price=request.price,
            )
        except KeyError as exc:
            raise OrderNotFoundError(str(exc)) from exc
        except ValueError as exc:
            raise BrokerValidationError(str(exc)) from exc
        except SafetyViolation as exc:
            raise BrokerSafetyError(str(exc)) from exc
        except RuntimeError as exc:
            raise BrokerError(str(exc)) from exc

    # -- Kill switch -------------------------------------------------------

    def activate_kill_switch(self) -> KillSwitchResult:
        """Activate the emergency kill switch."""
        raw: Dict[str, Any] = self._service.activate_kill_switch()
        return KillSwitchResult(
            activated=raw["activated"],
            cancelled_orders=raw["cancelled_orders"],
        )

    # -- Subscriptions -----------------------------------------------------

    def subscribe_orders(self, callback: OrderCallback) -> None:
        """Register a callback for real-time order events."""
        with self._cb_lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unsubscribe_orders(self, callback: OrderCallback) -> None:
        """Remove a previously registered callback."""
        with self._cb_lock:
            try:
                self._callbacks.remove(callback)
            except ValueError:
                pass

    # -- Internal helpers --------------------------------------------------

    def _on_chejan_event(self, payload: Dict[str, Any]) -> None:
        """Observer callback invoked by the chejan handler.

        Translates the raw chejan dict into an :class:`OrderEvent` and
        dispatches to all registered callbacks.  Non-order events and
        events lacking an ``order_no`` are silently ignored.
        """
        if payload.get("type") != "order":
            return

        order_no: Optional[str] = payload.get("order_no")
        if not order_no:
            return

        status = _resolve_order_status(payload.get("status", ""))

        event = OrderEvent(
            order_id=order_no,
            ticker=payload.get("code", ""),
            status=status,
            filled_quantity=payload.get("filled_qty", 0),
            unfilled_quantity=payload.get("unfilled_qty", 0),
            filled_price=self._safe_float(payload.get("fill_price")),
            broker="kiwoom",
        )

        with self._cb_lock:
            callbacks = list(self._callbacks)

        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                logger.exception(
                    "Order callback raised for order_id=%s", order_no
                )

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Convert *value* to float, returning ``None`` on failure."""
        if not value:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _raw_order_to_snapshot(raw: Dict[str, Any]) -> OrderSnapshot:
        """Convert a dict returned by ``KiwoomService`` to an ``OrderSnapshot``."""
        return OrderSnapshot(
            order_id=raw["order_id"],
            ticker=raw["ticker"],
            side=raw["side"],
            quantity=raw["quantity"],
            filled_quantity=raw.get("filled_quantity", 0),
            unfilled_quantity=raw.get("unfilled_quantity", 0),
            order_type=raw["order_type"],
            price=raw.get("price"),
            filled_price=raw.get("filled_price"),
            status=raw["status"],
            created_at=raw["created_at"],
            updated_at=raw.get("updated_at"),
            broker="kiwoom",
        )
