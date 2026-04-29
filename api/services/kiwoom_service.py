"""
Kiwoom trading service layer.

Wraps the ``kiwoom`` module components (connection, orders, conditions,
safety) behind a singleton service that the API router consumes.
On non-Windows platforms the service automatically operates in mock mode.
"""

from __future__ import annotations

import collections
import logging
import platform
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from brokers.kiwoom.chejan_handler import ChejanHandler
from brokers.kiwoom.condition_search import ConditionSearchManager
from brokers.kiwoom.connection import KiwoomConnection
from brokers.kiwoom.constants import HogaType, OrderType
from brokers.kiwoom.order import KiwoomOrderManager
from brokers.kiwoom.safety import AuditLogger, KiwoomSafetyManager, SafetyViolation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal status mapping helpers
# ---------------------------------------------------------------------------

_KIWOOM_STATUS_TO_API: Dict[str, str] = {
    "queued": "RECEIVED",
    "sent": "RECEIVED",
    "accepted": "CONFIRMED",
    "placed": "CONFIRMED",
    "confirmed": "CONFIRMED",
    "partial": "PARTIAL",
    "filled": "FILLED",
    "cancelled": "CANCELED",
    "rejected": "REJECTED",
}

_ORDER_TYPE_IS_BUY = {
    int(OrderType.NEW_BUY),
    int(OrderType.CANCEL_BUY),
    int(OrderType.MODIFY_BUY),
}


