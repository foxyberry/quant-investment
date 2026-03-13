"""
Tests for strategy comparison and leaderboard.

Verifies:
  - Compare 2-4 strategies with metrics side by side
  - Best-of fields (best_sharpe, best_cagr, etc.)
  - Leaderboard ranking with sort/order/status/limit
  - Edge cases: no results, missing strategies
"""

import sys
import os
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.schemas.strategy import StrategySaveRequest, StrategyGraph, StrategyNode, StrategyNodeData, StrategyEdge
from api.services.strategy_save_service import StrategySaveService
from api.services.strategy_comparison_service import compare_strategies, get_leaderboard
from api.models.strategy_backtest_result import StrategyBacktestResult


def _make_graph():
    return StrategyGraph(
        nodes=[
            StrategyNode(id="u1", data=StrategyNodeData(node_type="universe", universe="SP500", universes=["SP500"])),
            StrategyNode(id="c1", data=StrategyNodeData(node_type="condition", condition_type="rsi_oversold", params={"period": 14, "threshold": 30})),
            StrategyNode(id="o1", data=StrategyNodeData(node_type="output")),
        ],
        edges=[
            StrategyEdge(id="e1", source="u1", target="c1"),
            StrategyEdge(id="e2", source="c1", target="o1"),
        ],
    )


@pytest.fixture(autouse=True)
def _use_in_memory_db(monkeypatch):
    from api import database
    from api.services import strategy_save_service, strategy_backtest_result_service, strategy_comparison_service

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=test_engine)

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_save_service, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_backtest_result_service, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_comparison_service, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_save_service, "_strategy_save_service", None)

    database.Base.metadata.create_all(bind=test_engine)
    yield TestSession
    database.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def service():
    return StrategySaveService()


def _insert_backtest_result(session_factory, strategy_id, sharpe=1.0, cagr=0.1, win_rate=0.5, max_drawdown=0.15, total_return=0.2):
    """Insert a backtest result directly into DB."""
    import uuid
    db = session_factory()
    try:
        row = StrategyBacktestResult(
            id=uuid.uuid4().hex,
            strategy_id=strategy_id,
            ticker="AAPL",
            period="1y",
            initial_cash=10_000_000,
            sharpe_ratio=sharpe,
            cagr=cagr,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            total_return=total_return,
            total_trades=10,
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
    finally:
        db.close()


class TestCompareStrategies:
    def test_compare_two(self, service, _use_in_memory_db):
        s1 = service.save_strategy(StrategySaveRequest(name="Alpha", graph=_make_graph()))
        s2 = service.save_strategy(StrategySaveRequest(name="Beta", graph=_make_graph()))

        _insert_backtest_result(_use_in_memory_db, s1.id, sharpe=1.5, cagr=0.12)
        _insert_backtest_result(_use_in_memory_db, s2.id, sharpe=0.8, cagr=0.20)

        result = compare_strategies([s1.id, s2.id])

        assert len(result.strategies) == 2
        assert result.best_sharpe == s1.id
        assert result.best_cagr == s2.id

    def test_compare_without_results(self, service):
        s1 = service.save_strategy(StrategySaveRequest(name="A", graph=_make_graph()))
        s2 = service.save_strategy(StrategySaveRequest(name="B", graph=_make_graph()))

        result = compare_strategies([s1.id, s2.id])

        assert len(result.strategies) == 2
        assert result.best_sharpe is None

    def test_compare_not_found(self, service):
        s1 = service.save_strategy(StrategySaveRequest(name="A", graph=_make_graph()))

        with pytest.raises(ValueError, match="not found"):
            compare_strategies([s1.id, "nonexistent"])

    def test_compare_too_few(self, service):
        s1 = service.save_strategy(StrategySaveRequest(name="A", graph=_make_graph()))

        with pytest.raises(ValueError, match="At least 2"):
            compare_strategies([s1.id])

    def test_best_lowest_drawdown(self, service, _use_in_memory_db):
        s1 = service.save_strategy(StrategySaveRequest(name="A", graph=_make_graph()))
        s2 = service.save_strategy(StrategySaveRequest(name="B", graph=_make_graph()))

        _insert_backtest_result(_use_in_memory_db, s1.id, max_drawdown=0.30)
        _insert_backtest_result(_use_in_memory_db, s2.id, max_drawdown=0.05)

        result = compare_strategies([s1.id, s2.id])
        assert result.lowest_drawdown == s2.id


class TestLeaderboard:
    def test_leaderboard_sorted_desc(self, service, _use_in_memory_db):
        s1 = service.save_strategy(StrategySaveRequest(name="Alpha", graph=_make_graph()))
        s2 = service.save_strategy(StrategySaveRequest(name="Beta", graph=_make_graph()))
        s3 = service.save_strategy(StrategySaveRequest(name="Gamma", graph=_make_graph()))

        _insert_backtest_result(_use_in_memory_db, s1.id, sharpe=1.5)
        _insert_backtest_result(_use_in_memory_db, s2.id, sharpe=2.0)
        _insert_backtest_result(_use_in_memory_db, s3.id, sharpe=0.5)

        result = get_leaderboard(sort_by="sharpe_ratio", order="desc")

        assert len(result.entries) == 3
        assert result.entries[0].strategy_name == "Beta"
        assert result.entries[0].rank == 1
        assert result.entries[1].strategy_name == "Alpha"
        assert result.entries[2].strategy_name == "Gamma"

    def test_leaderboard_sorted_asc(self, service, _use_in_memory_db):
        s1 = service.save_strategy(StrategySaveRequest(name="A", graph=_make_graph()))
        s2 = service.save_strategy(StrategySaveRequest(name="B", graph=_make_graph()))

        _insert_backtest_result(_use_in_memory_db, s1.id, cagr=0.20)
        _insert_backtest_result(_use_in_memory_db, s2.id, cagr=0.05)

        result = get_leaderboard(sort_by="cagr", order="asc")
        assert result.entries[0].strategy_name == "B"

    def test_leaderboard_status_filter(self, service, _use_in_memory_db):
        s1 = service.save_strategy(StrategySaveRequest(name="A", graph=_make_graph()))
        s2 = service.save_strategy(StrategySaveRequest(name="B", graph=_make_graph()))

        service.update_status(s1.id, "backtested")
        # s2 stays draft

        _insert_backtest_result(_use_in_memory_db, s1.id, sharpe=1.0)
        _insert_backtest_result(_use_in_memory_db, s2.id, sharpe=2.0)

        result = get_leaderboard(status="backtested")
        assert len(result.entries) == 1
        assert result.entries[0].strategy_name == "A"

    def test_leaderboard_limit(self, service, _use_in_memory_db):
        for i in range(5):
            s = service.save_strategy(StrategySaveRequest(name=f"S{i}", graph=_make_graph()))
            _insert_backtest_result(_use_in_memory_db, s.id, sharpe=float(i))

        result = get_leaderboard(limit=3)
        assert len(result.entries) == 3

    def test_leaderboard_empty(self):
        result = get_leaderboard()
        assert len(result.entries) == 0
        assert result.total_count == 0

    def test_leaderboard_invalid_sort(self):
        with pytest.raises(ValueError, match="Invalid sort_by"):
            get_leaderboard(sort_by="invalid_metric")

    def test_leaderboard_invalid_order(self):
        with pytest.raises(ValueError, match="Invalid order"):
            get_leaderboard(order="random")
