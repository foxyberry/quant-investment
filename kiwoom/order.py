"""Kiwoom SendOrder wrapper with queue-based throttling for mock trading."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from kiwoom.constants import HogaType, OrderType


_ALLOWED_HOGA = {item.value for item in HogaType}
_ALLOWED_ORDER_TYPES = {int(item.value) for item in OrderType}
_CANCEL_OR_MODIFY_TYPES = {
    int(OrderType.CANCEL_BUY),
    int(OrderType.CANCEL_SELL),
    int(OrderType.MODIFY_BUY),
    int(OrderType.MODIFY_SELL),
}


def _validate_screen_no(screen_no: str) -> str:
    if not isinstance(screen_no, str) or len(screen_no) != 4 or not screen_no.isdigit():
        raise ValueError("screen_no must be a 4-digit string")
    return screen_no


def _validate_non_empty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass
class Order:
    """Order snapshot tracked by KiwoomOrderManager."""

    order_no: str
    rq_name: str
    api_rq_name: str
    screen_no: str
    acc_no: str
    order_type: int
    code: str
    qty: int
    price: int
    hoga_type: str
    org_order_no: str
    status: str = "queued"
    message: str = ""
    created_at: float = field(default_factory=time.time)
    sent_at: Optional[float] = None


@dataclass
class _OrderTask:
    rq_name: str
    api_rq_name: str
    screen_no: str
    acc_no: str
    order_type: int
    code: str
    qty: int
    price: int
    hoga_type: str
    org_order_no: str
    done_event: threading.Event
    result_holder: Dict[str, Any]


class KiwoomOrderManager:
    """Queue-driven SendOrder manager with 1 order/sec throttling."""

    def __init__(
        self,
        ocx: Any,
        throttle_seconds: float = 1.0,
        max_history_size: int = 2000,
        history_ttl_seconds: Optional[float] = 86400.0,
        sleep_fn: Callable[[float], None] = time.sleep,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ocx = ocx
        self._throttle_seconds = throttle_seconds
        self._max_history_size = max_history_size
        self._history_ttl_seconds = history_ttl_seconds
        self._sleep = sleep_fn
        self._time = time_fn

        self.order_history: Dict[str, Order] = {}
        self._order_by_rq_name: Dict[str, str] = {}
        self._queue: "queue.Queue[_OrderTask]" = queue.Queue()
        self._lock = threading.RLock()
        self._last_sent_at: float = 0.0
        self._counter = 0
        self._rq_counter = 0

        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        self._bind_events()

    def _bind_events(self) -> None:
        """Bind OnReceiveMsg callback if supported by OCX object."""
        if hasattr(self._ocx, "OnReceiveMsg") and hasattr(self._ocx.OnReceiveMsg, "connect"):
            self._ocx.OnReceiveMsg.connect(self.on_receive_msg)
        elif hasattr(self._ocx, "_callbacks") and isinstance(self._ocx._callbacks, dict):
            self._ocx._callbacks["OnReceiveMsg"] = self.on_receive_msg

    def send_order(
        self,
        rq_name: str,
        screen_no: str,
        acc_no: str,
        order_type: int,
        code: str,
        qty: int,
        price: int,
        hoga_type: str,
        org_order_no: str,
    ) -> str:
        """Queue an order and return tracked order number once sent."""
        rq_name = _validate_non_empty(rq_name, "rq_name")
        screen_no = _validate_screen_no(screen_no)
        acc_no = _validate_non_empty(acc_no, "acc_no")
        code = _validate_non_empty(code, "code")
        org_order_no = org_order_no.strip() if isinstance(org_order_no, str) else ""

        if order_type not in _ALLOWED_ORDER_TYPES:
            raise ValueError("order_type must be one of 1..6")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("qty must be a positive int")
        if not isinstance(price, int) or price < 0:
            raise ValueError("price must be a non-negative int")

        hoga_type = _validate_non_empty(hoga_type, "hoga_type")
        if hoga_type not in _ALLOWED_HOGA:
            raise ValueError("unsupported hoga_type")

        if order_type in _CANCEL_OR_MODIFY_TYPES and not org_order_no:
            raise ValueError("org_order_no is required for cancel/modify orders")

        if hoga_type == HogaType.MARKET.value and price != 0:
            raise ValueError("market order must use price=0")

        done_event = threading.Event()
        result_holder: Dict[str, Any] = {}
        task = _OrderTask(
            rq_name=rq_name,
            api_rq_name=self._next_api_rq_name(rq_name),
            screen_no=screen_no,
            acc_no=acc_no,
            order_type=order_type,
            code=code,
            qty=qty,
            price=price,
            hoga_type=hoga_type,
            org_order_no=org_order_no,
            done_event=done_event,
            result_holder=result_holder,
        )
        self._queue.put(task)
        done_event.wait(timeout=10.0)

        if "error" in result_holder:
            raise RuntimeError(result_holder["error"])
        if "order_no" not in result_holder:
            raise RuntimeError("order send timeout")
        return result_holder["order_no"]

    def on_receive_msg(self, screen_no: str, rq_name: str, tr_code: str, msg: str) -> None:
        """Handle OnReceiveMsg and update tracked order status/message."""
        _ = screen_no
        _ = tr_code
        with self._lock:
            order_no = self._order_by_rq_name.get(rq_name)
            if not order_no:
                return
            order = self.order_history.get(order_no)
            if not order:
                return

            order.message = msg or ""
            if any(token in (msg or "") for token in ["실패", "거부", "오류", "error", "Error"]):
                order.status = "rejected"
            else:
                order.status = "accepted"

    def _next_order_no(self) -> str:
        with self._lock:
            self._counter += 1
            return f"mock-{self._counter:08d}"

    def _next_api_rq_name(self, rq_name: str) -> str:
        with self._lock:
            self._rq_counter += 1
            return f"{rq_name}#{self._rq_counter}"

    def _cleanup_history(self) -> None:
        if not self.order_history:
            return

        now_wall = time.time()
        stale_order_nos = set()

        if self._history_ttl_seconds is not None and self._history_ttl_seconds > 0:
            for order_no, order in self.order_history.items():
                ref_ts = order.sent_at or order.created_at
                if now_wall - ref_ts >= self._history_ttl_seconds:
                    stale_order_nos.add(order_no)

        if (
            self._max_history_size > 0
            and len(self.order_history) - len(stale_order_nos) > self._max_history_size
        ):
            survivors = [
                (order_no, order)
                for order_no, order in self.order_history.items()
                if order_no not in stale_order_nos
            ]
            survivors.sort(key=lambda item: item[1].sent_at or item[1].created_at)
            overflow = len(survivors) - self._max_history_size
            if overflow > 0:
                stale_order_nos.update(order_no for order_no, _ in survivors[:overflow])

        if not stale_order_nos:
            return

        for order_no in stale_order_nos:
            self.order_history.pop(order_no, None)

        stale_rq_names = [rq_name for rq_name, order_no in self._order_by_rq_name.items() if order_no in stale_order_nos]
        for rq_name in stale_rq_names:
            self._order_by_rq_name.pop(rq_name, None)

    def _worker_loop(self) -> None:
        while True:
            task = self._queue.get()
            try:
                now = self._time()
                gap = now - self._last_sent_at
                if gap < self._throttle_seconds:
                    self._sleep(self._throttle_seconds - gap)

                ret = self._ocx.dynamicCall(
                    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                    task.api_rq_name,
                    task.screen_no,
                    task.acc_no,
                    task.order_type,
                    task.code,
                    task.qty,
                    task.price,
                    task.hoga_type,
                    task.org_order_no,
                )
                self._last_sent_at = self._time()

                if isinstance(ret, int) and ret < 0:
                    task.result_holder["error"] = f"SendOrder failed: {ret}"
                    task.done_event.set()
                    continue

                if isinstance(ret, str) and ret.strip():
                    order_no = ret.strip()
                elif isinstance(ret, int) and ret > 0:
                    order_no = str(ret)
                else:
                    order_no = self._next_order_no()

                order = Order(
                    order_no=order_no,
                    rq_name=task.rq_name,
                    api_rq_name=task.api_rq_name,
                    screen_no=task.screen_no,
                    acc_no=task.acc_no,
                    order_type=task.order_type,
                    code=task.code,
                    qty=task.qty,
                    price=task.price,
                    hoga_type=task.hoga_type,
                    org_order_no=task.org_order_no,
                    status="sent",
                    sent_at=time.time(),
                )
                with self._lock:
                    self.order_history[order_no] = order
                    self._order_by_rq_name[task.api_rq_name] = order_no
                    self._cleanup_history()
                task.result_holder["order_no"] = order_no
                task.done_event.set()
            except Exception as exc:  # pragma: no cover
                task.result_holder["error"] = str(exc)
                task.done_event.set()
            finally:
                self._queue.task_done()
