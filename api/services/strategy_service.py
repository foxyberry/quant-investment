"""
Strategy Service.

Business logic for the visual strategy builder.
Converts graph representations into screener conditions and executes them.
"""

import logging
from typing import Any, Dict, List, Optional, Type

import numpy as np

from api.schemas.strategy import (
    ConditionInfo,
    ConditionParamInfo,
    StrategyGraph,
    StrategyNode,
    StrategyResultItem,
)
from screener.conditions import BaseCondition, AndCondition, OrCondition, NotCondition
from screener.conditions.registry import get_condition_class_map, get_condition_metadata
from screener import StockScreener
from api.services.screening_service import ScreeningService

logger = logging.getLogger(__name__)

# Auto-populated from @register_condition decorators
CONDITION_CLASS_MAP: Dict[str, Type[BaseCondition]] = get_condition_class_map()
CONDITION_METADATA: Dict[str, Dict[str, Any]] = get_condition_metadata()


def _sanitize_value(v: Any) -> Any:
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, dict):
        return {k: _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(item) for item in v]
    return v


def get_available_conditions() -> List[ConditionInfo]:
    """Return list of available conditions with their parameter schemas."""
    conditions = []
    for key, meta in CONDITION_METADATA.items():
        params = [ConditionParamInfo(**p) for p in meta["params"]]
        conditions.append(
            ConditionInfo(
                key=key,
                label=meta["label"],
                description=meta.get("description", ""),
                category=meta["category"],
                params=params,
            )
        )
    return conditions


def _coerce_param(value: Any, param_type: str) -> Any:
    """Coerce a parameter value to the expected type."""
    if value is None:
        return None
    if param_type == "int":
        return int(value)
    if param_type == "float":
        return float(value)
    if param_type == "bool":
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    return value


def _build_condition(condition_type: str, params: Dict[str, Any]) -> BaseCondition:
    """Instantiate a single condition from type key and params."""
    cls = CONDITION_CLASS_MAP.get(condition_type)
    if cls is None:
        raise ValueError(f"Unknown condition type: {condition_type}")

    # Coerce params to correct types based on metadata
    meta = CONDITION_METADATA.get(condition_type, {})
    meta_params = {p["name"]: p["type"] for p in meta.get("params", [])}

    coerced = {}
    for k, v in params.items():
        if k in meta_params:
            coerced[k] = _coerce_param(v, meta_params[k])
        else:
            coerced[k] = v

    return cls(**coerced)


def build_conditions_from_graph(graph: StrategyGraph) -> tuple[List[BaseCondition], str]:
    """
    Walk the strategy graph from Output node backward and build nested conditions.

    Returns:
        Tuple of (conditions list, universe name)
    """
    nodes_by_id: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}

    # Build adjacency: target -> list of source node IDs
    # An edge from A -> B means A feeds into B
    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)

    # Find the output node
    output_nodes = [n for n in graph.nodes if n.data.node_type == "output"]
    if not output_nodes:
        raise ValueError("Graph must have an Output node")
    output_node = output_nodes[0]

    # Find universe from universe nodes
    universe = "KOSPI"  # default
    universe_nodes = [n for n in graph.nodes if n.data.node_type == "universe"]
    if universe_nodes:
        universe = universe_nodes[0].data.universe or "KOSPI"

    def _resolve_node(node_id: str) -> Optional[BaseCondition]:
        """Recursively resolve a node to a BaseCondition."""
        node = nodes_by_id.get(node_id)
        if node is None:
            return None

        if node.data.node_type == "universe":
            return None

        if node.data.node_type == "condition":
            if not node.data.condition_type:
                raise ValueError(f"Condition node {node_id} has no condition_type")
            return _build_condition(node.data.condition_type, node.data.params)

        if node.data.node_type == "logic":
            operator = (node.data.logic_operator or "and").lower()
            # New approach: use child_node_ids (group container)
            child_ids = node.data.child_node_ids or []
            if child_ids:
                source_ids = child_ids
            else:
                # Backward compatibility: use edge-based incoming
                source_ids = incoming.get(node_id, [])
            sub_conditions = []
            for src_id in source_ids:
                cond = _resolve_node(src_id)
                if cond is not None:
                    sub_conditions.append(cond)

            if not sub_conditions:
                return None

            if operator == "and":
                return AndCondition(sub_conditions) if len(sub_conditions) > 1 else sub_conditions[0]
            elif operator == "or":
                return OrCondition(sub_conditions) if len(sub_conditions) > 1 else sub_conditions[0]
            elif operator == "not":
                return NotCondition(sub_conditions[0])
            else:
                raise ValueError(f"Unknown logic operator: {operator}")

        if node.data.node_type == "output":
            # Resolve all incoming nodes to the output
            sub_conditions = []
            for src_id in incoming.get(node_id, []):
                cond = _resolve_node(src_id)
                if cond is not None:
                    sub_conditions.append(cond)
            return sub_conditions  # type: ignore

        return None

    # Resolve from output node
    resolved = _resolve_node(output_node.id)

    if isinstance(resolved, list):
        conditions = resolved
    elif resolved is not None:
        conditions = [resolved]
    else:
        conditions = []

    return conditions, universe


def execute_strategy(
    graph: StrategyGraph,
    universe_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a visual strategy graph.

    Args:
        graph: The strategy graph
        universe_override: Override the universe from graph

    Returns:
        Dict with results, counts, universe, and conditions used
    """
    conditions, graph_universe = build_conditions_from_graph(graph)

    if not conditions:
        raise ValueError("No conditions found in graph")

    universe = universe_override or graph_universe

    # Get tickers from universe
    screening_service = ScreeningService()
    tickers = screening_service._get_universe_tickers(universe)
    total_count = len(tickers)

    # Create screener and run
    screener = StockScreener(
        conditions=conditions,
        max_workers=5,
        use_full_universe=True,
        use_cache=True,
    )

    results = screener.run(tickers=tickers, show_progress=False)

    # Convert to response items (sanitize numpy types)
    result_items = []
    for result in results:
        cond_details = [
            {
                "condition_name": cr.condition_name,
                "matched": bool(cr.matched),
                "details": _sanitize_value(cr.details),
            }
            for cr in result.condition_results
        ]
        result_items.append(
            StrategyResultItem(
                ticker=result.ticker,
                name=result.name,
                current_price=result.current_price,
                matched=result.matched,
                conditions=cond_details,
            )
        )

    conditions_used = [type(c).__name__ for c in conditions]

    return {
        "results": result_items,
        "total_count": total_count,
        "matched_count": len(result_items),
        "universe": universe,
        "conditions_used": conditions_used,
    }
