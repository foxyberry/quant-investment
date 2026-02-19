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
    NodeIntermediateResult,
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
                recommended=meta.get("recommended", False),
                order=meta.get("order", 0),
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
            # Resolve all incoming nodes to the output via edges
            sub_conditions = []
            resolved_ids = set()
            for src_id in incoming.get(node_id, []):
                resolved_ids.add(src_id)
                cond = _resolve_node(src_id)
                if cond is not None:
                    sub_conditions.append(cond)

            # Also resolve top-level logic/condition nodes not connected
            # via edges (e.g., group nodes using child_node_ids containment)
            child_ids_set: set[str] = set()
            for n in graph.nodes:
                if n.data.child_node_ids:
                    child_ids_set.update(n.data.child_node_ids)

            for n in graph.nodes:
                if (
                    n.data.node_type in ("logic", "condition")
                    and n.id not in child_ids_set  # not a child of a group
                    and n.id not in resolved_ids  # not already resolved via edge
                ):
                    cond = _resolve_node(n.id)
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


def build_flat_conditions_from_graph(
    graph: StrategyGraph,
) -> tuple[List[BaseCondition], str, Dict[str, dict]]:
    """
    Walk the strategy graph and extract leaf conditions into a flat list.

    Unlike build_conditions_from_graph() which creates nested composite conditions,
    this function keeps each condition separate so that per-node intermediate results
    can be computed after screening.

    Returns:
        Tuple of (leaf_conditions, universe, node_meta)
        - leaf_conditions: flat list of individual BaseCondition instances
        - universe: universe name string
        - node_meta: Dict[node_id, dict] where each entry has:
            - 'node_type': str
            - 'label': str
            - 'leaf_indices': List[int] - indices into leaf_conditions
            - 'operator': Optional[str] - 'and'/'or'/'not' for logic nodes
    """
    nodes_by_id: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}

    # Build adjacency: target -> list of source node IDs
    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)

    # Find the output node
    output_nodes = [n for n in graph.nodes if n.data.node_type == "output"]
    if not output_nodes:
        raise ValueError("Graph must have an Output node")
    output_node = output_nodes[0]

    # Find universe
    universe = "KOSPI"
    universe_nodes = [n for n in graph.nodes if n.data.node_type == "universe"]
    if universe_nodes:
        universe = universe_nodes[0].data.universe or "KOSPI"

    leaf_conditions: List[BaseCondition] = []
    node_meta: Dict[str, dict] = {}

    # Track which nodes are children of group containers
    child_ids_set: set[str] = set()
    for n in graph.nodes:
        if n.data.child_node_ids:
            child_ids_set.update(n.data.child_node_ids)

    def _resolve_flat(node_id: str) -> List[int]:
        """Recursively resolve a node and return leaf condition indices."""
        if node_id in node_meta:
            return node_meta[node_id]["leaf_indices"]

        node = nodes_by_id.get(node_id)
        if node is None:
            return []

        if node.data.node_type == "universe":
            node_meta[node_id] = {
                "node_type": "universe",
                "label": node.data.universe or "Universe",
                "leaf_indices": [],
                "operator": None,
            }
            return []

        if node.data.node_type == "condition":
            if not node.data.condition_type:
                raise ValueError(f"Condition node {node_id} has no condition_type")
            cond = _build_condition(node.data.condition_type, node.data.params)
            idx = len(leaf_conditions)
            leaf_conditions.append(cond)
            node_meta[node_id] = {
                "node_type": "condition",
                "label": node.data.condition_type,
                "leaf_indices": [idx],
                "operator": None,
            }
            return [idx]

        if node.data.node_type == "logic":
            operator = (node.data.logic_operator or "and").lower()
            # Use child_node_ids (group container) if available
            child_ids = node.data.child_node_ids or []
            if child_ids:
                source_ids = child_ids
            else:
                source_ids = incoming.get(node_id, [])

            collected_indices: List[int] = []
            for src_id in source_ids:
                collected_indices.extend(_resolve_flat(src_id))

            node_meta[node_id] = {
                "node_type": "logic",
                "label": operator.upper(),
                "leaf_indices": collected_indices,
                "operator": operator,
            }
            return collected_indices

        if node.data.node_type == "output":
            collected_indices = []
            resolved_ids: set[str] = set()
            for src_id in incoming.get(node_id, []):
                resolved_ids.add(src_id)
                collected_indices.extend(_resolve_flat(src_id))

            # Also resolve top-level nodes not connected via edges
            for n in graph.nodes:
                if (
                    n.data.node_type in ("logic", "condition")
                    and n.id not in child_ids_set
                    and n.id not in resolved_ids
                ):
                    collected_indices.extend(_resolve_flat(n.id))

            node_meta[node_id] = {
                "node_type": "output",
                "label": "Output",
                "leaf_indices": collected_indices,
                "operator": "and",
            }
            return collected_indices

        return []

    _resolve_flat(output_node.id)

    return leaf_conditions, universe, node_meta


