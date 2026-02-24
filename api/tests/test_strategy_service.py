"""
Tests for strategy service: graph building and condition mapping.
"""

import pytest

from api.schemas.strategy import (
    StrategyGraph,
    StrategyNode,
    StrategyNodeData,
    StrategyEdge,
)
from api.services.strategy_service import (
    build_conditions_from_graph,
    get_available_conditions,
    CONDITION_CLASS_MAP,
    CONDITION_METADATA,
    _build_condition,
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
