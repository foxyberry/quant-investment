"""
Tests for auto-promote strategy status after graph backtest.

Verifies:
  - GraphBacktestRequest accepts strategy_id
  - GraphBacktestResponse includes strategy_status
  - After backtest with strategy_id: result saved + draft → backtested
  - Non-draft status is not changed
  - Missing strategy_id: no side effects
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.schemas.backtest import GraphBacktestRequest, GraphBacktestResponse
from api.schemas.strategy import StrategyGraph, StrategyNode, StrategyNodeData, StrategyEdge, StrategySaveRequest
from api.services.strategy_save_service import StrategySaveService
from api.services.strategy_backtest_result_service import get_results


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
    from api.services import strategy_save_service, strategy_backtest_result_service

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=test_engine)

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_save_service, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_backtest_result_service, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_save_service, "_strategy_save_service", None)

    database.Base.metadata.create_all(bind=test_engine)
    yield
    database.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def service():
    return StrategySaveService()


class TestSchemaFields:
    def test_request_accepts_strategy_id(self):
        req = GraphBacktestRequest(
            graph=_make_graph(),
            ticker="AAPL",
            strategy_id="abc123",
        )
        assert req.strategy_id == "abc123"

    def test_request_strategy_id_optional(self):
        req = GraphBacktestRequest(graph=_make_graph(), ticker="AAPL")
        assert req.strategy_id is None

    def test_response_has_strategy_status(self):
        from api.schemas.backtest import BacktestMetrics
        resp = GraphBacktestResponse(
            ticker="AAPL", strategy="graph", period="1y", cash=10_000_000,
            metrics=BacktestMetrics(
                sharpe_ratio=1.0, sortino_ratio=1.0, mdd=0.1, win_rate=0.5,
                profit_factor=1.2, cagr=0.08, total_return=0.15, num_trades=10,
                avg_trade_return=0.01, max_consecutive_wins=3, max_consecutive_losses=2,
            ),
            strategy_status="backtested",
        )
        assert resp.strategy_status == "backtested"


class TestAutoPromote:
    def test_draft_promoted_to_backtested(self, service):
        """run_graph_backtest with strategy_id should promote draft → backtested."""
        from api.services.backtest_service import run_graph_backtest

        saved = service.save_strategy(StrategySaveRequest(name="test", graph=_make_graph()))
        assert saved.status == "draft"

        request = GraphBacktestRequest(
            graph=_make_graph(),
            ticker="AAPL",
            strategy_id=saved.id,
        )
        response = run_graph_backtest(request)

        assert response.strategy_status == "backtested"

        # Verify status persisted
        updated = service.get_strategy(saved.id)
        assert updated.status == "backtested"

    def test_result_persisted(self, service):
        """Backtest result should be saved to DB."""
        from api.services.backtest_service import run_graph_backtest

        saved = service.save_strategy(StrategySaveRequest(name="test2", graph=_make_graph()))

        request = GraphBacktestRequest(
            graph=_make_graph(),
            ticker="AAPL",
            strategy_id=saved.id,
        )
        run_graph_backtest(request)

        results = get_results(saved.id)
        assert len(results) == 1
        assert results[0].ticker == "AAPL"

    def test_non_draft_not_promoted(self, service):
        """Already-backtested strategy should not change status."""
        from api.services.backtest_service import run_graph_backtest

        saved = service.save_strategy(StrategySaveRequest(name="test3", graph=_make_graph()))
        service.update_status(saved.id, "backtested")

        request = GraphBacktestRequest(
            graph=_make_graph(),
            ticker="AAPL",
            strategy_id=saved.id,
        )
        response = run_graph_backtest(request)

        # Status stays backtested (not re-promoted)
        assert response.strategy_status == "backtested"

    def test_no_strategy_id_no_side_effects(self):
        """Without strategy_id, no persistence or promotion happens."""
        from api.services.backtest_service import run_graph_backtest

        request = GraphBacktestRequest(
            graph=_make_graph(),
            ticker="AAPL",
        )
        response = run_graph_backtest(request)

        assert response.strategy_status is None
