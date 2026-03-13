"""
Tests for strategy cross-validation and status promotion.

Verifies:
  - Indicator extraction from strategy graph
  - Cross-validation filtering
  - backtested → validated promotion on pass
  - No promotion when not backtested or when checks fail
  - No indicators found case
  - Endpoint integration
"""

import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.schemas.cross_validation import CrossValidationResponse, IndicatorComparison
from api.schemas.strategy import StrategyGraph, StrategyNode, StrategyNodeData, StrategyEdge, StrategySaveRequest
from api.services.strategy_save_service import StrategySaveService
from api.services.strategy_validation_service import (
    _extract_indicator_types,
    _filter_comparisons,
    validate_strategy,
)


def _make_graph(condition_type="rsi_oversold", params=None):
    return StrategyGraph(
        nodes=[
            StrategyNode(id="u1", data=StrategyNodeData(node_type="universe", universe="SP500", universes=["SP500"])),
            StrategyNode(id="c1", data=StrategyNodeData(node_type="condition", condition_type=condition_type, params=params or {"period": 14, "threshold": 30})),
            StrategyNode(id="o1", data=StrategyNodeData(node_type="output")),
        ],
        edges=[
            StrategyEdge(id="e1", source="u1", target="c1"),
            StrategyEdge(id="e2", source="c1", target="o1"),
        ],
    )


def _make_multi_indicator_graph():
    """Graph with RSI + MACD conditions."""
    return StrategyGraph(
        nodes=[
            StrategyNode(id="u1", data=StrategyNodeData(node_type="universe", universe="SP500", universes=["SP500"])),
            StrategyNode(id="c1", data=StrategyNodeData(node_type="condition", condition_type="rsi_oversold", params={"period": 14, "threshold": 30})),
            StrategyNode(id="c2", data=StrategyNodeData(node_type="condition", condition_type="macd_cross", params={})),
            StrategyNode(id="o1", data=StrategyNodeData(node_type="output")),
        ],
        edges=[
            StrategyEdge(id="e1", source="u1", target="c1"),
            StrategyEdge(id="e2", source="c1", target="c2"),
            StrategyEdge(id="e3", source="c2", target="o1"),
        ],
    )


def _mock_cv_response(all_pass=True):
    """Create a mock CrossValidationResponse."""
    return CrossValidationResponse(
        ticker="AAPL",
        period="1y",
        data_points=252,
        comparisons=[
            IndicatorComparison(name="RSI (14)", our_value=45.0, reference_value=44.5, difference=0.5, pct_difference=1.1, match=all_pass),
            IndicatorComparison(name="MACD Line", our_value=1.2, reference_value=1.2, difference=0.0, pct_difference=0.0, match=True),
            IndicatorComparison(name="MACD Signal", our_value=0.8, reference_value=0.8, difference=0.0, pct_difference=0.0, match=True),
            IndicatorComparison(name="MACD Histogram", our_value=0.4, reference_value=0.4, difference=0.0, pct_difference=0.0, match=True),
            IndicatorComparison(name="BB Upper", our_value=150.0, reference_value=149.5, difference=0.5, pct_difference=0.3, match=True),
            IndicatorComparison(name="BB Middle", our_value=145.0, reference_value=145.0, difference=0.0, pct_difference=0.0, match=True),
            IndicatorComparison(name="BB Lower", our_value=140.0, reference_value=140.5, difference=-0.5, pct_difference=0.4, match=True),
            IndicatorComparison(name="BB Width (%)", our_value=6.9, reference_value=6.2, difference=0.7, pct_difference=11.3, match=True),
        ],
        overall_pass=all_pass,
        known_divergences=[],
    )


@pytest.fixture(autouse=True)
def _use_in_memory_db(monkeypatch):
    from api import database
    from api.services import strategy_save_service

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=test_engine)

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_save_service, "SessionLocal", TestSession)
    monkeypatch.setattr(strategy_save_service, "_strategy_save_service", None)

    database.Base.metadata.create_all(bind=test_engine)
    yield
    database.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def service():
    return StrategySaveService()


class TestExtractIndicatorTypes:
    def test_rsi_condition(self):
        graph = _make_graph("rsi_oversold").model_dump()
        assert _extract_indicator_types(graph) == ["RSI"]

    def test_macd_condition(self):
        graph = _make_graph("macd_cross").model_dump()
        assert _extract_indicator_types(graph) == ["MACD"]

    def test_bb_condition(self):
        graph = _make_graph("bb_squeeze").model_dump()
        assert _extract_indicator_types(graph) == ["BB"]

    def test_multiple_indicators(self):
        graph = _make_multi_indicator_graph().model_dump()
        result = _extract_indicator_types(graph)
        assert "MACD" in result
        assert "RSI" in result

    def test_unknown_condition_type(self):
        graph = _make_graph("volume_spike").model_dump()
        assert _extract_indicator_types(graph) == []

    def test_no_condition_nodes(self):
        graph = StrategyGraph(
            nodes=[
                StrategyNode(id="u1", data=StrategyNodeData(node_type="universe", universe="SP500", universes=["SP500"])),
                StrategyNode(id="o1", data=StrategyNodeData(node_type="output")),
            ],
            edges=[StrategyEdge(id="e1", source="u1", target="o1")],
        ).model_dump()
        assert _extract_indicator_types(graph) == []


