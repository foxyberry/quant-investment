"""
Strategy Builder Service.

Converts a QuantCanvas strategy graph (DAG) into a backtestable Strategy.
Uses the GraphBacktestStrategy with compiled signal functions.

Architecture:
    StrategyGraph (JSON) -> walk DAG from output node -> compile conditions -> inject into Strategy -> run backtest

The builder respects graph topology by walking edges backward from the output
node, rather than flat-scanning all nodes. This ensures only reachable
conditions are included and the correct logic operator is used.
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Type

from backtesting import Strategy

from api.schemas.strategy import StrategyGraph, StrategyNode
from engine.strategies.graph_strategy import (
    GraphBacktestStrategy,
    SignalSpec,
    SUPPORTED_CONDITION_TYPES,
    compile_condition,
)

logger = logging.getLogger(__name__)

# Logic operators supported for backtesting
_SUPPORTED_LOGIC_OPS = {"and", "or"}


@dataclass
class BuildResult:
    """Result of building a Strategy from a graph."""

    strategy_cls: Type[Strategy]
    warnings: List[str] = field(default_factory=list)
    skipped_conditions: List[str] = field(default_factory=list)
    compiled_conditions: List[str] = field(default_factory=list)


def _walk_reachable(
    node_id: str,
    reverse_adj: Dict[str, List[str]],
    node_map: Dict[str, StrategyNode],
    visited: Set[str],
) -> List[str]:
    """Walk backward from a node and return all reachable node IDs (BFS)."""
    queue = deque([node_id])
    order: List[str] = []
    while queue:
        nid = queue.popleft()
        if nid in visited:
            continue
        visited.add(nid)
        order.append(nid)
        # Follow reverse edges
        for parent_id in reverse_adj.get(nid, []):
            if parent_id not in visited:
                queue.append(parent_id)
        # Follow child_node_ids (logic nodes reference children directly)
        node = node_map.get(nid)
        if node and node.data.child_node_ids:
            for child_id in node.data.child_node_ids:
                if child_id not in visited:
                    queue.append(child_id)
    return order


def build_strategy_from_graph(
    graph: StrategyGraph,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
) -> BuildResult:
    """Build a backtestable Strategy class from a QuantCanvas graph.

    Walks the DAG backward from the output node to discover reachable
    condition and logic nodes. Only connected nodes are compiled.

    Args:
        graph: The strategy graph with nodes and edges.
        take_profit: Optional fixed take-profit ratio (e.g. 0.05 = 5%).
        stop_loss: Optional fixed stop-loss ratio (e.g. 0.03 = 3%).

    Returns:
        BuildResult with the Strategy class, warnings, and metadata.

    Raises:
        ValueError: If no backtestable conditions are found in the graph.
    """
    warnings: List[str] = []
    skipped: List[str] = []
    compiled: List[str] = []

    # Build node lookup and adjacency
    node_map: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}
    reverse_adj: Dict[str, List[str]] = defaultdict(list)
    for edge in graph.edges:
        reverse_adj[edge.target].append(edge.source)

    # Find output node(s) — walk backward from each
    output_nodes = [n for n in graph.nodes if n.data.node_type == "output"]
    if not output_nodes:
        # Fallback: treat all nodes as reachable (backward compat)
        reachable_ids = set(node_map.keys())
        warnings.append("No output node found; using all nodes as reachable.")
    else:
        visited: Set[str] = set()
        for out_node in output_nodes:
            _walk_reachable(out_node.id, reverse_adj, node_map, visited)
        reachable_ids = visited

    # Collect condition nodes and logic operator from reachable nodes
    condition_nodes: List[StrategyNode] = []
    root_logic_operator = "and"  # default
    seen_condition_ids: Set[str] = set()

    for nid in reachable_ids:
        node = node_map.get(nid)
        if node is None:
            continue

        if node.data.node_type == "condition":
            if nid not in seen_condition_ids:
                seen_condition_ids.add(nid)
                condition_nodes.append(node)

        elif node.data.node_type == "logic":
            op = node.data.logic_operator
            if op:
                if op in _SUPPORTED_LOGIC_OPS:
                    root_logic_operator = op
                elif op == "not":
                    warnings.append(
                        f"Logic operator 'not' (node '{nid}') is not supported for "
                        f"backtesting. Falling back to 'and'."
                    )
                else:
                    warnings.append(
                        f"Unknown logic operator '{op}' (node '{nid}'). "
                        f"Falling back to 'and'."
                    )

        elif node.data.node_type in ("universe", "sector"):
            warnings.append(
                f"Node '{nid}' ({node.data.node_type}) is ignored in backtesting "
                f"(single-ticker mode)."
            )

    # Compile conditions into signals
    signal_specs: List[SignalSpec] = []

    for cond_node in condition_nodes:
        ct = cond_node.data.condition_type
        if ct is None:
            warnings.append(f"Condition node '{cond_node.id}' has no condition_type, skipped.")
            continue

        if ct not in SUPPORTED_CONDITION_TYPES:
            skipped.append(ct)
            warnings.append(
                f"Condition '{ct}' is not supported for backtesting and was skipped. "
                f"Supported: {', '.join(sorted(SUPPORTED_CONDITION_TYPES))}"
            )
            continue

        spec = compile_condition(ct, cond_node.data.params)
        if spec is None:
            skipped.append(ct)
            continue

        signal_specs.append(spec)
        compiled.append(ct)

    if not signal_specs:
        raise ValueError(
            "No backtestable conditions found in the graph. "
            f"Skipped conditions: {skipped}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_CONDITION_TYPES))}"
        )

    # Create a new subclass with injected attributes
    # (Backtesting.py requires class-level attributes for parameter binding)
    strategy_cls = type(
        "CompiledGraphStrategy",
        (GraphBacktestStrategy,),
        {
            "_signal_specs": signal_specs,
            "_logic_operator": root_logic_operator,
            "_take_profit": take_profit,
            "_stop_loss": stop_loss,
        },
    )

    return BuildResult(
        strategy_cls=strategy_cls,
        warnings=warnings,
        skipped_conditions=skipped,
        compiled_conditions=compiled,
    )