def _passes_node(result: Any, meta: dict) -> bool:
    """Check whether a screening result passes a given node's conditions."""
    indices = meta["leaf_indices"]
    if not indices:
        return True  # universe node or no conditions

    operator = meta.get("operator", "and")
    relevant = [
        result.condition_results[i]
        for i in indices
        if i < len(result.condition_results)
    ]
    if not relevant:
        return True

    if operator == "or":
        return any(r.matched for r in relevant)
    if operator == "not":
        return not relevant[0].matched
    return all(r.matched for r in relevant)  # default: 'and'


def _compute_node_survivors(
    node_id: str,
    all_results: list,
    nodes_by_id: Dict[str, StrategyNode],
    incoming: Dict[str, List[str]],
    node_meta: Dict[str, dict],
    child_ids_set: set,
    cache: Dict[str, set],
) -> set:
    """Compute the set of result indices that survive up to this node.

    Unlike _passes_node() which checks each node independently,
    this function walks the graph backward so that each node's result
    reflects cumulative filtering from upstream nodes.
    """
    if node_id in cache:
        return cache[node_id]

    node = nodes_by_id.get(node_id)
    if node is None:
        cache[node_id] = set()
        return set()

    all_indices = set(range(len(all_results)))

    if node.data.node_type == "universe":
        cache[node_id] = all_indices
        return all_indices

    if node.data.node_type == "condition":
        meta = node_meta.get(node_id, {})
        leaf_idx = meta.get("leaf_indices", [])
        # Stocks passing this condition alone
        own_passers = set()
        for i, r in enumerate(all_results):
            if leaf_idx and leaf_idx[0] < len(r.condition_results):
                if r.condition_results[leaf_idx[0]].matched:
                    own_passers.add(i)
        # Intersect with upstream survivors (pipeline filtering)
        upstream_ids = incoming.get(node_id, [])
        if upstream_ids:
            upstream = set.intersection(*(
                _compute_node_survivors(
                    uid, all_results, nodes_by_id, incoming,
                    node_meta, child_ids_set, cache,
                )
                for uid in upstream_ids
            ))
            result = own_passers & upstream
        else:
            result = own_passers
        cache[node_id] = result
        return result

    if node.data.node_type == "logic":
        operator = (node.data.logic_operator or "and").lower()
        child_ids = node.data.child_node_ids or []
        source_ids = child_ids if child_ids else incoming.get(node_id, [])

        child_sets = [
            _compute_node_survivors(
                sid, all_results, nodes_by_id, incoming,
                node_meta, child_ids_set, cache,
            )
            for sid in source_ids
            if nodes_by_id.get(sid) and nodes_by_id[sid].data.node_type != "universe"
        ]

        if not child_sets:
            combined = all_indices
        elif operator == "or":
            combined = set.union(*child_sets)
        elif operator == "not":
            combined = all_indices - child_sets[0]
        else:
            combined = set.intersection(*child_sets)

        # If group-based, intersect with upstream edges to the group itself
        if child_ids:
            upstream_ids = [
                uid for uid in incoming.get(node_id, [])
                if uid not in set(child_ids)
            ]
            if upstream_ids:
                upstream = set.intersection(*(
                    _compute_node_survivors(
                        uid, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache,
                    )
                    for uid in upstream_ids
                ))
                combined = combined & upstream

        cache[node_id] = combined
        return combined

    if node.data.node_type == "output":
        child_sets = []
        resolved_ids: set[str] = set()
        for sid in incoming.get(node_id, []):
            resolved_ids.add(sid)
            if nodes_by_id.get(sid) and nodes_by_id[sid].data.node_type != "universe":
                child_sets.append(
                    _compute_node_survivors(
                        sid, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache,
                    )
                )
        # Top-level nodes not connected via edges
        for n in nodes_by_id.values():
            if (
                n.data.node_type in ("logic", "condition")
                and n.id not in child_ids_set
                and n.id not in resolved_ids
            ):
                child_sets.append(
                    _compute_node_survivors(
                        n.id, all_results, nodes_by_id, incoming,
                        node_meta, child_ids_set, cache,
                    )
                )
        if not child_sets:
            combined = all_indices
        else:
            combined = set.intersection(*child_sets)
        cache[node_id] = combined
        return combined

    cache[node_id] = all_indices
    return all_indices


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
        Dict with results, counts, universe, conditions used, and node_results
    """
    leaf_conditions, graph_universe, node_meta = build_flat_conditions_from_graph(graph)

    if not leaf_conditions:
        raise ValueError("No conditions found in graph")

    universe = universe_override or graph_universe

    # Get tickers from universe
    screening_service = ScreeningService()
    tickers = screening_service._get_universe_tickers(universe)
    total_count = len(tickers)

    # Create screener with flat leaf conditions and run with return_all=True
    screener = StockScreener(
        conditions=leaf_conditions,
        max_workers=5,
        use_full_universe=True,
        use_cache=True,
    )

    all_results = screener.run(tickers=tickers, show_progress=False, return_all=True)

    # Rebuild graph structures for survivor computation
    nodes_by_id: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}
    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)
    child_ids_set: set[str] = set()
    for n in graph.nodes:
        if n.data.child_node_ids:
            child_ids_set.update(n.data.child_node_ids)

    # Compute per-node survivors using graph-aware cumulative filtering
    survivor_cache: Dict[str, set] = {}
    node_results: Dict[str, NodeIntermediateResult] = {}
    output_node_id = None

    for node_id, meta in node_meta.items():
        if meta["node_type"] == "output":
            output_node_id = node_id

        survivor_indices = _compute_node_survivors(
            node_id, all_results, nodes_by_id, incoming,
            node_meta, child_ids_set, survivor_cache,
        )
        passing_stocks: List[StrategyResultItem] = []
        for i in sorted(survivor_indices):
            r = all_results[i]
            cond_details = [
                {
                    "condition_name": cr.condition_name,
                    "matched": bool(cr.matched),
                    "details": _sanitize_value(cr.details),
                }
                for cr in r.condition_results
            ]
            passing_stocks.append(
                StrategyResultItem(
                    ticker=r.ticker,
                    name=r.name,
                    current_price=r.current_price,
                    matched=True,
                    conditions=cond_details,
                )
            )
        node_results[node_id] = NodeIntermediateResult(
            node_id=node_id,
            node_type=meta["node_type"],
            label=meta["label"],
            stock_count=len(passing_stocks),
            stocks=passing_stocks,
        )

    # Final results are the stocks that survive the output node
    final_items: List[StrategyResultItem] = []
    if output_node_id and output_node_id in node_results:
        final_items = node_results[output_node_id].stocks
    else:
        for result in all_results:
            if result.matched:
                cond_details = [
                    {
                        "condition_name": cr.condition_name,
                        "matched": bool(cr.matched),
                        "details": _sanitize_value(cr.details),
                    }
                    for cr in result.condition_results
                ]
                final_items.append(
                    StrategyResultItem(
                        ticker=result.ticker,
                        name=result.name,
                        current_price=result.current_price,
                        matched=result.matched,
                        conditions=cond_details,
                    )
                )

    conditions_used = [type(c).__name__ for c in leaf_conditions]

    return {
        "results": final_items,
        "total_count": total_count,
        "matched_count": len(final_items),
        "universe": universe,
        "conditions_used": conditions_used,
        "node_results": node_results,
    }
