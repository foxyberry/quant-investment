"""Tests for Kiwoom P4 order placement manager."""

from __future__ import annotations

import pytest

from kiwoom.constants import HogaType, OrderType
from kiwoom.order import KiwoomOrderManager


class _FakeOcx:
    def __init__(self, return_value=0):
        self.calls = []
        self.return_value = return_value
        self._callbacks = {}

    def dynamicCall(self, func_spec, *args):
        self.calls.append((func_spec, args))
        if "SendOrder" in func_spec:
            return self.return_value
        return ""


class _FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time_fn(self):
        return self.now

    def sleep_fn(self, sec):
        self.sleeps.append(sec)
        self.now += sec


def test_send_order_creates_history_and_returns_order_no() -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)

    order_no = manager.send_order(
        rq_name="new_buy",
        screen_no="1001",
        acc_no="8123456789",
        order_type=int(OrderType.NEW_BUY),
        code="005930",
        qty=10,
        price=70000,
        hoga_type=HogaType.LIMIT.value,
        org_order_no="",
    )

    assert order_no.startswith("mock-")
    assert order_no in manager.order_history
    assert manager.order_history[order_no].status == "sent"
    assert any("SendOrder" in call[0] for call in ocx.calls)


def test_send_order_uses_returned_order_no_string_when_available() -> None:
    ocx = _FakeOcx(return_value="123456")
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)

    order_no = manager.send_order(
        rq_name="new_buy_2",
        screen_no="1001",
        acc_no="8123456789",
        order_type=int(OrderType.NEW_BUY),
        code="005930",
        qty=1,
        price=70000,
        hoga_type=HogaType.LIMIT.value,
        org_order_no="",
    )

    assert order_no == "123456"


def test_queue_throttle_applies_one_per_second_gap() -> None:
    ocx = _FakeOcx(return_value=0)
    clock = _FakeClock()
    manager = KiwoomOrderManager(
        ocx,
        throttle_seconds=1.0,
        sleep_fn=clock.sleep_fn,
        time_fn=clock.time_fn,
    )

    _ = manager.send_order(
        rq_name="first",
        screen_no="1001",
        acc_no="8123456789",
        order_type=int(OrderType.NEW_BUY),
        code="005930",
        qty=1,
        price=1000,
        hoga_type=HogaType.LIMIT.value,
        org_order_no="",
    )
    _ = manager.send_order(
        rq_name="second",
        screen_no="1001",
        acc_no="8123456789",
        order_type=int(OrderType.NEW_SELL),
        code="005930",
        qty=1,
        price=1000,
        hoga_type=HogaType.LIMIT.value,
        org_order_no="",
    )

    assert len(clock.sleeps) >= 1
    assert clock.sleeps[0] == pytest.approx(1.0)


def test_cancel_or_modify_requires_org_order_no() -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)

    with pytest.raises(ValueError):
        manager.send_order(
            rq_name="cancel_buy",
            screen_no="1001",
            acc_no="8123456789",
            order_type=int(OrderType.CANCEL_BUY),
            code="005930",
            qty=1,
            price=0,
            hoga_type=HogaType.LIMIT.value,
            org_order_no="",
        )


def test_market_order_requires_zero_price() -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)

    with pytest.raises(ValueError):
        manager.send_order(
            rq_name="market_buy",
            screen_no="1001",
            acc_no="8123456789",
            order_type=int(OrderType.NEW_BUY),
            code="005930",
            qty=1,
            price=100,
            hoga_type=HogaType.MARKET.value,
            org_order_no="",
        )


def test_on_receive_msg_updates_status_and_message() -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)

    order_no = manager.send_order(
        rq_name="rq_msg",
        screen_no="1001",
        acc_no="8123456789",
        order_type=int(OrderType.NEW_BUY),
        code="005930",
        qty=1,
        price=1000,
        hoga_type=HogaType.LIMIT.value,
        org_order_no="",
    )

    manager.on_receive_msg("1001", "rq_msg", "SendOrder", "정상처리")
    assert manager.order_history[order_no].status == "accepted"

    manager.on_receive_msg("1001", "rq_msg", "SendOrder", "주문 실패")
    assert manager.order_history[order_no].status == "rejected"
