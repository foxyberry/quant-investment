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
        self._order_status_by_no = {}

    def add_observer(self, cb):
        self._observers.append(cb)

    def get_order_status(self, order_no):
        if order_no in self._order_status_by_no:
            return self._order_status_by_no[order_no]
        return self._status

    def emit_order_event(self, order_no, code, status, order_qty=0, side=""):
        self._order_status_by_no[order_no] = type("S", (), {"value": status})()
        payload = {
            "type": "order",
            "order_no": order_no,
            "code": code,
            "status": status,
            "order_qty": order_qty,
            "side": side,
        }
        for cb in list(self._observers):
            cb(payload)


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

    chejan_handler.emit_order_event("real-555", "005930", "FILLED")
    status = executor.get_order_status("cid-1")
    assert status is not None
    assert status.status == OrderStatus.FILLED.value


def test_kiwoom_executor_fallback_remap_matches_side_and_qty() -> None:
    order_manager = _FakeOrderManager()
    chejan_handler = _FakeChejanHandler()
    executor = KiwoomExecutor(
        ocx=object(),
        acc_no="8123456789",
        risk_manager=_AllowRiskManager(),
        order_manager=order_manager,
        chejan_handler=chejan_handler,
    )

    buy_result = executor.execute(
        Order(
            ticker="005930.KS",
            side="BUY",
            quantity=2,
            price=70000,
            order_type="LIMIT",
            order_id="cid-buy-2",
        )
    )
    sell_result = executor.execute(
        Order(
            ticker="005930.KS",
            side="SELL",
            quantity=1,
            price=71000,
            order_type="LIMIT",
            order_id="cid-sell-1",
        )
    )
    assert buy_result.success is True
    assert sell_result.success is True

    # Broker number differs from provisional number and arrives without mapping.
    chejan_handler.emit_order_event("real-777", "005930", "FILLED", order_qty=1, side="SELL")
    buy_status = executor.get_order_status("cid-buy-2")
    sell_status = executor.get_order_status("cid-sell-1")
    assert buy_status is not None and buy_status.status == OrderStatus.PENDING.value
    assert sell_status is not None and sell_status.status == OrderStatus.FILLED.value


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


def test_market_order_rejected_without_market_price_for_risk() -> None:
    executor = KiwoomExecutor(
        ocx=object(),
        acc_no="8123456789",
        risk_manager=_AllowRiskManager(),
        order_manager=_FakeOrderManager(),
        chejan_handler=_FakeChejanHandler(),
    )

    result = executor.execute(
        Order(
            ticker="005930.KS",
            side="BUY",
            quantity=1,
            order_type="MARKET",
            order_id="cid-market-1",
        )
    )

    assert result.success is False
    assert result.status == OrderStatus.REJECTED.value
    assert "Market price unavailable" in result.message


def test_market_order_uses_price_provider_for_risk_check() -> None:
    executor = KiwoomExecutor(
        ocx=object(),
        acc_no="8123456789",
        risk_manager=_AllowRiskManager(),
        order_manager=_FakeOrderManager(),
        chejan_handler=_FakeChejanHandler(),
        market_price_provider=lambda code: 70500.0 if code == "005930" else None,
    )

    result = executor.execute(
        Order(
            ticker="005930.KS",
            side="BUY",
            quantity=1,
            order_type="MARKET",
            order_id="cid-market-2",
        )
    )

    assert result.success is True
    assert result.status == OrderStatus.PENDING.value


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


def test_portfolio_sync_preserves_market_suffix_for_kosdaq(tmp_path) -> None:
    portfolio_file = tmp_path / "portfolio_market.yaml"
    p = Portfolio(filepath=str(portfolio_file))

    count = p.sync_from_opw00018(
        [
            {"code": "035720", "name": "카카오", "holding_qty": 2, "avg_buy_price": 50000, "market": "KOSDAQ"},
        ]
    )
    assert count == 1
    assert p.get("035720.KQ") is not None


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


def test_realtime_trigger_bridge_resolves_kosdaq_suffix() -> None:
    checker = ConditionChecker()
    checker.add_condition("035720.KQ", "PRICE_ABOVE", 50000)
    bridge = RealtimeTriggerBridge(checker)

    emitted = bridge.on_realtime_event(
        {"code": "035720", "current_price": 51000, "market": "KOSDAQ"}
    )
    assert len(emitted) == 1
    assert emitted[0].ticker == "035720.KQ"


def test_portfolio_realtime_sync_uses_throttled_save(tmp_path) -> None:
    portfolio_file = tmp_path / "portfolio_throttled.yaml"
    p = Portfolio(filepath=str(portfolio_file), realtime_save_interval_seconds=60.0)
    save_calls = {"n": 0}

    def _fake_save():
        save_calls["n"] += 1

    p._save = _fake_save  # type: ignore[method-assign]

    p.sync_from_kiwoom_balance_event(
        {"type": "balance", "code": "005930", "holding_qty": 1, "avg_buy_price": 70000}
    )
    p.sync_from_kiwoom_balance_event(
        {"type": "balance", "code": "005930", "holding_qty": 2, "avg_buy_price": 70000}
    )
    assert save_calls["n"] == 0

    p.flush_pending_sync_save()
    assert save_calls["n"] == 1
