"""Tests for Kiwoom P6 portfolio integration surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from portfolio.executor import KiwoomExecutor, Order, OrderStatus
from portfolio.holdings import Portfolio
from portfolio.trigger import ConditionChecker, RealtimeTriggerBridge


class _FakeOrderManager:
    def __init__(self):
        self.calls = []

    def send_order(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["order_type"] in {3, 4}:
            return "cancel-001"
        return "broker-001"


class _FakeChejanHandler:
    def __init__(self, status=None):
        self._status = status
        self._observers = []

    def add_observer(self, cb):
        self._observers.append(cb)

    def get_order_status(self, order_no):
        _ = order_no
        return self._status


@dataclass
class _Violation:
    message: str


@dataclass
class _RiskResult:
    allowed: bool
    violations: list


class _AllowRiskManager:
    def validate_order(self, **kwargs):
        _ = kwargs
        return _RiskResult(allowed=True, violations=[])


class _BlockRiskManager:
    def validate_order(self, **kwargs):
        _ = kwargs
        return _RiskResult(allowed=False, violations=[_Violation("blocked by test")])


def test_kiwoom_executor_execute_and_status_mapping() -> None:
    order_manager = _FakeOrderManager()
    chejan_handler = _FakeChejanHandler()
    executor = KiwoomExecutor(
        ocx=object(),
        acc_no="8123456789",
        risk_manager=_AllowRiskManager(),
        order_manager=order_manager,
        chejan_handler=chejan_handler,
    )

    result = executor.execute(
        Order(
            ticker="005930.KS",
            side="BUY",
            quantity=3,
            price=70000,
            order_type="LIMIT",
            order_id="cid-1",
        )
    )

    assert result.success is True
    assert result.status == OrderStatus.PENDING.value
    assert order_manager.calls[0]["code"] == "005930"
    assert order_manager.calls[0]["order_type"] == 1


def test_kiwoom_executor_blocks_by_risk_rule() -> None:
    executor = KiwoomExecutor(
        ocx=object(),
        acc_no="8123456789",
        risk_manager=_BlockRiskManager(),
        order_manager=_FakeOrderManager(),
        chejan_handler=_FakeChejanHandler(),
    )

    result = executor.execute(
        Order(
            ticker="005930.KS",
            side="BUY",
            quantity=1,
            price=70000,
            order_type="LIMIT",
            order_id="cid-2",
        )
    )

    assert result.success is False
    assert result.status == OrderStatus.REJECTED.value
    assert "blocked" in result.message


def test_portfolio_sync_from_chejan_and_opw00018(tmp_path) -> None:
    portfolio_file = tmp_path / "portfolio.yaml"
    p = Portfolio(filepath=str(portfolio_file))

    p.sync_from_kiwoom_balance_event(
        {
            "type": "balance",
            "code": "005930",
            "holding_qty": 5,
            "avg_buy_price": 70000,
        }
    )
    assert p.get("005930.KS") is not None
    assert p.get("005930.KS").quantity == 5

    count = p.sync_from_opw00018(
        [
            {"code": "005930", "name": "삼성전자", "holding_qty": 10, "avg_buy_price": 71000},
            {"code": "000660", "name": "SK하이닉스", "holding_qty": 3, "avg_buy_price": 120000},
        ]
    )
    assert count == 2
    assert p.get("005930.KS").quantity == 10
    assert p.get("000660.KS").quantity == 3


def test_realtime_trigger_bridge_uses_event_feed() -> None:
    checker = ConditionChecker()
    checker.add_condition("005930.KS", "PRICE_ABOVE", 70000)

    events = []
    checker.on_triggered(events.append)

    bridge = RealtimeTriggerBridge(checker)
    emitted = bridge.on_realtime_event({"code": "005930", "current_price": 71000})

    assert len(emitted) == 1
    assert len(events) == 1
    assert events[0]["ticker"] == "005930.KS"
