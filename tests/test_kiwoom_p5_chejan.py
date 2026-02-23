"""Tests for Kiwoom P5 Chejan handler and order state machine."""

from __future__ import annotations

from typing import Dict

from kiwoom.chejan_handler import ChejanHandler, OrderStatus
from kiwoom.constants import FID
from kiwoom.order import KiwoomOrderManager


class _FakeOcx:
    def __init__(self):
        self.calls = []
        self._callbacks = {}
        self._chejan_values: Dict[int, str] = {}

    def dynamicCall(self, func_spec, *args):
        self.calls.append((func_spec, args))
        if "GetChejanData" in func_spec:
            return self._chejan_values.get(args[0], "")
        if "SendOrder" in func_spec:
            return 0
        return ""


def _set_order_chejan(ocx: _FakeOcx, *, order_no: str, code: str, status: str, fill_price: int, fill_qty: int, unfilled_qty: int) -> None:
    ocx._chejan_values = {
        FID.ORDER_NO: order_no,
        FID.CODE: code,
        FID.ORDER_STATUS: status,
        FID.FILL_PRICE: str(fill_price),
        FID.FILL_QTY: str(fill_qty),
        FID.UNFILLED_QTY: str(unfilled_qty),
    }


def test_order_state_machine_transitions() -> None:
    ocx = _FakeOcx()
    handler = ChejanHandler(ocx)

    _set_order_chejan(ocx, order_no="111", code="A005930", status="접수", fill_price=0, fill_qty=0, unfilled_qty=10)
    handler.on_receive_chejan_data("0", 0, "")
    assert handler.get_order_status("111") == OrderStatus.PLACED

    _set_order_chejan(ocx, order_no="111", code="A005930", status="확인", fill_price=0, fill_qty=0, unfilled_qty=10)
    handler.on_receive_chejan_data("0", 0, "")
    assert handler.get_order_status("111") == OrderStatus.CONFIRMED

    _set_order_chejan(ocx, order_no="111", code="A005930", status="체결", fill_price=70000, fill_qty=3, unfilled_qty=7)
    handler.on_receive_chejan_data("0", 0, "")
    assert handler.get_order_status("111") == OrderStatus.PARTIAL

    _set_order_chejan(ocx, order_no="111", code="A005930", status="체결", fill_price=70000, fill_qty=10, unfilled_qty=0)
    handler.on_receive_chejan_data("0", 0, "")
    assert handler.get_order_status("111") == OrderStatus.FILLED


def test_cancelled_status_mapping() -> None:
    ocx = _FakeOcx()
    handler = ChejanHandler(ocx)

    _set_order_chejan(ocx, order_no="222", code="A005930", status="취소", fill_price=0, fill_qty=0, unfilled_qty=0)
    handler.on_receive_chejan_data("0", 0, "")
    assert handler.get_order_status("222") == OrderStatus.CANCELLED


def test_balance_event_updates_positions() -> None:
    ocx = _FakeOcx()
    handler = ChejanHandler(ocx)

    ocx._chejan_values = {
        FID.CODE: "A005930",
        FID.HOLDING_QTY: "10",
        FID.AVG_BUY_PRICE: "70000",
        FID.TOTAL_COST: "700000",
        FID.ORDERABLE_QTY: "10",
        FID.DAY_PNL: "10000",
        FID.PNL_RATE: "2",
    }

    handler.on_receive_chejan_data("1", 0, "")
    assert handler.positions["005930"]["holding_qty"] == 10
    assert handler.positions["005930"]["avg_buy_price"] == 70000


def test_observer_receives_order_and_balance_events() -> None:
    ocx = _FakeOcx()
    handler = ChejanHandler(ocx)
    events = []
    handler.add_observer(events.append)

    _set_order_chejan(ocx, order_no="333", code="A005930", status="접수", fill_price=0, fill_qty=0, unfilled_qty=10)
    handler.on_receive_chejan_data("0", 0, "")

    ocx._chejan_values = {
        FID.CODE: "A005930",
        FID.HOLDING_QTY: "10",
        FID.AVG_BUY_PRICE: "70000",
        FID.TOTAL_COST: "700000",
        FID.ORDERABLE_QTY: "10",
        FID.DAY_PNL: "0",
        FID.PNL_RATE: "0",
    }
    handler.on_receive_chejan_data("1", 0, "")

    assert events[0]["type"] == "order"
    assert events[1]["type"] == "balance"


def test_observer_exception_does_not_block_next_observer() -> None:
    ocx = _FakeOcx()
    handler = ChejanHandler(ocx)
    events = []

    def _broken(_payload):
        raise RuntimeError("observer failure")

    handler.add_observer(_broken)
    handler.add_observer(events.append)

    _set_order_chejan(
        ocx,
        order_no="334",
        code="A005930",
        status="접수",
        fill_price=0,
        fill_qty=0,
        unfilled_qty=10,
    )
    handler.on_receive_chejan_data("0", 0, "")
    assert len(events) == 1
    assert events[0]["type"] == "order"


def test_syncs_status_to_order_manager_history() -> None:
    ocx = _FakeOcx()
    order_manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)

    order_no = order_manager.send_order(
        rq_name="rq_sync",
        screen_no="1001",
        acc_no="8123456789",
        order_type=1,
        code="005930",
        qty=1,
        price=70000,
        hoga_type="00",
        org_order_no="",
    )

    handler = ChejanHandler(ocx, order_manager=order_manager)
    _set_order_chejan(ocx, order_no=order_no, code="A005930", status="체결", fill_price=70000, fill_qty=1, unfilled_qty=0)
    handler.on_receive_chejan_data("0", 0, "")

    assert order_manager.order_history[order_no].status == "filled"
