"""
Tests for strategy service: graph building and condition mapping.
"""

import pytest
import numpy as np
import pandas as pd

from api.schemas.strategy import (
    PortfolioConstructionConfig,
    RankingConfig,
    StrategyGraph,
    StrategyNode,
    StrategyNodeData,
    StrategyEdge,
    StrategyResultItem,
)
from api.services.strategy_service import (
    _build_ranking_outputs,
    build_conditions_from_graph,
    get_available_conditions,
    CONDITION_CLASS_MAP,
    CONDITION_METADATA,
    _build_weighted_portfolio,
    _compute_inverse_vol_weights,
    _compute_risk_parity_weights,
    _build_condition,
    execute_strategy,
    execute_strategy_with_progress,
)
from screener.conditions import (
    AndCondition,
    OrCondition,
    NotCondition,
    MinPriceCondition,
    RSIOversoldCondition,
    MATouchCondition,
    VolumeSpikeCondition,
)


class TestConditionClassMap:
    """Test CONDITION_CLASS_MAP completeness and correctness."""

    def test_all_metadata_keys_in_class_map(self):
        """Every key in CONDITION_METADATA must exist in CONDITION_CLASS_MAP."""
        for key in CONDITION_METADATA:
            assert key in CONDITION_CLASS_MAP, f"Missing class mapping for: {key}"

    def test_all_class_map_keys_in_metadata(self):
        """Every key in CONDITION_CLASS_MAP should have metadata."""
        for key in CONDITION_CLASS_MAP:
            assert key in CONDITION_METADATA, f"Missing metadata for: {key}"

    def test_class_map_not_empty(self):
        assert len(CONDITION_CLASS_MAP) >= 25


class TestBuildCondition:
    """Test single condition instantiation."""

    def test_min_price(self):
        cond = _build_condition("min_price", {"min_price": 5000})
        assert isinstance(cond, MinPriceCondition)
        assert cond.min_price == 5000

    def test_rsi_oversold(self):
        cond = _build_condition("rsi_oversold", {"threshold": 25, "period": 14})
        assert isinstance(cond, RSIOversoldCondition)
        assert cond.threshold == 25

    def test_ma_touch_default(self):
        cond = _build_condition("ma_touch", {"period": 160, "threshold": 0.02})
        assert isinstance(cond, MATouchCondition)
        assert cond.period == 160

    def test_unknown_condition_type_raises(self):
        with pytest.raises(ValueError, match="Unknown condition type"):
            _build_condition("nonexistent", {})

    def test_param_type_coercion(self):
        """String values should be coerced to correct types."""
        cond = _build_condition("min_price", {"min_price": "5000"})
        assert isinstance(cond, MinPriceCondition)
        assert cond.min_price == 5000.0


