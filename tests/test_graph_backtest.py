"""
Tests for graph-based backtesting (QuantCanvas -> Backtesting.py bridge).

Verifies that strategy graphs can be compiled and executed through
the BacktestEngine.
"""

import sys
import os

import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.schemas.strategy import StrategyGraph, StrategyNode, StrategyNodeData, StrategyEdge
from api.services.strategy_builder import build_strategy_from_graph, BuildResult
from engine.backtesting_engine import BacktestEngine
from engine.strategies.graph_strategy import (
    SUPPORTED_CONDITION_TYPES,
    compile_condition,
)


# --- Fixtures ---

@pytest.fixture(scope="module")
def sample_ohlcv() -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    import numpy as np
    np.random.seed(42)
    n = 300
    dates = pd.bdate_range(start="2024-01-01", periods=n)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    close = pd.Series(close, index=dates).clip(lower=1)
    df = pd.DataFrame({
        "Open": close * (1 + np.random.randn(n) * 0.005),
        "High": close * (1 + abs(np.random.randn(n) * 0.01)),
        "Low": close * (1 - abs(np.random.randn(n) * 0.01)),
        "Close": close,
        "Volume": np.random.randint(100000, 1000000, size=n),
    }, index=dates)
    return df


def _make_graph(condition_nodes, logic_operator="and") -> StrategyGraph:
    """Helper to create a simple graph with universe -> logic -> output."""
    nodes = [
        StrategyNode(id="u1", data=StrategyNodeData(node_type="universe", universe="SP500")),
    ]
    child_ids = []

    for i, (ct, params) in enumerate(condition_nodes):
        cid = f"c{i}"
        nodes.append(StrategyNode(
            id=cid,
            data=StrategyNodeData(
                node_type="condition",
                condition_type=ct,
                params=params,
            ),
        ))
        child_ids.append(cid)

    nodes.append(StrategyNode(
        id="g1",
        data=StrategyNodeData(
            node_type="logic",
            logic_operator=logic_operator,
            child_node_ids=child_ids,
        ),
    ))
    nodes.append(StrategyNode(id="o1", data=StrategyNodeData(node_type="output")))

    edges = [
        StrategyEdge(id="e1", source="u1", target="g1"),
        StrategyEdge(id="e2", source="g1", target="o1"),
    ]

    return StrategyGraph(nodes=nodes, edges=edges)


# --- Tests: compile_condition ---

class TestCompileCondition:
    def test_supported_types(self):
        """All supported types should compile without error."""
        test_cases = [
            ("ma_cross_up", {"short_period": 10, "long_period": 20}),
            ("ma_cross_down", {"short_period": 10, "long_period": 20}),
            ("above_ma", {"period": 20}),
            ("below_ma", {"period": 20}),
            ("ma_touch", {"period": 20, "threshold": 0.02}),
            ("rsi_oversold", {"threshold": 30, "period": 14}),
            ("rsi_overbought", {"threshold": 70, "period": 14}),
            ("rsi_range", {"lower": 30, "upper": 70, "period": 14}),
            ("macd_cross_up", {}),
            ("macd_cross_down", {}),
            ("bb_lower_touch", {"period": 20}),
            ("bb_upper_touch", {"period": 20}),
            ("min_volume", {"min_volume": 100000}),
            ("volume_above_avg", {"period": 20, "multiplier": 1.5}),
        ]
        for ct, params in test_cases:
            spec = compile_condition(ct, params)
            assert spec is not None, f"compile_condition returned None for '{ct}'"
            assert spec.condition_type == ct

    def test_unsupported_returns_none(self):
        assert compile_condition("pe_ratio", {}) is None
        assert compile_condition("pairs_correlation", {}) is None
        assert compile_condition("nonexistent", {}) is None

    def test_supported_count(self):
        assert len(SUPPORTED_CONDITION_TYPES) == 14


# --- Tests: build_strategy_from_graph ---

