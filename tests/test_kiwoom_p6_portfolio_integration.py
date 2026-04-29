"""Tests for Kiwoom P6 portfolio integration."""

from __future__ import annotations

from pathlib import Path

from brokers.kiwoom.chejan_handler import ChejanHandler
from brokers.kiwoom.constants import FID
from brokers.kiwoom.order import KiwoomOrderManager
from portfolio.executor import KiwoomExecutor, Order, OrderStatus
from portfolio.holdings import Portfolio
from portfolio.trigger import ConditionChecker, RealtimeTriggerBridge


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
        if "SendOrder" in func_spec:
            return self.return_value
        return ""


class _FakeTrClient:
    def __init__(self):
        self.inputs = {}
        self.requests = []

    def set_input_value(self, key: str, value: str) -> None:
        self.inputs[key] = value

    def comm_rq_data(self, request) -> int:
        self.requests.append(request)
        return 0


class _FakeRealtimeManager:
    def __init__(self):
        self.register_calls = []
        self.unregister_calls = []

    def register(self, code, fids, real_type="1"):
        self.register_calls.append((code, tuple(fids), real_type))
        return "1001"

    def unregister(self, code):
        self.unregister_calls.append(code)


def test_kiwoom_executor_execute_and_fill_status() -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)
    chejan = ChejanHandler(ocx, order_manager=manager, async_notify=False)
    executor = KiwoomExecutor(
        order_manager=manager,
        chejan_handler=chejan,
        account_no="8123456789",
        screen_no="1001",
    )

    order = Order(ticker="005930.KS", side="BUY", quantity=1, price=70000, order_type="LIMIT")
    submit = executor.execute(order)
    assert submit.success
    assert submit.status == OrderStatus.PENDING.value

    broker_no = manager.order_history[next(iter(manager.order_history))].order_no
    ocx._chejan_values = {
        FID.ORDER_NO: broker_no,
        FID.CODE: "A005930",
        FID.ORDER_STATUS: "체결",
        FID.FILL_PRICE: "70000",
        FID.FILL_QTY: "1",
        FID.UNFILLED_QTY: "0",
    }
    chejan.on_receive_chejan_data("0", 0, "")
    status = executor.get_order_status(order.order_id)
    assert status is not None
    assert status.status == OrderStatus.FILLED.value


def test_kiwoom_executor_risk_block() -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)
    chejan = ChejanHandler(ocx, order_manager=manager, async_notify=False)
    executor = KiwoomExecutor(
        order_manager=manager,
        chejan_handler=chejan,
        account_no="8123456789",
        risk_context_provider=lambda: {
            "portfolio_value": 1000.0,
            "cash_balance": 100.0,
            "positions": {},
            "daily_pnl": 0.0,
            "daily_trades": 0,
        },
    )

    order = Order(ticker="005930.KS", side="BUY", quantity=1, price=70000, order_type="LIMIT")
    result = executor.execute(order)
    assert not result.success
    assert result.status == OrderStatus.REJECTED.value
    assert "Risk blocked" in result.message


def test_kiwoom_executor_rejects_invalid_side() -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)
    chejan = ChejanHandler(ocx, order_manager=manager, async_notify=False)
    executor = KiwoomExecutor(
        order_manager=manager,
        chejan_handler=chejan,
        account_no="8123456789",
    )

    order = Order(ticker="005930.KS", side="HOLD", quantity=1, price=70000, order_type="LIMIT")
    result = executor.execute(order)
    assert not result.success
    assert result.status == OrderStatus.REJECTED.value
    assert "unsupported order side" in result.message


def test_kiwoom_executor_market_order_requires_reference_price() -> None:
    ocx = _FakeOcx(return_value=0)
    manager = KiwoomOrderManager(ocx, throttle_seconds=0.0)
    chejan = ChejanHandler(ocx, order_manager=manager, async_notify=False)
    executor = KiwoomExecutor(
        order_manager=manager,
        chejan_handler=chejan,
        account_no="8123456789",
    )

    order = Order(ticker="005930.KS", side="BUY", quantity=1, price=None, order_type="MARKET")
    result = executor.execute(order)
    assert not result.success
    assert result.status == OrderStatus.REJECTED.value
    assert "reference price" in result.message


def test_portfolio_balance_sync_and_tr_request(tmp_path: Path) -> None:
    filepath = tmp_path / "portfolio.yaml"
    portfolio = Portfolio(filepath=str(filepath))
    portfolio.add("005930.KS", quantity=1, avg_price=50000)
    portfolio.apply_balance_event({"code": "005930", "holding_qty": 3, "avg_buy_price": 70000})
    assert portfolio.get("005930.KS").quantity == 3  # type: ignore[union-attr]

    portfolio.sync_from_kiwoom_rows(
        [
            {"code": "000660", "holding_qty": 5, "avg_buy_price": 100000},
            {"code": "005930", "holding_qty": 0, "avg_buy_price": 0},
        ]
    )
    assert portfolio.get("000660.KS") is not None
    assert portfolio.get("005930.KS") is None

    tr_client = _FakeTrClient()
    ret = portfolio.request_tr_sync(tr_client, account_no="8123456789", password="0000")
    assert ret == 0
    assert tr_client.inputs["계좌번호"] == "8123456789"


def test_realtime_trigger_bridge_event_path() -> None:
    checker = ConditionChecker()
    checker.add_condition("005930.KS", "PRICE_ABOVE", 70000)
    bridge = RealtimeTriggerBridge(checker)
    realtime = _FakeRealtimeManager()
    bridge.subscribe(realtime, "005930.KS")

    events = bridge.on_tick({"code": "005930", "current_price": 71000, "change_pct": 1.2})
    assert events
    assert events[0].ticker == "005930.KS"

    bridge.unsubscribe(realtime, "005930.KS")
    assert realtime.unregister_calls == ["005930"]
