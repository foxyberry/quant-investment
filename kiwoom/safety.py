"""Safety utilities for live Kiwoom trading."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Dict, Optional, Tuple

from kiwoom.constants import OrderType


class SafetyViolation(RuntimeError):
    """Raised when a safety rule blocks order submission."""


@dataclass(frozen=True)
class OrderSignature:
    """A lightweight signature for duplicate-order detection."""

    code: str
    side: str
    qty: int


class AuditLogger:
    """File-based audit logger for order and chejan events."""

    def __init__(self, log_dir: str = "logs", time_fn: Callable[[], float] = time.time) -> None:
        self._log_dir = log_dir
        self._time_fn = time_fn
        self._lock = threading.RLock()
        os.makedirs(self._log_dir, exist_ok=True)

    def _log_path(self) -> str:
        date_str = datetime.fromtimestamp(self._time_fn()).strftime("%Y%m%d")
        return os.path.join(self._log_dir, f"kiwoom_audit_{date_str}.log")

    @staticmethod
    def _to_line(event: str, payload: Dict[str, Any]) -> str:
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        fields = " ".join(f"{k}={payload[k]}" for k in sorted(payload))
        return f"{ts} event={event} {fields}\n"

    def write(self, event: str, payload: Dict[str, Any]) -> None:
        line = self._to_line(event, payload)
        with self._lock:
            with open(self._log_path(), "a", encoding="utf-8") as fp:
                fp.write(line)


class DuplicateOrderGuard:
    """Prevents duplicate order submissions in a short time window."""

    def __init__(self, window_seconds: float = 5.0, time_fn: Callable[[], float] = time.time) -> None:
        self._window_seconds = window_seconds
        self._time_fn = time_fn
        self._last_seen_by_signature: Dict[OrderSignature, float] = {}
        self._sent_order_nos: Dict[str, float] = {}
        self._lock = threading.RLock()

    def _cleanup(self, now: float) -> None:
        min_ts = now - self._window_seconds
        stale_signatures = [sig for sig, ts in self._last_seen_by_signature.items() if ts < min_ts]
        for sig in stale_signatures:
            self._last_seen_by_signature.pop(sig, None)
        stale_nos = [order_no for order_no, ts in self._sent_order_nos.items() if ts < min_ts]
        for order_no in stale_nos:
            self._sent_order_nos.pop(order_no, None)

    def is_duplicate(self, signature: OrderSignature) -> bool:
        now = self._time_fn()
        with self._lock:
            self._cleanup(now)
            seen_at = self._last_seen_by_signature.get(signature)
            return seen_at is not None and now - seen_at <= self._window_seconds

    def mark_submitted(self, signature: OrderSignature, order_no: str = "") -> None:
        now = self._time_fn()
        with self._lock:
            self._cleanup(now)
            self._last_seen_by_signature[signature] = now
            if order_no:
                self._sent_order_nos[order_no] = now

    def has_order_no(self, order_no: str) -> bool:
        if not order_no:
            return False
        now = self._time_fn()
        with self._lock:
            self._cleanup(now)
            return order_no in self._sent_order_nos


class KillSwitch:
    """Global kill switch to stop new orders in emergency situations."""

    def __init__(self, cancel_open_orders_fn: Optional[Callable[[], int]] = None) -> None:
        self._cancel_open_orders_fn = cancel_open_orders_fn
        self._active = False
        self._reason = ""
        self._activated_at: Optional[float] = None
        self._lock = threading.RLock()

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._active

    @property
    def reason(self) -> str:
        with self._lock:
            return self._reason

    def activate(self, reason: str) -> int:
        with self._lock:
            if self._active:
                return 0
            self._active = True
            self._reason = reason
            self._activated_at = time.time()
        if self._cancel_open_orders_fn is None:
            return 0
        try:
            return int(self._cancel_open_orders_fn())
        except Exception:
            return 0


class KiwoomSafetyManager:
    """Coordinates kill-switch, audit logging, and duplicate prevention."""

    def __init__(
        self,
        *,
        duplicate_window_seconds: float = 5.0,
        audit_logger: Optional[AuditLogger] = None,
        allow_live_trading: bool = False,
        cancel_open_orders_fn: Optional[Callable[[], int]] = None,
        risk_validator: Optional[Callable[[Dict[str, Any]], Tuple[bool, str]]] = None,
    ) -> None:
        self._audit = audit_logger or AuditLogger()
        self._dup = DuplicateOrderGuard(window_seconds=duplicate_window_seconds)
        self._kill_switch = KillSwitch(cancel_open_orders_fn=cancel_open_orders_fn)
        self._allow_live_trading = allow_live_trading
        self._risk_validator = risk_validator

    @property
    def kill_switch(self) -> KillSwitch:
        return self._kill_switch

    def activate_kill_switch(self, reason: str) -> int:
        cancelled = self._kill_switch.activate(reason)
        self._audit.write("kill_switch", {"reason": reason, "cancelled": cancelled})
        return cancelled

    def validate_pre_order(
        self,
        *,
        connection: Any,
        order_type: int,
        code: str,
        qty: int,
        price: int,
        acc_no: str,
        org_order_no: str,
    ) -> Optional[OrderSignature]:
        is_cancel_or_modify = order_type in {
            int(OrderType.CANCEL_BUY),
            int(OrderType.CANCEL_SELL),
            int(OrderType.MODIFY_BUY),
            int(OrderType.MODIFY_SELL),
        }

        if self._kill_switch.is_active and not is_cancel_or_modify:
            raise SafetyViolation(f"kill switch is active: {self._kill_switch.reason}")

        if connection is not None and hasattr(connection, "is_mock_trading"):
            if (not self._allow_live_trading) and (not connection.is_mock_trading()):
                raise SafetyViolation("live trading is blocked; enable explicit live trading setting")

        if self._risk_validator is not None:
            ok, reason = self._risk_validator(
                {"order_type": order_type, "code": code, "qty": qty, "price": price, "acc_no": acc_no}
            )
            if not ok:
                raise SafetyViolation(f"risk validation failed: {reason}")

        if is_cancel_or_modify:
            return None

        side = "BUY" if order_type in {int(OrderType.NEW_BUY), int(OrderType.MODIFY_BUY)} else "SELL"
        signature = OrderSignature(code=code, side=side, qty=qty)
        if self._dup.is_duplicate(signature):
            raise SafetyViolation("duplicate order blocked within guard window")
        return signature

    def on_order_submit(
        self,
        *,
        rq_name: str,
        api_rq_name: str,
        acc_no: str,
        order_type: int,
        code: str,
        qty: int,
        price: int,
        status: str,
        order_no: str = "",
        signature: Optional[OrderSignature] = None,
        message: str = "",
    ) -> None:
        if signature is not None:
            self._dup.mark_submitted(signature, order_no)
        self._audit.write(
            "send_order",
            {
                "rq_name": rq_name,
                "api_rq_name": api_rq_name,
                "acc_no": acc_no,
                "order_type": order_type,
                "code": code,
                "qty": qty,
                "price": price,
                "status": status,
                "order_no": order_no,
                "message": message,
            },
        )

    def on_chejan_event(self, payload: Dict[str, Any]) -> None:
        self._audit.write("chejan", payload)
