"""Chejan event handler for order confirmation and balance updates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from kiwoom.constants import ChejanGubun, FID


class OrderStatus(str, Enum):
    """Order lifecycle states derived from Chejan events."""

    PENDING = "PENDING"
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class ChejanOrderEvent:
    """Parsed order/fill event payload."""

    order_no: str
    code: str
    raw_status: str
    order_qty: int
    side: str
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
    ) -> None:
        self._ocx = ocx
        self._order_manager = order_manager
        self._get_chejan_data_fn = get_chejan_data_fn

        self._order_status: Dict[str, OrderStatus] = {}
        self._positions: Dict[str, Dict[str, int]] = {}
        self._observers: List[Callable[[Dict[str, Any]], None]] = []

        self._bind_events()

    def _bind_events(self) -> None:
        if hasattr(self._ocx, "OnReceiveChejanData") and hasattr(self._ocx.OnReceiveChejanData, "connect"):
            self._ocx.OnReceiveChejanData.connect(self.on_receive_chejan_data)
        elif hasattr(self._ocx, "_callbacks") and isinstance(self._ocx._callbacks, dict):
            self._ocx._callbacks["OnReceiveChejanData"] = self.on_receive_chejan_data

    def add_observer(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._observers.append(callback)

    def remove_observer(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    def get_order_status(self, order_no: str) -> Optional[OrderStatus]:
        return self._order_status.get(order_no)

    @property
    def positions(self) -> Dict[str, Dict[str, int]]:
        return dict(self._positions)

    def on_receive_chejan_data(self, sGubun: str, nItemCnt: int, sFidList: str) -> None:
        _ = nItemCnt
        _ = sFidList
        if sGubun == ChejanGubun.ORDER.value:
            event = self._parse_order_event()
            if not event.order_no:
                return
            self._order_status[event.order_no] = event.status
            self._sync_order_manager(event)
            self._notify(
                {
                    "type": "order",
                    "order_no": event.order_no,
                    "code": event.code,
                    "status": event.status.value,
                    "raw_status": event.raw_status,
                    "order_qty": event.order_qty,
                    "side": event.side,
                    "filled_qty": event.filled_qty,
                    "unfilled_qty": event.unfilled_qty,
                    "fill_price": event.fill_price,
                }
            )
        elif sGubun == ChejanGubun.BALANCE.value:
            position = self._parse_balance_event()
            if not position:
                return
            code = position["code"]
            self._positions[code] = position
            self._notify({"type": "balance", **position})

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

    @staticmethod
    def _normalize_side(order_category: str, buy_sell: str) -> str:
        text = f"{order_category} {buy_sell}".upper().replace("+", "").replace("-", "")
        if "매수" in text or "BUY" in text:
            return "BUY"
        if "매도" in text or "SELL" in text:
            return "SELL"
        return ""

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

    def _parse_order_event(self) -> ChejanOrderEvent:
        order_no = self._get_chejan_data(FID.ORDER_NO)
        code = self._normalize_code(self._get_chejan_data(FID.CODE))
        raw_status = self._get_chejan_data(FID.ORDER_STATUS)
        order_qty = self._to_int(self._get_chejan_data(FID.ORDER_QTY))
        side = self._normalize_side(
            self._get_chejan_data(FID.ORDER_CATEGORY),
            self._get_chejan_data(FID.BUY_SELL),
        )
        fill_price = self._to_int(self._get_chejan_data(FID.FILL_PRICE))
        filled_qty = self._to_int(self._get_chejan_data(FID.FILL_QTY))
        unfilled_qty = self._to_int(self._get_chejan_data(FID.UNFILLED_QTY))

        status = self._derive_status(raw_status, filled_qty, unfilled_qty)
        return ChejanOrderEvent(
            order_no=order_no,
            code=code,
            raw_status=raw_status,
            order_qty=order_qty,
            side=side,
            filled_qty=filled_qty,
            unfilled_qty=unfilled_qty,
            fill_price=fill_price,
            status=status,
        )

    def _parse_balance_event(self) -> Optional[Dict[str, int]]:
        code = self._normalize_code(self._get_chejan_data(FID.CODE))
        if not code:
            return None

        return {
            "code": code,
            "holding_qty": self._to_int(self._get_chejan_data(FID.HOLDING_QTY)),
            "avg_buy_price": self._to_int(self._get_chejan_data(FID.AVG_BUY_PRICE)),
            "total_cost": self._to_int(self._get_chejan_data(FID.TOTAL_COST)),
            "orderable_qty": self._to_int(self._get_chejan_data(FID.ORDERABLE_QTY)),
            "day_pnl": self._to_int(self._get_chejan_data(FID.DAY_PNL)),
            "pnl_rate": self._to_int(self._get_chejan_data(FID.PNL_RATE)),
        }

    def _sync_order_manager(self, event: ChejanOrderEvent) -> None:
        if self._order_manager is None:
            return
        order = getattr(self._order_manager, "order_history", {}).get(event.order_no)
        if order is None:
            return
        order.status = event.status.value.lower()
        order.message = event.raw_status

    def _notify(self, payload: Dict[str, Any]) -> None:
        for callback in list(self._observers):
            try:
                callback(payload)
            except Exception:
                continue