class TestFilterComparisons:
    def test_filter_rsi(self):
        comps = _mock_cv_response().comparisons
        result = _filter_comparisons(comps, ["RSI"])
        assert len(result) == 1
        assert result[0].name == "RSI (14)"

    def test_filter_macd(self):
        comps = _mock_cv_response().comparisons
        result = _filter_comparisons(comps, ["MACD"])
        assert len(result) == 3

    def test_filter_bb(self):
        comps = _mock_cv_response().comparisons
        result = _filter_comparisons(comps, ["BB"])
        assert len(result) == 4

    def test_filter_multiple(self):
        comps = _mock_cv_response().comparisons
        result = _filter_comparisons(comps, ["RSI", "MACD"])
        assert len(result) == 4


class TestValidateStrategy:
    @patch("api.services.strategy_validation_service.run_cross_validation")
    def test_backtested_promoted_to_validated(self, mock_cv, service):
        """Backtested strategy with passing checks should be promoted."""
        mock_cv.return_value = _mock_cv_response(all_pass=True)

        saved = service.save_strategy(StrategySaveRequest(name="test", graph=_make_graph()))
        service.update_status(saved.id, "backtested")

        result = validate_strategy(saved.id, ticker="AAPL", period="1y")

        assert result.all_pass is True
        assert result.status_before == "backtested"
        assert result.status_after == "validated"
        assert "promoted" in result.message.lower()

    @patch("api.services.strategy_validation_service.run_cross_validation")
    def test_draft_not_promoted(self, mock_cv, service):
        """Draft strategy should not be promoted even if checks pass."""
        mock_cv.return_value = _mock_cv_response(all_pass=True)

        saved = service.save_strategy(StrategySaveRequest(name="test", graph=_make_graph()))

        result = validate_strategy(saved.id, ticker="AAPL", period="1y")

        assert result.all_pass is True
        assert result.status_before == "draft"
        assert result.status_after == "draft"
        assert "not changed" in result.message.lower()

    @patch("api.services.strategy_validation_service.run_cross_validation")
    def test_failed_checks_no_promotion(self, mock_cv, service):
        """Failed cross-validation should not promote."""
        mock_cv.return_value = _mock_cv_response(all_pass=False)

        saved = service.save_strategy(StrategySaveRequest(name="test", graph=_make_graph()))
        service.update_status(saved.id, "backtested")

        result = validate_strategy(saved.id, ticker="AAPL", period="1y")

        assert result.all_pass is False
        assert result.status_after == "backtested"
        assert "failed" in result.message.lower()

    def test_no_indicators_found(self, service):
        """Strategy with no cross-validatable indicators should return early."""
        graph = StrategyGraph(
            nodes=[
                StrategyNode(id="u1", data=StrategyNodeData(node_type="universe", universe="SP500", universes=["SP500"])),
                StrategyNode(id="c1", data=StrategyNodeData(node_type="condition", condition_type="volume_spike", params={})),
                StrategyNode(id="o1", data=StrategyNodeData(node_type="output")),
            ],
            edges=[
                StrategyEdge(id="e1", source="u1", target="c1"),
                StrategyEdge(id="e2", source="c1", target="o1"),
            ],
        )
        saved = service.save_strategy(StrategySaveRequest(name="test", graph=graph))
        service.update_status(saved.id, "backtested")

        result = validate_strategy(saved.id, ticker="AAPL", period="1y")

        assert result.all_pass is False
        assert result.indicators_tested == []
        assert "no cross-validatable" in result.message.lower()

    def test_strategy_not_found(self):
        """Non-existent strategy should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            validate_strategy("nonexistent")

    @patch("api.services.strategy_validation_service.run_cross_validation")
    def test_multi_indicator_strategy(self, mock_cv, service):
        """Strategy with multiple indicator types tests all."""
        mock_cv.return_value = _mock_cv_response(all_pass=True)

        saved = service.save_strategy(StrategySaveRequest(name="multi", graph=_make_multi_indicator_graph()))
        service.update_status(saved.id, "backtested")

        result = validate_strategy(saved.id, ticker="AAPL", period="1y")

        assert "RSI" in result.indicators_tested
        assert "MACD" in result.indicators_tested
        assert len(result.comparisons) == 4  # 1 RSI + 3 MACD
        assert result.all_pass is True
        assert result.status_after == "validated"
