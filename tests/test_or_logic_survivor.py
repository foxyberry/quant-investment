"""Tests for OR logic node survivor computation.

Reproduces the bug where intermediate condition nodes in an edge-based OR
graph get AND-intersected with the OR result by the output node, causing
the OR to behave like AND.

Graph topology tested:
  Universe ──→ CondA ──→ CondB ──→ OR ──→ Output
  Universe ──→ CondC ──→ CondD ──↗

Expected: Output = union(CondB_survivors, CondD_survivors)
Bug:      Output = intersection(OR_union, CondA, CondB, CondC, CondD)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pytest

from api.schemas.strategy import StrategyNode, StrategyNodeData
from api.services.strategy_service import _compute_node_survivors


@dataclass
class _FakeCondResult:
    matched: bool
    condition_name: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class _FakeResult:
    ticker: str
    name: str
    current_price: float
    condition_results: List[_FakeCondResult]


def _build_edge_or_graph():
    """Build: Universe → A → B → OR → Output, Universe → C → D → OR → Output.

    4 leaf conditions (indices 0-3): A, B, C, D.
    10 tickers (indices 0-9).

    Condition match patterns:
      A (leaf 0): tickers 0-6 pass  (7 tickers)
      B (leaf 1): tickers 0-4 pass  (5 tickers) — chain A→B survivors = 5
      C (leaf 2): tickers 3-9 pass  (7 tickers)
      D (leaf 3): tickers 5-9 pass  (5 tickers) — chain C→D survivors = 5

    Expected OR union: {0,1,2,3,4} ∪ {5,6,7,8,9} = {0..9} = 10
    Bug result:        {0..4} ∩ {5..9} = {} (or similarly small)
    """
    nodes = [
        StrategyNode(id="univ", data=StrategyNodeData(node_type="universe", universe="TEST")),
        StrategyNode(id="condA", data=StrategyNodeData(node_type="condition", condition_type="test_a")),
        StrategyNode(id="condB", data=StrategyNodeData(node_type="condition", condition_type="test_b")),
        StrategyNode(id="condC", data=StrategyNodeData(node_type="condition", condition_type="test_c")),
        StrategyNode(id="condD", data=StrategyNodeData(node_type="condition", condition_type="test_d")),
        StrategyNode(id="or1", data=StrategyNodeData(node_type="logic", logic_operator="or")),
        StrategyNode(id="out", data=StrategyNodeData(node_type="output")),
    ]
    nodes_by_id = {n.id: n for n in nodes}

    # Edges: univ→A, A→B, B→OR, univ→C, C→D, D→OR, OR→out
    incoming: Dict[str, List[str]] = {n.id: [] for n in nodes}
    incoming["condA"] = ["univ"]
    incoming["condB"] = ["condA"]
    incoming["condC"] = ["univ"]
    incoming["condD"] = ["condC"]
    incoming["or1"] = ["condB", "condD"]
    incoming["out"] = ["or1"]

    node_meta = {
        "univ": {"node_type": "universe", "label": "TEST", "leaf_indices": []},
        "condA": {"node_type": "condition", "label": "A", "leaf_indices": [0]},
        "condB": {"node_type": "condition", "label": "B", "leaf_indices": [1]},
        "condC": {"node_type": "condition", "label": "C", "leaf_indices": [2]},
        "condD": {"node_type": "condition", "label": "D", "leaf_indices": [3]},
        "or1": {"node_type": "logic", "label": "OR", "leaf_indices": [0, 1, 2, 3], "operator": "or"},
        "out": {"node_type": "output", "label": "Output", "leaf_indices": [0, 1, 2, 3]},
    }

    child_ids_set: set = set()
    child_to_parent: Dict[str, str] = {}

    # 10 tickers with condition match patterns
    all_results = []
    for i in range(10):
        conds = [
            _FakeCondResult(matched=(i <= 6)),  # A: 0-6
            _FakeCondResult(matched=(i <= 4)),  # B: 0-4
            _FakeCondResult(matched=(i >= 3)),  # C: 3-9
            _FakeCondResult(matched=(i >= 5)),  # D: 5-9
        ]
        all_results.append(_FakeResult(ticker=f"T{i}", name=f"T{i}", current_price=100.0, condition_results=conds))

    return nodes_by_id, incoming, node_meta, child_ids_set, child_to_parent, all_results


class TestOrLogicSurvivorCache:
    """Verify OR node produces union, not intersection."""

    def test_or_edge_based_union(self):
        """OR of two branches should be union of each branch's survivors."""
        nodes_by_id, incoming, node_meta, child_ids_set, child_to_parent, all_results = (
            _build_edge_or_graph()
        )
        cache: Dict[str, set] = {}
        result = _compute_node_survivors(
            "out", all_results, nodes_by_id, incoming,
            node_meta, child_ids_set, cache, child_to_parent,
        )
        # Branch 1 (A→B): tickers 0-4  (B survivors with A upstream)
        # Branch 2 (C→D): tickers 5-9  (D survivors with C upstream)
        # OR union: {0,1,2,3,4} ∪ {5,6,7,8,9} = all 10
        assert result == set(range(10))

    def test_or_intermediate_counts_correct(self):
        """Individual node counts should reflect pipeline filtering."""
        nodes_by_id, incoming, node_meta, child_ids_set, child_to_parent, all_results = (
            _build_edge_or_graph()
        )
        cache: Dict[str, set] = {}

        # Simulate outer loop: evaluate all nodes (as the real code does)
        for node_id in node_meta:
            _compute_node_survivors(
                node_id, all_results, nodes_by_id, incoming,
                node_meta, child_ids_set, cache, child_to_parent,
            )

        assert cache["condA"] == {0, 1, 2, 3, 4, 5, 6}  # 7 tickers
        assert cache["condB"] == {0, 1, 2, 3, 4}          # 5 tickers (A∩B)
        assert cache["condC"] == {3, 4, 5, 6, 7, 8, 9}    # 7 tickers
        assert cache["condD"] == {5, 6, 7, 8, 9}           # 5 tickers (C∩D)
        assert cache["or1"] == set(range(10))              # union = 10
        assert cache["out"] == set(range(10))              # same as OR

    def test_or_with_overlapping_branches(self):
        """OR with partially overlapping branch results."""
        nodes_by_id, incoming, node_meta, child_ids_set, child_to_parent, all_results = (
            _build_edge_or_graph()
        )
        # Modify: B passes tickers 2-6, D passes tickers 4-8
        # So branch 1 survivors (A∩B) = {2,3,4,5,6}, branch 2 (C∩D) = {5,6,7,8}
        # OR union = {2,3,4,5,6,7,8} = 7 tickers
        for i, r in enumerate(all_results):
            r.condition_results[1] = _FakeCondResult(matched=(2 <= i <= 6))  # B
            r.condition_results[3] = _FakeCondResult(matched=(4 <= i <= 8))  # D

        cache: Dict[str, set] = {}
        result = _compute_node_survivors(
            "out", all_results, nodes_by_id, incoming,
            node_meta, child_ids_set, cache, child_to_parent,
        )
        expected = {2, 3, 4, 5, 6, 7, 8}
        assert result == expected

    def test_or_outer_loop_then_output_consistent(self):
        """Output result is identical whether we pre-populate cache or not.

        This is the exact bug scenario: the outer display loop evaluates
        intermediate condition nodes first, populating the cache. Then
        the output node evaluation should still produce the correct union.
        """
        nodes_by_id, incoming, node_meta, child_ids_set, child_to_parent, all_results = (
            _build_edge_or_graph()
        )

        # Approach 1: fresh cache, evaluate output only
        cache1: Dict[str, set] = {}
        result1 = _compute_node_survivors(
            "out", all_results, nodes_by_id, incoming,
            node_meta, child_ids_set, cache1, child_to_parent,
        )

        # Approach 2: pre-populate cache by evaluating all nodes (simulates outer loop)
        cache2: Dict[str, set] = {}
        for node_id in node_meta:
            _compute_node_survivors(
                node_id, all_results, nodes_by_id, incoming,
                node_meta, child_ids_set, cache2, child_to_parent,
            )

        assert cache2["out"] == result1, (
            "Output result should be identical regardless of cache pre-population order"
        )


