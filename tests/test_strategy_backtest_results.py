"""
Tests for strategy backtest result persistence.

Verifies:
  - Model creation and defaults
  - Service: save, list, get_latest
  - Schema response structure
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.schemas.backtest import (
    BacktestMetrics,
    EquityPoint,
    GraphBacktestResponse,
    TradeRecord,
)
from api.schemas.strategy_backtest_result import (
    StrategyBacktestResultResponse,
    StrategyBacktestResultsListResponse,
)
from api.services.strategy_backtest_result_service import (
    get_latest,
    get_results,
    save_backtest_result,
)


def _make_response(ticker: str = "AAPL", period: str = "1y") -> GraphBacktestResponse:
    return GraphBacktestResponse(
        ticker=ticker,
        strategy="graph",
        period=period,
        cash=10_000_000,
        metrics=BacktestMetrics(
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            mdd=0.15,
            win_rate=0.6,
            profit_factor=1.8,
            cagr=0.12,
            total_return=0.25,
            num_trades=42,
            avg_trade_return=0.006,
            max_consecutive_wins=5,
            max_consecutive_losses=3,
        ),
        trades=[
            TradeRecord(
                entry_date="2024-01-01", exit_date="2024-02-01",
                entry_price=100.0, exit_price=110.0,
                pnl=1000.0, return_pct=0.10, size=100,
            ),
        ],
        equity_curve=[
            EquityPoint(date="2024-01-01", equity=10_000_000),
            EquityPoint(date="2024-12-31", equity=12_500_000),
        ],
        compiled_conditions=["rsi_oversold", "ma_cross_up"],
        skipped_conditions=["min_market_cap"],
        warnings=["Universe node ignored in backtest"],
    )


@pytest.fixture(autouse=True)
def _use_in_memory_db(monkeypatch):
    """Override database to use in-memory SQLite for tests."""
    from api import database
    from api.services import strategy_backtest_result_service

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=test_engine)

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_backtest_result_service, "SessionLocal", TestSession)

    database.Base.metadata.create_all(bind=test_engine)
    yield
    database.Base.metadata.drop_all(bind=test_engine)


# --- Tests: Save ---

class TestSaveResult:
    def test_save_returns_response(self):
        resp = _make_response()
        result = save_backtest_result("strategy_abc", resp)
        assert isinstance(result, StrategyBacktestResultResponse)
        assert result.strategy_id == "strategy_abc"
        assert result.ticker == "AAPL"
        assert result.period == "1y"

    def test_save_persists_metrics(self):
        resp = _make_response()
        result = save_backtest_result("strat1", resp)
        assert result.sharpe_ratio == 1.5
        assert result.cagr == 0.12
        assert result.max_drawdown == 0.15
        assert result.win_rate == 0.6
        assert result.total_return == 0.25
        assert result.total_trades == 42

    def test_save_persists_trades(self):
        resp = _make_response()
        result = save_backtest_result("strat2", resp)
        assert len(result.trades) == 1
        assert result.trades[0].entry_price == 100.0

    def test_save_persists_equity_curve(self):
        resp = _make_response()
        result = save_backtest_result("strat3", resp)
        assert len(result.equity_curve) == 2

    def test_save_persists_conditions(self):
        resp = _make_response()
        result = save_backtest_result("strat4", resp)
        assert result.compiled_conditions == ["rsi_oversold", "ma_cross_up"]
        assert result.skipped_conditions == ["min_market_cap"]
        assert result.warnings == ["Universe node ignored in backtest"]

    def test_save_generates_unique_id(self):
        resp = _make_response()
        r1 = save_backtest_result("strat5", resp)
        r2 = save_backtest_result("strat5", resp)
        assert r1.id != r2.id


# --- Tests: List ---

class TestListResults:
    def test_list_empty(self):
        results = get_results("nonexistent")
        assert results == []

    def test_list_multiple(self):
        resp = _make_response()
        save_backtest_result("strat_list", resp)
        save_backtest_result("strat_list", _make_response(ticker="MSFT"))

        results = get_results("strat_list")
        assert len(results) == 2

    def test_list_ordered_newest_first(self):
        save_backtest_result("strat_order", _make_response(ticker="A"))
        save_backtest_result("strat_order", _make_response(ticker="B"))

        results = get_results("strat_order")
        # Most recent first — B was saved last
        assert results[0].ticker == "B"
        assert results[1].ticker == "A"

    def test_list_filters_by_strategy_id(self):
        save_backtest_result("strat_a", _make_response())
        save_backtest_result("strat_b", _make_response())

        results_a = get_results("strat_a")
        results_b = get_results("strat_b")
        assert len(results_a) == 1
        assert len(results_b) == 1


# --- Tests: Get Latest ---

class TestGetLatest:
    def test_latest_returns_none_when_empty(self):
        result = get_latest("nonexistent")
        assert result is None

    def test_latest_returns_most_recent(self):
        save_backtest_result("strat_latest", _make_response(ticker="OLD"))
        save_backtest_result("strat_latest", _make_response(ticker="NEW"))

        latest = get_latest("strat_latest")
        assert latest is not None
        assert latest.ticker == "NEW"


# --- Tests: Schema ---

class TestSchema:
    def test_list_response_model(self):
        resp = StrategyBacktestResultsListResponse(
            strategy_id="abc",
            results=[],
            total_count=0,
        )
        assert resp.strategy_id == "abc"
        assert resp.total_count == 0
