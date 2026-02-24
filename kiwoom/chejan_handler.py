"""Chejan event handler for order confirmation and balance updates."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from kiwoom.constants import ChejanGubun, FID
from kiwoom.safety import KiwoomSafetyManager


class OrderStatus(str, Enum):
    """Order lifecycle states derived from Chejan events."""

    PENDING = "PENDING"
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


_STATUS_PRECEDENCE = {
    OrderStatus.PENDING: 0,
    OrderStatus.PLACED: 1,
    OrderStatus.CONFIRMED: 2,
    OrderStatus.PARTIAL: 3,
    OrderStatus.FILLED: 4,
    OrderStatus.CANCELLED: 4,
    OrderStatus.REJECTED: 4,
}


@dataclass
class ChejanOrderEvent:
    """Parsed order/fill event payload."""

    order_no: str
    code: str
    raw_status: str
    filled_qty: int
    unfilled_qty: int
    fill_price: int
    status: OrderStatus


class ChejanHandler:
    """Handle OnReceiveChejanData callbacks and maintain order/position state."""

    def __init__(
        self,
        ocx: Any,
        order_manager: Any | None = None,
        get_chejan_data_fn: Optional[Callable[[int], str]] = None,
        async_notify: bool = True,
        safety_manager: Optional[KiwoomSafetyManager] = None,
    ) -> None:
        self._ocx = ocx
        self._order_manager = order_manager
        self._get_chejan_data_fn = get_chejan_data_fn
        self._async_notify = async_notify
        self._safety_manager = safety_manager

        self._order_status: Dict[str, OrderStatus] = {}
        self._positions: Dict[str, Dict[str, int]] = {}
        self._observers: List[Callable[[Dict[str, Any]], None]] = []
        self._state_lock = threading.RLock()
        self._observer_lock = threading.RLock()
        self._notify_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._notify_worker: Optional[threading.Thread] = None
        if self._async_notify:
            self._notify_worker = threading.Thread(target=self._notify_loop, daemon=True)
            self._notify_worker.start()

        self._bind_events()

    def _bind_events(self) -> None:
        if hasattr(self._ocx, "OnReceiveChejanData") and hasattr(self._ocx.OnReceiveChejanData, "connect"):
            self._ocx.OnReceiveChejanData.connect(self.on_receive_chejan_data)
        elif hasattr(self._ocx, "_callbacks") and isinstance(self._ocx._callbacks, dict):
            self._ocx._callbacks["OnReceiveChejanData"] = self.on_receive_chejan_data

    def add_observer(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._observer_lock:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._observer_lock:
            if callback in self._observers:
                self._observers.remove(callback)

    def get_order_status(self, order_no: str) -> Optional[OrderStatus]:
        with self._state_lock:
            return self._order_status.get(order_no)

    @property
    def positions(self) -> Dict[str, Dict[str, int]]:
        with self._state_lock:
            return dict(self._positions)

    def on_receive_chejan_data(self, sGubun: str, nItemCnt: int, sFidList: str) -> None:
        requested_fids = self._parse_fid_list(sFidList) if nItemCnt > 0 else set()
        if sGubun == ChejanGubun.ORDER.value:
            event = self._parse_order_event(requested_fids)
            if not event.order_no:
                return
            with self._state_lock:
                prev_status = self._order_status.get(event.order_no)
                next_status = self._resolve_next_status(prev_status, event.status)
                self._order_status[event.order_no] = next_status
            event.status = next_status
            self._sync_order_manager(event)
            if prev_status != next_status:
                self._notify(
                    {
                        "type": "order",
                        "order_no": event.order_no,
                        "code": event.code,
                        "status": next_status.value,
                        "raw_status": event.raw_status,
                        "filled_qty": event.filled_qty,
                        "unfilled_qty": event.unfilled_qty,
                        "fill_price": event.fill_price,
                    }
                )
                if self._safety_manager is not None:
                    self._safety_manager.on_chejan_event(
                        {
                            "type": "order",
                            "order_no": event.order_no,
                            "code": event.code,
                            "status": next_status.value,
                            "raw_status": event.raw_status,
                            "filled_qty": event.filled_qty,
                            "unfilled_qty": event.unfilled_qty,
                            "fill_price": event.fill_price,
                        }
                    )
        elif sGubun == ChejanGubun.BALANCE.value:
            position = self._parse_balance_event(requested_fids)
            if not position:
                return
            code = position["code"]
            with self._state_lock:
                self._positions[code] = position
            self._notify({"type": "balance", **position})
            if self._safety_manager is not None:
                self._safety_manager.on_chejan_event({"type": "balance", **position})

    @staticmethod
    def _parse_fid_list(s_fid_list: str) -> Set[int]:
        if not s_fid_list:
            return set()
        parsed: Set[int] = set()
        for token in s_fid_list.split(";"):
            token = token.strip()
            if not token:
                continue
            try:
                parsed.add(int(token))
            except ValueError:
                continue
        return parsed

    def _get_chejan_data(self, fid: int) -> str:
        if self._get_chejan_data_fn is not None:
            value = self._get_chejan_data_fn(fid)
            return value.strip() if isinstance(value, str) else str(value).strip()
        value = self._ocx.dynamicCall("GetChejanData(int)", fid)
        return value.strip() if isinstance(value, str) else str(value).strip()

    @staticmethod
    def _to_int(value: str) -> int:
        if not value:
            return 0
        cleaned = value.replace(",", "")
        try:
            return int(cleaned)
        except ValueError:
            return 0

    @staticmethod
    def _normalize_code(raw_code: str) -> str:
        code = raw_code.strip()
        if code.startswith("A") and len(code) > 1:
            return code[1:]
        return code

    def _derive_status(self, raw_status: str, filled_qty: int, unfilled_qty: int) -> OrderStatus:
        status = raw_status.strip()

        if "취소" in status:
            return OrderStatus.CANCELLED
        if any(token in status for token in ["거부", "실패", "오류"]):
            return OrderStatus.REJECTED
        if "접수" in status:
            return OrderStatus.PLACED
        if "확인" in status:
            return OrderStatus.CONFIRMED
        if "체결" in status:
            if filled_qty > 0 and unfilled_qty > 0:
                return OrderStatus.PARTIAL
            if filled_qty > 0 and unfilled_qty == 0:
                return OrderStatus.FILLED
            return OrderStatus.CONFIRMED

        if filled_qty > 0 and unfilled_qty > 0:
            return OrderStatus.PARTIAL
        if filled_qty > 0 and unfilled_qty == 0:
            return OrderStatus.FILLED
        return OrderStatus.PENDING

    @staticmethod
    def _resolve_next_status(current: Optional[OrderStatus], candidate: OrderStatus) -> OrderStatus:
        if current is None:
            return candidate
        if current in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}:
            return current
        if _STATUS_PRECEDENCE[candidate] >= _STATUS_PRECEDENCE[current]:
            return candidate
        return current
    def _get_fid_values(self, required_fids: List[int], requested_fids: Set[int]) -> Dict[int, str]:
        if not requested_fids:
            return {fid: self._get_chejan_data(fid) for fid in required_fids}
        return {fid: self._get_chejan_data(fid) for fid in required_fids if fid in requested_fids}

    def _parse_order_event(self, requested_fids: Set[int]) -> ChejanOrderEvent:
        values = self._get_fid_values(
            [
                FID.ORDER_NO,
                FID.CODE,
                FID.ORDER_STATUS,
                FID.FILL_PRICE,
                FID.FILL_QTY,
                FID.UNFILLED_QTY,
            ],
            requested_fids,
        )
        order_no = values.get(FID.ORDER_NO, "")
        code = self._normalize_code(values.get(FID.CODE, ""))
        raw_status = values.get(FID.ORDER_STATUS, "")
        fill_price = self._to_int(values.get(FID.FILL_PRICE, ""))
        filled_qty = self._to_int(values.get(FID.FILL_QTY, ""))
        unfilled_qty = self._to_int(values.get(FID.UNFILLED_QTY, ""))

        status = self._derive_status(raw_status, filled_qty, unfilled_qty)
        return ChejanOrderEvent(
            order_no=order_no,
            code=code,
            raw_status=raw_status,
            filled_qty=filled_qty,
            unfilled_qty=unfilled_qty,
            fill_price=fill_price,
            status=status,
        )

    def _parse_balance_event(self, requested_fids: Set[int]) -> Optional[Dict[str, int]]:
        values = self._get_fid_values(
            [
                FID.CODE,
                FID.HOLDING_QTY,
                FID.AVG_BUY_PRICE,
                FID.TOTAL_COST,
                FID.ORDERABLE_QTY,
                FID.DAY_PNL,
                FID.PNL_RATE,
            ],
            requested_fids,
        )
        code = self._normalize_code(values.get(FID.CODE, ""))
        if not code:
            return None

        return {
            "code": code,
            "holding_qty": self._to_int(values.get(FID.HOLDING_QTY, "")),
            "avg_buy_price": self._to_int(values.get(FID.AVG_BUY_PRICE, "")),
            "total_cost": self._to_int(values.get(FID.TOTAL_COST, "")),
            "orderable_qty": self._to_int(values.get(FID.ORDERABLE_QTY, "")),
            "day_pnl": self._to_int(values.get(FID.DAY_PNL, "")),
            "pnl_rate": self._to_int(values.get(FID.PNL_RATE, "")),
        }

    def _sync_order_manager(self, event: ChejanOrderEvent) -> None:
        if self._order_manager is None:
            return
        order = getattr(self._order_manager, "order_history", {}).get(event.order_no)
        if order is None:
            return
        order.status = event.status.value.lower()
        order.message = event.raw_status

    def _notify_loop(self) -> None:
        while True:
            payload = self._notify_queue.get()
            try:
                self._dispatch(payload)
            finally:
                self._notify_queue.task_done()

    def _dispatch(self, payload: Dict[str, Any]) -> None:
        with self._observer_lock:
            observers = list(self._observers)
        for callback in observers:
            try:
                callback(payload)
            except Exception:
                continue

    def _notify(self, payload: Dict[str, Any]) -> None:
        if self._async_notify:
            self._notify_queue.put(payload)
            return
        self._dispatch(payload)