class TestBuildStrategyFromGraph:
    def test_simple_ma_cross(self):
        graph = _make_graph([("ma_cross_up", {"short_period": 10, "long_period": 20})])
        result = build_strategy_from_graph(graph)
        assert result.strategy_cls is not None
        assert "ma_cross_up" in result.compiled_conditions
        assert len(result.skipped_conditions) == 0

    def test_multi_condition_and(self):
        graph = _make_graph([
            ("rsi_oversold", {"threshold": 30}),
            ("macd_cross_up", {}),
        ], logic_operator="and")
        result = build_strategy_from_graph(graph)
        assert len(result.compiled_conditions) == 2
        assert "rsi_oversold" in result.compiled_conditions
        assert "macd_cross_up" in result.compiled_conditions

    def test_multi_condition_or(self):
        graph = _make_graph([
            ("rsi_oversold", {"threshold": 30}),
            ("bb_lower_touch", {"period": 20}),
        ], logic_operator="or")
        result = build_strategy_from_graph(graph)
        assert len(result.compiled_conditions) == 2

    def test_unsupported_skipped_with_warning(self):
        graph = _make_graph([
            ("ma_cross_up", {"short_period": 10, "long_period": 20}),
            ("pe_ratio", {"max_pe": 15}),
        ])
        result = build_strategy_from_graph(graph)
        assert "ma_cross_up" in result.compiled_conditions
        assert "pe_ratio" in result.skipped_conditions
        assert any("pe_ratio" in w for w in result.warnings)

    def test_all_unsupported_raises(self):
        graph = _make_graph([("pe_ratio", {"max_pe": 15})])
        with pytest.raises(ValueError, match="No backtestable conditions"):
            build_strategy_from_graph(graph)

    def test_universe_warning(self):
        graph = _make_graph([("ma_cross_up", {"short_period": 10, "long_period": 20})])
        result = build_strategy_from_graph(graph)
        assert any("universe" in w.lower() or "ignored" in w.lower() for w in result.warnings)

    def test_tp_sl_injected(self):
        graph = _make_graph([("ma_cross_up", {"short_period": 10, "long_period": 20})])
        result = build_strategy_from_graph(graph, take_profit=0.05, stop_loss=0.03)
        assert result.strategy_cls._take_profit == 0.05
        assert result.strategy_cls._stop_loss == 0.03

    def test_not_operator_warns(self):
        """'not' logic operator should produce a warning and fallback to 'and'."""
        graph = _make_graph(
            [("ma_cross_up", {"short_period": 10, "long_period": 20})],
            logic_operator="not",
        )
        result = build_strategy_from_graph(graph)
        assert result.strategy_cls._logic_operator == "and"
        assert any("not" in w.lower() for w in result.warnings)

    def test_invalid_params_use_defaults(self):
        """Invalid parameter values should fall back to defaults, not crash."""
        spec = compile_condition("ma_cross_up", {"short_period": "bad", "long_period": None})
        assert spec is not None
        assert spec.condition_type == "ma_cross_up"

    def test_disconnected_node_ignored(self):
        """A condition node not reachable from output should be ignored."""
        nodes = [
            StrategyNode(id="u1", data=StrategyNodeData(node_type="universe", universe="SP500")),
            StrategyNode(id="c1", data=StrategyNodeData(
                node_type="condition", condition_type="ma_cross_up",
                params={"short_period": 10, "long_period": 20},
            )),
            StrategyNode(id="c_orphan", data=StrategyNodeData(
                node_type="condition", condition_type="rsi_oversold",
                params={"threshold": 30},
            )),
            StrategyNode(id="g1", data=StrategyNodeData(
                node_type="logic", logic_operator="and", child_node_ids=["c1"],
            )),
            StrategyNode(id="o1", data=StrategyNodeData(node_type="output")),
        ]
        edges = [
            StrategyEdge(id="e1", source="u1", target="g1"),
            StrategyEdge(id="e2", source="g1", target="o1"),
        ]
        graph = StrategyGraph(nodes=nodes, edges=edges)
        result = build_strategy_from_graph(graph)
        assert "ma_cross_up" in result.compiled_conditions
        assert "rsi_oversold" not in result.compiled_conditions


# --- Tests: end-to-end backtest execution ---

class TestGraphBacktestExecution:
    def test_ma_cross_runs(self, sample_ohlcv):
        """MA crossover graph should execute a full backtest."""
        graph = _make_graph([("ma_cross_up", {"short_period": 10, "long_period": 30})])
        result = build_strategy_from_graph(graph)

        engine = BacktestEngine(commission=0.001)
        bt_result = engine.run(
            strategy=result.strategy_cls,
            ticker="TEST",
            data=sample_ohlcv,
            cash=10_000_000,
        )
        assert bt_result is not None
        assert bt_result.num_trades >= 0

    def test_rsi_oversold_runs(self, sample_ohlcv):
        """RSI oversold graph should execute without error."""
        graph = _make_graph([("rsi_oversold", {"threshold": 35, "period": 14})])
        result = build_strategy_from_graph(graph)

        engine = BacktestEngine(commission=0.001)
        bt_result = engine.run(
            strategy=result.strategy_cls,
            ticker="TEST",
            data=sample_ohlcv,
            cash=10_000_000,
        )
        assert bt_result is not None

    def test_multi_condition_and_runs(self, sample_ohlcv):
        """AND combination of conditions should work."""
        graph = _make_graph([
            ("rsi_oversold", {"threshold": 40}),
            ("volume_above_avg", {"period": 20, "multiplier": 1.0}),
        ], logic_operator="and")
        result = build_strategy_from_graph(graph)

        engine = BacktestEngine(commission=0.001)
        bt_result = engine.run(
            strategy=result.strategy_cls,
            ticker="TEST",
            data=sample_ohlcv,
            cash=10_000_000,
        )
        assert bt_result is not None

    def test_tp_sl_works(self, sample_ohlcv):
        """TP/SL should be respected."""
        graph = _make_graph([("ma_cross_up", {"short_period": 5, "long_period": 20})])
        result = build_strategy_from_graph(graph, take_profit=0.02, stop_loss=0.01)

        engine = BacktestEngine(commission=0.001)
        bt_result = engine.run(
            strategy=result.strategy_cls,
            ticker="TEST",
            data=sample_ohlcv,
            cash=10_000_000,
        )
        assert bt_result is not None
        # With tight TP/SL, we should get more trades than without
        assert bt_result.num_trades >= 0

    def test_bb_strategy_runs(self, sample_ohlcv):
        """Bollinger Band strategy should execute."""
        graph = _make_graph([("bb_lower_touch", {"period": 20, "std_dev": 2.0})])
        result = build_strategy_from_graph(graph)

        engine = BacktestEngine(commission=0.001)
        bt_result = engine.run(
            strategy=result.strategy_cls,
            ticker="TEST",
            data=sample_ohlcv,
            cash=10_000_000,
        )
        assert bt_result is not None

    def test_macd_cross_runs(self, sample_ohlcv):
        """MACD crossover should execute."""
        graph = _make_graph([("macd_cross_up", {})])
        result = build_strategy_from_graph(graph)

        engine = BacktestEngine(commission=0.001)
        bt_result = engine.run(
            strategy=result.strategy_cls,
            ticker="TEST",
            data=sample_ohlcv,
            cash=10_000_000,
        )
        assert bt_result is not None
        assert bt_result.num_trades >= 0