class TestGroupBasedOrLogic:
    """Verify OR works correctly with child_node_ids (group-based)."""

    def test_group_or_union(self):
        """OR group with child_node_ids should produce union."""
        nodes = [
            StrategyNode(id="univ", data=StrategyNodeData(node_type="universe", universe="TEST")),
            StrategyNode(id="condA", data=StrategyNodeData(node_type="condition", condition_type="test_a")),
            StrategyNode(id="condB", data=StrategyNodeData(node_type="condition", condition_type="test_b")),
            StrategyNode(id="or1", data=StrategyNodeData(
                node_type="logic", logic_operator="or", child_node_ids=["condA", "condB"],
            )),
            StrategyNode(id="out", data=StrategyNodeData(node_type="output")),
        ]
        nodes_by_id = {n.id: n for n in nodes}

        incoming: Dict[str, List[str]] = {n.id: [] for n in nodes}
        incoming["or1"] = ["univ"]
        incoming["out"] = ["or1"]

        node_meta = {
            "univ": {"node_type": "universe", "label": "TEST", "leaf_indices": []},
            "condA": {"node_type": "condition", "label": "A", "leaf_indices": [0]},
            "condB": {"node_type": "condition", "label": "B", "leaf_indices": [1]},
            "or1": {"node_type": "logic", "label": "OR", "leaf_indices": [0, 1], "operator": "or"},
            "out": {"node_type": "output", "label": "Output", "leaf_indices": [0, 1]},
        }

        child_ids_set = {"condA", "condB"}
        child_to_parent = {"condA": "or1", "condB": "or1"}

        # 6 tickers: A passes 0-2, B passes 3-5
        all_results = []
        for i in range(6):
            conds = [
                _FakeCondResult(matched=(i <= 2)),  # A: 0-2
                _FakeCondResult(matched=(i >= 3)),  # B: 3-5
            ]
            all_results.append(_FakeResult(ticker=f"T{i}", name=f"T{i}", current_price=100.0, condition_results=conds))

        cache: Dict[str, set] = {}
        result = _compute_node_survivors(
            "out", all_results, nodes_by_id, incoming,
            node_meta, child_ids_set, cache, child_to_parent,
        )
        assert result == set(range(6))  # union of {0,1,2} ∪ {3,4,5}