def _iso_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _epoch_to_iso(epoch: Optional[float]) -> Optional[str]:
    """Convert epoch timestamp to ISO 8601 string, or None."""
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class KiwoomService:
    """Singleton-like service managing Kiwoom components lifecycle.

    Call ``get_instance()`` to obtain the shared service object.  The first
    call initialises the Kiwoom connection (mock mode on non-Windows) and
    wires all sub-components together.
    """

    _instance: Optional[KiwoomService] = None

    def __init__(self) -> None:
        logger.info("Initialising KiwoomService ...")

        # Connection (mock on non-Windows, real on Windows)
        is_windows = platform.system() == "Windows"
        self._connection = KiwoomConnection(mock=not is_windows)
        try:
            self._connection.login()
        except Exception:
            logger.error("KiwoomService login failed", exc_info=True)
            raise

        # Safety layer
        self._safety = KiwoomSafetyManager(
            audit_logger=AuditLogger(),
            allow_live_trading=False,
        )

        # Order management
        self._order_manager = KiwoomOrderManager(
            ocx=self._connection.ocx,
            connection=self._connection,
            safety_manager=self._safety,
        )

        # Wire cancel_open_orders for kill switch
        self._safety.kill_switch._cancel_open_orders_fn = (
            self._order_manager.cancel_open_orders
        )

        # Chejan handler (order confirmations / balance updates)
        self._chejan = ChejanHandler(
            ocx=self._connection.ocx,
            order_manager=self._order_manager,
            safety_manager=self._safety,
        )

        # Condition search
        self._condition_manager = ConditionSearchManager(
            ocx=self._connection.ocx,
        )

        # Event store for WebSocket broadcasting (bounded to prevent leak)
        self._chejan_events: collections.deque[Dict[str, Any]] = collections.deque(
            maxlen=500
        )
        self._chejan.add_observer(self._on_chejan_event)

        self._started_at = _iso_now()
        logger.info("KiwoomService initialised (mock=%s)", self._connection._mock)

    # -- Singleton accessor ---------------------------------------------------

    @classmethod
    def get_instance(cls) -> KiwoomService:
        """Return the shared KiwoomService singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -- Connection -----------------------------------------------------------

    def get_connection_status(self) -> Dict[str, Any]:
        """Return current connection status matching frontend schema."""
        connected = self._connection.is_connected()
        if connected:
            status = "connected"
            is_mock = self._connection.is_mock_trading()
            user_id = self._connection.get_login_info("USER_ID") or None
            accounts = self._connection.get_account_list()
        else:
            status = "disconnected"
            is_mock = None
            user_id = None
            accounts = []

        return {
            "status": status,
            "is_mock_trading": is_mock,
            "user_id": user_id,
            "accounts": accounts,
            "updated_at": _iso_now(),
        }

    # -- Orders ---------------------------------------------------------------

    def place_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        order_type: str,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place a new order and return the created order dict.

        Parameters
        ----------
        ticker : str
            Stock code (e.g. ``"005930"``).
        side : str
            ``"BUY"`` or ``"SELL"``.
        quantity : int
            Positive integer quantity.
        order_type : str
            ``"MARKET"`` or ``"LIMIT"``.
        price : float or None
            Required for LIMIT orders.  Ignored for MARKET.

        Returns
        -------
        dict
            Order snapshot matching the ``KiwoomOrder`` schema.

        Raises
        ------
        ValueError
            If inputs are invalid (e.g. LIMIT without price).
        RuntimeError
            If order sending fails or times out.
        SafetyViolation
            If blocked by kill switch, duplicate guard, or risk rule.
        """
        # Map frontend enums to Kiwoom constants
        if side == "BUY":
            kiwoom_order_type = int(OrderType.NEW_BUY)
        else:
            kiwoom_order_type = int(OrderType.NEW_SELL)

        if order_type == "MARKET":
            hoga = HogaType.MARKET.value
            kiwoom_price = 0
        else:
            hoga = HogaType.LIMIT.value
            if price is None or price <= 0:
                raise ValueError("price is required for LIMIT orders")
            kiwoom_price = int(price)

        accounts = self._connection.get_account_list()
        if not accounts:
            raise RuntimeError("no accounts available")
        acc_no = accounts[0]

        order_no = self._order_manager.send_order(
            rq_name=f"api_{side.lower()}_{ticker}",
            screen_no="2000",
            acc_no=acc_no,
            order_type=kiwoom_order_type,
            code=ticker,
            qty=quantity,
            price=kiwoom_price,
            hoga_type=hoga,
            org_order_no="",
        )

        return self._order_to_dict(order_no)

    def get_orders(self) -> List[Dict[str, Any]]:
        """Return all tracked orders as a list of dicts."""
        result: List[Dict[str, Any]] = []
        for order_no in list(self._order_manager.order_history.keys()):
            try:
                result.append(self._order_to_dict(order_no))
            except KeyError:
                continue
        return result

    def cancel_order(self, order_id: str) -> None:
        """Cancel an open order by its order ID.

        Raises
        ------
        KeyError
            If the order is not found.
        RuntimeError
            If cancel sending fails.
        """
        order = self._order_manager.order_history.get(order_id)
        if order is None:
            raise KeyError(f"order not found: {order_id}")

        if order.order_type in _ORDER_TYPE_IS_BUY:
            cancel_type = int(OrderType.CANCEL_BUY)
        else:
            cancel_type = int(OrderType.CANCEL_SELL)

        self._order_manager.send_order(
            rq_name=f"api_cancel_{order_id}",
            screen_no=order.screen_no,
            acc_no=order.acc_no,
            order_type=cancel_type,
            code=order.code,
            qty=order.qty,
            price=0,
            hoga_type=HogaType.LIMIT.value,
            org_order_no=order_id,
        )

    def amend_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
    ) -> None:
        """Amend (modify) an open order.

        Raises
        ------
        KeyError
            If the order is not found.
        ValueError
            If neither quantity nor price is provided.
        RuntimeError
            If amend sending fails.
        """
        order = self._order_manager.order_history.get(order_id)
        if order is None:
            raise KeyError(f"order not found: {order_id}")

        if quantity is None and price is None:
            raise ValueError("at least one of quantity or price must be provided")

        if order.order_type in _ORDER_TYPE_IS_BUY:
            modify_type = int(OrderType.MODIFY_BUY)
        else:
            modify_type = int(OrderType.MODIFY_SELL)

        new_qty = quantity if quantity is not None else order.qty
        new_price = int(price) if price is not None else order.price

        self._order_manager.send_order(
            rq_name=f"api_amend_{order_id}",
            screen_no=order.screen_no,
            acc_no=order.acc_no,
            order_type=modify_type,
            code=order.code,
            qty=new_qty,
            price=new_price,
            hoga_type=order.hoga_type,
            org_order_no=order_id,
        )

    def activate_kill_switch(self) -> Dict[str, Any]:
        """Activate the emergency kill switch.

        Returns
        -------
        dict
            ``{"activated": bool, "cancelled_orders": int}``
        """
        cancelled = self._safety.activate_kill_switch("manual")
        return {
            "activated": True,
            "cancelled_orders": cancelled,
        }

    # -- Conditions -----------------------------------------------------------

    def get_conditions(self) -> List[Dict[str, Any]]:
        """Return the list of available conditions."""
        definitions = self._condition_manager.get_condition_list()
        return [{"index": d.index, "name": d.name} for d in definitions]

    def start_condition(self, index: int, name: str) -> Dict[str, Any]:
        """Start realtime monitoring for a condition.

        Returns
        -------
        dict
            ``{"condition_index": int, "condition_name": str, "screen_no": str}``
        """
        screen_no = self._condition_manager.start_monitoring(
            condition_name=name,
            condition_index=index,
        )
        return {
            "condition_index": index,
            "condition_name": name,
            "screen_no": screen_no,
        }

    def stop_condition(self, index: int, name: str) -> Dict[str, Any]:
        """Stop realtime monitoring for a condition.

        Returns
        -------
        dict
            ``{"condition_index": int, "condition_name": str, "stopped": bool}``
        """
        stopped = self._condition_manager.stop_monitoring(
            condition_name=name,
            condition_index=index,
        )
        return {
            "condition_index": index,
            "condition_name": name,
            "stopped": stopped,
        }

    def get_condition_matches(self, index: int, name: str) -> List[Dict[str, Any]]:
        """Return currently tracked codes for a monitored condition."""
        key = (index, name)
        codes = self._condition_manager._tracked_codes.get(key, set())
        now_iso = _iso_now()
        return [
            {
                "ticker": code,
                "name": None,
                "current_price": None,
                "updated_at": now_iso,
            }
            for code in sorted(codes)
        ]

    # -- Internal helpers -----------------------------------------------------

    def _order_to_dict(self, order_no: str) -> Dict[str, Any]:
        """Convert an internal ``Order`` to the frontend-compatible dict."""
        order = self._order_manager.order_history[order_no]

        if order.order_type in _ORDER_TYPE_IS_BUY:
            side = "BUY"
        else:
            side = "SELL"

        if order.hoga_type == HogaType.MARKET.value:
            api_order_type = "MARKET"
            display_price = None
        else:
            api_order_type = "LIMIT"
            display_price = float(order.price) if order.price else None

        # Derive status and fill quantities from chejan state if available
        filled_qty = 0
        unfilled_qty = order.qty
        fill_price: Optional[float] = None

        chejan_status = self._chejan.get_order_status(order_no)
        if chejan_status is not None:
            api_status = chejan_status.value.upper()
            # Normalise to frontend enum
            if api_status == "CANCELLED":
                api_status = "CANCELED"
            elif api_status == "PLACED":
                api_status = "CONFIRMED"
            elif api_status == "PENDING":
                api_status = "RECEIVED"

            # Extract fill data from most recent chejan event for this order
            for evt in reversed(self._chejan_events):
                if evt.get("order_no") == order_no and evt.get("type") == "order":
                    filled_qty = evt.get("filled_qty", 0)
                    unfilled_qty = evt.get("unfilled_qty", order.qty)
                    raw_price = evt.get("fill_price", 0)
                    if raw_price:
                        fill_price = float(raw_price)
                    break
        else:
            api_status = _KIWOOM_STATUS_TO_API.get(order.status, "RECEIVED")

        return {
            "order_id": order_no,
            "ticker": order.code,
            "side": side,
            "quantity": order.qty,
            "filled_quantity": filled_qty,
            "unfilled_quantity": unfilled_qty,
            "order_type": api_order_type,
            "price": display_price,
            "filled_price": fill_price,
            "status": api_status,
            "created_at": _epoch_to_iso(order.created_at) or _iso_now(),
            "updated_at": _epoch_to_iso(order.sent_at),
        }

    def _on_chejan_event(self, payload: Dict[str, Any]) -> None:
        """Store chejan events for potential WebSocket broadcasting."""
        self._chejan_events.append(payload)
        logger.debug("Chejan event stored: %s", payload.get("type"))