class TestBuildConditionsFromGraph:
    """Test graph-to-conditions conversion."""

    def _make_graph(self, nodes, edges):
        return StrategyGraph(
            nodes=[StrategyNode(id=n["id"], data=StrategyNodeData(**n["data"])) for n in nodes],
            edges=[StrategyEdge(**e) for e in edges],
        )

    def test_simple_single_condition(self):
        """Universe -> Condition -> Output."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 5000}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "c1"},
                {"id": "e2", "source": "c1", "target": "o1"},
            ],
        )
        conditions, universe = build_conditions_from_graph(graph)
        assert universe == "KOSPI"
        assert len(conditions) == 1
        assert isinstance(conditions[0], MinPriceCondition)

    def test_two_conditions_direct_to_output(self):
        """Two conditions connected directly to output (implicit AND)."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "SP500"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "c2", "data": {"node_type": "condition", "condition_type": "rsi_oversold", "params": {"threshold": 30, "period": 14}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "c1"},
                {"id": "e2", "source": "c1", "target": "o1"},
                {"id": "e3", "source": "c2", "target": "o1"},
            ],
        )
        conditions, universe = build_conditions_from_graph(graph)
        assert universe == "SP500"
        assert len(conditions) == 2

    def test_and_logic_node(self):
        """Two conditions -> AND gate -> Output."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 5000}}},
                {"id": "c2", "data": {"node_type": "condition", "condition_type": "volume_spike", "params": {"multiplier": 2.0, "period": 20}}},
                {"id": "l1", "data": {"node_type": "logic", "logic_operator": "and"}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "c1", "target": "l1"},
                {"id": "e2", "source": "c2", "target": "l1"},
                {"id": "e3", "source": "l1", "target": "o1"},
            ],
        )
        conditions, universe = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], AndCondition)

    def test_or_logic_node(self):
        """Two conditions -> OR gate -> Output."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "rsi_oversold", "params": {"threshold": 30}}},
                {"id": "c2", "data": {"node_type": "condition", "condition_type": "ma_touch", "params": {"period": 200}}},
                {"id": "l1", "data": {"node_type": "logic", "logic_operator": "or"}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "c1", "target": "l1"},
                {"id": "e2", "source": "c2", "target": "l1"},
                {"id": "e3", "source": "l1", "target": "o1"},
            ],
        )
        conditions, universe = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], OrCondition)

    def test_not_logic_node(self):
        """Condition -> NOT gate -> Output."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "rsi_overbought", "params": {"threshold": 70}}},
                {"id": "l1", "data": {"node_type": "logic", "logic_operator": "not"}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "c1", "target": "l1"},
                {"id": "e2", "source": "l1", "target": "o1"},
            ],
        )
        conditions, universe = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], NotCondition)

    def test_nested_logic(self):
        """(A AND B) -> Output, where A and B feed into AND gate."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 1000}}},
                {"id": "c2", "data": {"node_type": "condition", "condition_type": "rsi_oversold", "params": {"threshold": 30}}},
                {"id": "c3", "data": {"node_type": "condition", "condition_type": "volume_spike", "params": {"multiplier": 3.0}}},
                {"id": "l1", "data": {"node_type": "logic", "logic_operator": "and"}},
                {"id": "l2", "data": {"node_type": "logic", "logic_operator": "or"}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "c1", "target": "l1"},
                {"id": "e2", "source": "c2", "target": "l1"},
                {"id": "e3", "source": "l1", "target": "l2"},
                {"id": "e4", "source": "c3", "target": "l2"},
                {"id": "e5", "source": "l2", "target": "o1"},
            ],
        )
        conditions, _ = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], OrCondition)

    def test_no_output_node_raises(self):
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 5000}}},
            ],
            edges=[],
        )
        with pytest.raises(ValueError, match="Output node"):
            build_conditions_from_graph(graph)

    def test_default_universe(self):
        """Graph without universe node defaults to KOSPI."""
        graph = self._make_graph(
            nodes=[
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 5000}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "c1", "target": "o1"},
            ],
        )
        _, universe = build_conditions_from_graph(graph)
        assert universe == "KOSPI"

    def test_universe_node_multi_input_keeps_primary_for_compatibility(self):
        """Universe node with comma-separated input should normalize to primary universe."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "kospi,kosdaq"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 5000}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "c1"},
                {"id": "e2", "source": "c1", "target": "o1"},
            ],
        )
        _, universe = build_conditions_from_graph(graph)
        assert universe == "KOSPI"

    def test_group_and_with_child_node_ids(self):
        """AND group with child_node_ids (new container approach)."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "g1", "data": {"node_type": "logic", "logic_operator": "and", "child_node_ids": ["c1", "c2"]}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 5000}}},
                {"id": "c2", "data": {"node_type": "condition", "condition_type": "volume_spike", "params": {"multiplier": 2.0, "period": 20}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "g1"},
                {"id": "e2", "source": "g1", "target": "o1"},
            ],
        )
        conditions, universe = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], AndCondition)

    def test_group_or_with_child_node_ids(self):
        """OR group with child_node_ids."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "g1", "data": {"node_type": "logic", "logic_operator": "or", "child_node_ids": ["c1", "c2"]}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "rsi_oversold", "params": {"threshold": 30}}},
                {"id": "c2", "data": {"node_type": "condition", "condition_type": "ma_touch", "params": {"period": 200}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "g1"},
                {"id": "e2", "source": "g1", "target": "o1"},
            ],
        )
        conditions, universe = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], OrCondition)

    def test_group_not_with_child_node_ids(self):
        """NOT group with single child_node_id."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "g1", "data": {"node_type": "logic", "logic_operator": "not", "child_node_ids": ["c1"]}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "rsi_overbought", "params": {"threshold": 70}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "g1"},
                {"id": "e2", "source": "g1", "target": "o1"},
            ],
        )
        conditions, universe = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], NotCondition)

    def test_group_single_child_returns_unwrapped(self):
        """AND group with a single child returns the condition directly."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "g1", "data": {"node_type": "logic", "logic_operator": "and", "child_node_ids": ["c1"]}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 5000}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "g1"},
                {"id": "e2", "source": "g1", "target": "o1"},
            ],
        )
        conditions, _ = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], MinPriceCondition)

    def test_edge_based_logic_still_works(self):
        """Backward compatibility: edge-based AND gate still works."""
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 5000}}},
                {"id": "c2", "data": {"node_type": "condition", "condition_type": "volume_spike", "params": {"multiplier": 2.0}}},
                {"id": "l1", "data": {"node_type": "logic", "logic_operator": "and"}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "c1", "target": "l1"},
                {"id": "e2", "source": "c2", "target": "l1"},
                {"id": "e3", "source": "l1", "target": "o1"},
            ],
        )
        conditions, _ = build_conditions_from_graph(graph)
        assert len(conditions) == 1
        assert isinstance(conditions[0], AndCondition)


class TestGetAvailableConditions:
    """Test the conditions listing function."""

    def test_returns_conditions(self):
        conditions = get_available_conditions()
        assert len(conditions) >= 25

    def test_condition_has_required_fields(self):
        conditions = get_available_conditions()
        for c in conditions:
            assert c.key
            assert c.label
            assert c.category

    def test_categories_present(self):
        conditions = get_available_conditions()
        categories = set(c.category for c in conditions)
        assert "Price" in categories
        assert "Volume" in categories
        assert "Moving Average" in categories
        assert "RSI" in categories
        assert "Accumulation" in categories
        assert "Breakout" in categories


class TestExecuteStrategyMultiUniverse:
    """Test multi-universe execution semantics and precedence."""

    def _make_graph(self, nodes, edges):
        return StrategyGraph(
            nodes=[StrategyNode(id=n["id"], data=StrategyNodeData(**n["data"])) for n in nodes],
            edges=[StrategyEdge(**e) for e in edges],
        )

    def test_request_override_has_priority_over_graph_universe(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "SP500"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 1000}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "c1"},
                {"id": "e2", "source": "c1", "target": "o1"},
            ],
        )

        captured = {"universe_input": None}

        def _mock_get_tickers_for_universes(self, universe_input, fail_fast=False):
            captured["universe_input"] = universe_input
            return ["005930.KS", "000660.KS"]

        class _MockScreener:
            def run(self, tickers, show_progress, return_all, progress_callback=None):
                return []

        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            _mock_get_tickers_for_universes,
        )
        monkeypatch.setattr(
            "api.services.strategy_service.StockScreener",
            lambda **kwargs: _MockScreener(),
        )

        result = execute_strategy(
            graph=graph,
            universe_override="KOSPI",
            universe_overrides=["KOSPI", "KOSDAQ"],
        )

        assert captured["universe_input"] == ["KOSPI", "KOSDAQ"]
        assert result["universe"] == "KOSPI"
        assert result["universes"] == ["KOSPI", "KOSDAQ"]
        assert result["total_count"] == 2
        assert result["screened_count"] == 2

    def test_graph_multi_universe_used_when_no_override(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "SP500,NASDAQ100"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "c1"},
                {"id": "e2", "source": "c1", "target": "o1"},
            ],
        )

        captured = {"universe_input": None}

        def _mock_get_tickers_for_universes(self, universe_input, fail_fast=False):
            captured["universe_input"] = universe_input
            return ["AAPL", "MSFT", "NVDA"]

        class _MockScreener:
            def run(self, tickers, show_progress, return_all, progress_callback=None):
                return []

        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            _mock_get_tickers_for_universes,
        )
        monkeypatch.setattr(
            "api.services.strategy_service.StockScreener",
            lambda **kwargs: _MockScreener(),
        )

        result = execute_strategy(graph=graph)
        assert captured["universe_input"] == ["SP500", "NASDAQ100"]
        assert result["universe"] == "SP500"
        assert result["universes"] == ["SP500", "NASDAQ100"]
        assert result["total_count"] == 3
        assert result["screened_count"] == 3

    def test_duplicate_universe_inputs_are_normalized_stably(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[{"id": "e1", "source": "c1", "target": "o1"}],
        )

        captured = {"universe_input": None}

        def _mock_get_tickers_for_universes(self, universe_input, fail_fast=False):
            captured["universe_input"] = universe_input
            return ["005930.KS", "AAPL"]

        class _MockScreener:
            def run(self, tickers, show_progress, return_all, progress_callback=None):
                return []

        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            _mock_get_tickers_for_universes,
        )
        monkeypatch.setattr(
            "api.services.strategy_service.StockScreener",
            lambda **kwargs: _MockScreener(),
        )

        result = execute_strategy(
            graph=graph,
            universe_overrides=["kospi", "SP500", "KOSPI", "sp500"],
        )
        assert captured["universe_input"] == ["KOSPI", "SP500"]
        assert result["universes"] == ["KOSPI", "SP500"]
        assert result["universe"] == "KOSPI"

    def test_total_and_matched_count_follow_result_sizes(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[{"id": "e1", "source": "c1", "target": "o1"}],
        )

        class _Result:
            def __init__(self, ticker: str, matched: bool):
                self.ticker = ticker
                self.name = ticker
                self.current_price = 100.0
                self.matched = matched
                self.condition_results = [
                    type(
                        "_ConditionResult",
                        (),
                        {
                            "condition_name": "min_price",
                            "matched": matched,
                            "details": {},
                        },
                    )()
                ]

        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            lambda self, universe_input, fail_fast=False: ["005930.KS", "AAPL", "MSFT"],
        )

        class _MockScreener:
            def run(self, tickers, show_progress, return_all, progress_callback=None):
                return [_Result("005930.KS", True), _Result("AAPL", True), _Result("MSFT", True)]

        monkeypatch.setattr(
            "api.services.strategy_service.StockScreener",
            lambda **kwargs: _MockScreener(),
        )

        result = execute_strategy(graph=graph, universe_overrides=["KOSPI", "SP500"])
        assert result["total_count"] == 3
        assert result["matched_count"] == 3
        assert len(result["results"]) == 3

    def test_partial_market_fetch_failure_is_allowed_when_tickers_exist(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[{"id": "e1", "source": "c1", "target": "o1"}],
        )

        # Simulate service already degraded one market and returned remaining tickers.
        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            lambda self, universe_input, fail_fast=False: ["005930.KS"],
        )

        class _MockScreener:
            def run(self, tickers, show_progress, return_all, progress_callback=None):
                return []

        monkeypatch.setattr(
            "api.services.strategy_service.StockScreener",
            lambda **kwargs: _MockScreener(),
        )

        result = execute_strategy(graph=graph, universe_overrides=["KOSPI", "KOSDAQ"])
        assert result["total_count"] == 1
        assert result["screened_count"] == 1

    def test_progress_total_matches_merged_ticker_count(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[{"id": "e1", "source": "c1", "target": "o1"}],
        )

        progress_events = []

        def _mock_get_tickers_for_universes(self, universe_input, fail_fast=False):
            return ["005930.KS", "AAPL"]

        class _MockScreener:
            def run(self, tickers, show_progress, return_all, progress_callback=None):
                if progress_callback is not None:
                    progress_callback(1, len(tickers), 0)
                    progress_callback(len(tickers), len(tickers), 0)
                return []

        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            _mock_get_tickers_for_universes,
        )
        monkeypatch.setattr(
            "api.services.strategy_service.StockScreener",
            lambda **kwargs: _MockScreener(),
        )

        result = execute_strategy_with_progress(
            graph=graph,
            universe_overrides=["KOSPI", "SP500"],
            progress_callback=lambda p, t, m: progress_events.append((p, t, m)),
        )

        assert progress_events
        assert progress_events[-1][1] == 2
        assert result["total_count"] == 2
        assert result["screened_count"] == 2

    def test_execute_strategy_guardrail_rejects_oversized_universe(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[{"id": "e1", "source": "c1", "target": "o1"}],
        )

        oversized = [f"T{i:04d}" for i in range(4001)]
        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            lambda self, universe_input, fail_fast=False: oversized,
        )

        with pytest.raises(ValueError, match="Target universe too large"):
            execute_strategy(
                graph=graph,
                universe_overrides=["KOSPI", "KOSDAQ"],
            )


class TestExecuteStrategySectorPolicy:
    """Test sector behavior under mixed multi-market execution."""

    def _make_graph(self, nodes, edges):
        return StrategyGraph(
            nodes=[StrategyNode(id=n["id"], data=StrategyNodeData(**n["data"])) for n in nodes],
            edges=[StrategyEdge(**e) for e in edges],
        )

    def test_sector_filters_only_kr_tickers_in_mixed_universes(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "u1", "data": {"node_type": "universe", "universe": "KOSPI"}},
                {"id": "s1", "data": {"node_type": "sector", "sector": "전기전자"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "u1", "target": "c1"},
                {"id": "e2", "source": "s1", "target": "c1"},
                {"id": "e3", "source": "c1", "target": "o1"},
            ],
        )

        captured = {"tickers": None}

        def _mock_get_tickers_for_universes(self, universe_input, fail_fast=False):
            return ["005930.KS", "000660.KS", "AAPL"]

        class _MockSectorFetcher:
            def get_sector_tickers(self, market: str, sector: str):
                return ["005930.KS"]

        class _MockScreener:
            def run(self, tickers, show_progress, return_all, progress_callback=None):
                captured["tickers"] = tickers
                return []

        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            _mock_get_tickers_for_universes,
        )
        monkeypatch.setattr(
            "api.services.strategy_service.get_sector_fetcher",
            lambda: _MockSectorFetcher(),
        )
        monkeypatch.setattr(
            "api.services.strategy_service.StockScreener",
            lambda **kwargs: _MockScreener(),
        )

        result = execute_strategy(
            graph=graph,
            universe_overrides=["KOSPI", "SP500"],
        )

        assert captured["tickers"] == ["005930.KS", "AAPL"]
        assert result["total_count"] == 3
        assert result["screened_count"] == 2

    def test_sector_with_non_kr_universe_fails_fast(self, monkeypatch):
        graph = self._make_graph(
            nodes=[
                {"id": "s1", "data": {"node_type": "sector", "sector": "전기전자"}},
                {"id": "c1", "data": {"node_type": "condition", "condition_type": "min_price", "params": {"min_price": 10}}},
                {"id": "o1", "data": {"node_type": "output"}},
            ],
            edges=[
                {"id": "e1", "source": "s1", "target": "c1"},
                {"id": "e2", "source": "c1", "target": "o1"},
            ],
        )

        monkeypatch.setattr(
            "api.services.strategy_service.ScreeningService.get_tickers_for_universes",
            lambda self, universe_input, fail_fast=False: ["AAPL", "MSFT"],
        )

        with pytest.raises(ValueError, match="Sector filtering is supported only when KR universes"):
            execute_strategy(
                graph=graph,
                universe_overrides=["SP500"],
            )


class TestPortfolioConstruction:
    def test_inverse_vol_weights_are_normalized(self):
        vols = np.array([0.2, 0.4, 0.8], dtype=float)
        weights = _compute_inverse_vol_weights(vols)
        assert len(weights) == 3
        assert abs(float(weights.sum()) - 1.0) < 1e-9
        assert weights[0] > weights[1] > weights[2]

    def test_risk_parity_weights_are_normalized(self):
        cov = np.array(
            [
                [0.04, 0.01, 0.0],
                [0.01, 0.09, 0.0],
                [0.0, 0.0, 0.16],
            ],
            dtype=float,
        )
        weights = _compute_risk_parity_weights(cov)
        assert len(weights) == 3
        assert abs(float(weights.sum()) - 1.0) < 1e-8
        assert all(w >= 0 for w in weights)

    def test_weighted_portfolio_falls_back_when_history_missing(self, monkeypatch):
        monkeypatch.setattr(
            "api.services.strategy_service._estimate_return_matrix",
            lambda tickers, lookback_days, probe_conditions: pd.DataFrame(),
        )
        items = [
            StrategyResultItem(
                ticker="AAPL",
                name="Apple",
                current_price=100.0,
                matched=True,
                conditions=[],
            ),
            StrategyResultItem(
                ticker="MSFT",
                name="Microsoft",
                current_price=200.0,
                matched=True,
                conditions=[],
            ),
        ]
        weighted, meta = _build_weighted_portfolio(
            final_items=items,
            leaf_conditions=[MinPriceCondition(1)],
            config=PortfolioConstructionConfig(mode="risk_parity", lookback_days=60, max_assets=10),
        )
        assert len(weighted) == 2
        assert abs(sum(w.weight for w in weighted) - 1.0) < 1e-8
        assert meta is not None
        assert meta.mode_applied == "equal_weight"
        assert meta.fallback_reason == "insufficient_return_history"


class TestRankingOutputs:
    def test_build_ranking_outputs_generates_rank_and_long_short_baskets(self):
        items = [
            StrategyResultItem(ticker="AAPL", name="Apple", current_price=180.0, matched=True, conditions=[]),
            StrategyResultItem(ticker="MSFT", name="Microsoft", current_price=420.0, matched=True, conditions=[]),
            StrategyResultItem(ticker="TSLA", name="Tesla", current_price=220.0, matched=True, conditions=[]),
            StrategyResultItem(ticker="INTC", name="Intel", current_price=35.0, matched=True, conditions=[]),
        ]
        ranked, baskets = _build_ranking_outputs(
            final_items=items,
            ranking_config=RankingConfig(
                metric_key="current_price",
                direction="desc",
                top_percent=25,
                bottom_percent=25,
                max_assets=10,
                long_short=True,
            ),
        )
        assert len(ranked) == 4
        assert ranked[0].ticker == "MSFT"
        assert baskets is not None
        assert len(baskets.long) == 1
        assert len(baskets.short) == 1
        assert baskets.long[0].ticker == "MSFT"
        assert baskets.short[0].ticker == "INTC"

    def test_build_ranking_outputs_can_rank_by_condition_detail_key(self):
        items = [
            StrategyResultItem(
                ticker="AAA",
                name="AAA",
                current_price=10.0,
                matched=True,
                conditions=[{"details": {"quality_score": 80}}],
            ),
            StrategyResultItem(
                ticker="BBB",
                name="BBB",
                current_price=10.0,
                matched=True,
                conditions=[{"details": {"quality_score": 60}}],
            ),
        ]
        ranked, baskets = _build_ranking_outputs(
            final_items=items,
            ranking_config=RankingConfig(metric_key="quality_score", direction="desc", top_percent=50, bottom_percent=0, long_short=False),
        )
        assert len(ranked) == 2
        assert ranked[0].ticker == "AAA"
        assert baskets is not None
        assert len(baskets.long) == 1
        assert len(baskets.short) == 0
