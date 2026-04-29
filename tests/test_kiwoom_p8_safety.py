"""Tests for Kiwoom P8 safety features."""

from __future__ import annotations

import time
from pathlib import Path

from brokers.kiwoom.chejan_handler import ChejanHandler
from brokers.kiwoom.connection import KiwoomConnection
from brokers.kiwoom.constants import FID, HogaType, OrderType
from brokers.kiwoom.order import KiwoomOrderManager
from brokers.kiwoom.safety import AuditLogger, KiwoomSafetyManager, SafetyViolation


class _FakeOcx:
    def __init__(self, return_value=0):
        self.calls = []
        self.return_value = return_value
        self._callbacks = {}
        self._chejan_values = {}

    def dynamicCall(self, func_spec, *args):
        self.calls.append((func_spec, args))
        if "GetChejanData" in func_spec:
            return self._chejan_values.get(args[0], "")
        if "GetLoginInfo" in func_spec:
            return "1"
        if "SendOrder" in func_spec:
            return self.return_value
        return ""


class _MockConnection:
    def __init__(self, mock_trading: bool = True):
        self._mock_trading = mock_trading

    def is_mock_trading(self) -> bool:
        return self._mock_trading


def test_duplicate_order_prevention_blocks_fast_repeats(tmp_path: Path) -> None:
    ocx = _FakeOcx(return_value=0)
    safety = KiwoomSafetyManager(
        duplicate_window_seconds=5.0,
        audit_logger=AuditLogger(log_dir=str(tmp_path)),
    )
    manager = KiwoomOrderManager(
        ocx,
        throttle_seconds=0.0,
        connection=_MockConnection(mock_trading=True),
        safety_manager=safety,
    )

    _ = manager.send_order(
        rq_name="dup",
        screen_no="1001",
        acc_no="8123456789",
        order_type=int(OrderType.NEW_BUY),
        code="005930",
        qty=1,
        price=70000,
        hoga_type=HogaType.LIMIT.value,
        org_order_no="",
    )

    try:
        manager.send_order(
            rq_name="dup2",
            screen_no="1001",
            acc_no="8123456789",
            order_type=int(OrderType.NEW_BUY),
            code="005930",
            qty=1,
            price=70000,
            hoga_type=HogaType.LIMIT.value,
            org_order_no="",
        )
        assert False, "duplicate order should have been blocked"
    except SafetyViolation:
        pass


def test_kill_switch_blocks_new_orders_and_allows_cancel(tmp_path: Path) -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(
        ocx,
        throttle_seconds=0.0,
        connection=_MockConnection(mock_trading=True),
    )
    safety = KiwoomSafetyManager(
        duplicate_window_seconds=5.0,
        audit_logger=AuditLogger(log_dir=str(tmp_path)),
        cancel_open_orders_fn=manager.cancel_open_orders,
    )
    manager._safety_manager = safety

    order_no = manager.send_order(
        rq_name="new_buy",
        screen_no="1001",
        acc_no="8123456789",
        order_type=int(OrderType.NEW_BUY),
        code="005930",
        qty=1,
        price=70000,
        hoga_type=HogaType.LIMIT.value,
        org_order_no="",
    )
    assert order_no

    cancelled = safety.activate_kill_switch("manual emergency stop")
    assert cancelled >= 1

    try:
        manager.send_order(
            rq_name="blocked_buy",
            screen_no="1001",
            acc_no="8123456789",
            order_type=int(OrderType.NEW_BUY),
            code="005930",
            qty=1,
            price=70000,
            hoga_type=HogaType.LIMIT.value,
            org_order_no="",
        )
        assert False, "new order should be blocked when kill switch is active"
    except SafetyViolation:
        pass


def test_audit_logging_writes_send_order_and_chejan(tmp_path: Path) -> None:
    ocx = _FakeOcx(return_value=0)
    safety = KiwoomSafetyManager(
        duplicate_window_seconds=5.0,
        audit_logger=AuditLogger(log_dir=str(tmp_path)),
    )
    manager = KiwoomOrderManager(
        ocx,
        throttle_seconds=0.0,
        connection=_MockConnection(mock_trading=True),
        safety_manager=safety,
    )
    handler = ChejanHandler(ocx, order_manager=manager, safety_manager=safety, async_notify=False)

    order_no = manager.send_order(
        rq_name="audit_order",
        screen_no="1001",
        acc_no="8123456789",
        order_type=int(OrderType.NEW_BUY),
        code="005930",
        qty=1,
        price=70000,
        hoga_type=HogaType.LIMIT.value,
        org_order_no="",
    )

    ocx._chejan_values = {
        FID.ORDER_NO: order_no,
        FID.CODE: "A005930",
        FID.ORDER_STATUS: "체결",
        FID.FILL_PRICE: "70000",
        FID.FILL_QTY: "1",
        FID.UNFILLED_QTY: "0",
    }
    handler.on_receive_chejan_data("0", 0, "")

    log_files = list(tmp_path.glob("kiwoom_audit_*.log"))
    assert log_files, "audit log file should exist"
    content = log_files[0].read_text(encoding="utf-8")
    assert "event=send_order" in content
    assert "event=chejan" in content


def test_connection_reconnect_failure_callback_triggered() -> None:
    failures = []
    conn = KiwoomConnection(
        mock=True,
        reconnect_attempts=1,
        reconnect_interval=0.01,
        on_reconnect_failure=lambda code: failures.append(code),
    )
    conn._connected = True
    conn.login = lambda: False  # type: ignore[method-assign]
    conn._on_event_connect(-101)
    time.sleep(0.05)
    assert failures
