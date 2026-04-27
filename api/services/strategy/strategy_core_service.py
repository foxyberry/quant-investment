"""
Strategy Core Service.

Condition registry, graph traversal, condition building, and helper utilities.
Covers: get_available_conditions, build_conditions_from_graph,
build_flat_conditions_from_graph, and all supporting private helpers.
"""

import logging
from itertools import combinations
from typing import Any, Dict, List, Optional, Type

import numpy as np

from api.schemas.strategy import (
    ConditionInfo,
    ConditionParamInfo,
    StrategyGraph,
    StrategyNode,
)
from screener.conditions import BaseCondition, AndCondition, OrCondition, NotCondition
from screener.conditions.registry import get_condition_class_map, get_condition_metadata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Condition registry (populated from @register_condition decorators)
# ---------------------------------------------------------------------------

CONDITION_CLASS_MAP: Dict[str, Type[BaseCondition]] = get_condition_class_map()
CONDITION_METADATA: Dict[str, Dict[str, Any]] = get_condition_metadata()

# ---------------------------------------------------------------------------
# Legacy alias map
# ---------------------------------------------------------------------------

_LEGACY_ALIAS_MAP: Dict[str, tuple[str, Dict[str, Any]]] = {}
_LAGS = [1, 2, 3, 5, 10, 20, 60]

for _field in ["close", "open", "high", "low"]:
    for _left, _right in combinations(_LAGS, 2):
        for _op in ("gt", "lt"):
            _LEGACY_ALIAS_MAP[f"{_field}_lag_{_left}_{_op}_{_right}"] = (
                "price_lag_compare",
                {"field": _field, "lag_a": _left, "lag_b": _right, "operator": _op},
            )

for _left, _right in combinations(_LAGS, 2):
    _LEGACY_ALIAS_MAP[f"volume_lag_{_left}_gt_{_right}"] = (
        "volume_lag_compare",
        {"lag_a": _left, "lag_b": _right, "operator": "gt"},
    )

# ---------------------------------------------------------------------------
# Scalar helpers
# ---------------------------------------------------------------------------

WARN_TICKERS_THRESHOLD = 2500
MAX_TICKERS_PER_RUN = 4000


def _to_optional_float(value: Any) -> Optional[float]:
    """Safely convert a value to float; return None for NaN/inf/non-numeric."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric):
        return None
    return numeric


def _is_korean_ticker(ticker: str) -> bool:
    return ticker.endswith(".KS") or ticker.endswith(".KQ")


def _extract_krx_code(ticker: str) -> str:
    return ticker.split(".")[0]


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


# ---------------------------------------------------------------------------
# Condition factory
# ---------------------------------------------------------------------------

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
    if condition_type not in CONDITION_CLASS_MAP and condition_type in _LEGACY_ALIAS_MAP:
        new_type, default_params = _LEGACY_ALIAS_MAP[condition_type]
        remapped = {}
        for k, v in params.items():
            if k == "left_lag":
                remapped["lag_a"] = v
            elif k == "right_lag":
                remapped["lag_b"] = v
            else:
                remapped[k] = v
        merged = {**default_params, **remapped}
        return _build_condition(new_type, merged)

    cls = CONDITION_CLASS_MAP.get(condition_type)
    if cls is None:
        raise ValueError(f"Unknown condition type: {condition_type}")

    meta = CONDITION_METADATA.get(condition_type, {})
    meta_params = {p["name"]: p["type"] for p in meta.get("params", [])}

    coerced = {}
    for k, v in params.items():
        if k in meta_params:
            coerced[k] = _coerce_param(v, meta_params[k])
        else:
            coerced[k] = v

    if meta.get("is_pairs"):
        t2 = coerced.get("ticker2", "")
        if not isinstance(t2, str):
            raise ValueError(
                f"Pairs condition '{condition_type}': ticker2 must be a string"
            )
        t2 = t2.strip()
        coerced["ticker2"] = t2
        if not t2:
            raise ValueError(
                f"Pairs condition '{condition_type}' requires a 'ticker2' parameter"
            )

    return cls(**coerced)


# ---------------------------------------------------------------------------
# Public API — condition catalogue
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Graph traversal — nested (build_conditions_from_graph)
# ---------------------------------------------------------------------------

def build_conditions_from_graph(graph: StrategyGraph) -> tuple[List[BaseCondition], str]:
    """
    Walk the strategy graph from Output node backward and build nested conditions.

    Returns:
        Tuple of (conditions list, universe name)
    """
    nodes_by_id: Dict[str, StrategyNode] = {n.id: n for n in graph.nodes}

    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)

    output_nodes = [n for n in graph.nodes if n.data.node_type == "output"]
    if not output_nodes:
        raise ValueError("Graph must have an Output node")
    output_node = output_nodes[0]

    universe = "KOSPI"
    universe_nodes = [n for n in graph.nodes if n.data.node_type == "universe"]
    if universe_nodes:
        universe = universe_nodes[0].data.universe or "KOSPI"

    def _resolve_node(node_id: str) -> Optional[BaseCondition]:
        node = nodes_by_id.get(node_id)
        if node is None:
            return None

        if node.data.node_type == "universe":
            return None

        if node.data.node_type == "sector":
            return None

        if node.data.node_type == "condition":
            if not node.data.condition_type:
                raise ValueError(f"Condition node {node_id} has no condition_type")
            return _build_condition(node.data.condition_type, node.data.params)

        if node.data.node_type == "logic":
            operator = (node.data.logic_operator or "and").lower()
            child_ids = node.data.child_node_ids or []
            if child_ids:
                source_ids = child_ids
            else:
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
            sub_conditions = []
            resolved_ids = set()
            for src_id in incoming.get(node_id, []):
                resolved_ids.add(src_id)
                cond = _resolve_node(src_id)
                if cond is not None:
                    sub_conditions.append(cond)

            child_ids_set: set[str] = set()
            for n in graph.nodes:
                if n.data.child_node_ids:
                    child_ids_set.update(n.data.child_node_ids)

            for n in graph.nodes:
                if (
                    n.data.node_type in ("logic", "condition")
                    and n.id not in child_ids_set
                    and n.id not in resolved_ids
                ):
                    cond = _resolve_node(n.id)
                    if cond is not None:
                        sub_conditions.append(cond)

            return sub_conditions  # type: ignore

        return None

    resolved = _resolve_node(output_node.id)

    if isinstance(resolved, list):
        conditions = resolved
    elif resolved is not None:
        conditions = [resolved]
    else:
        conditions = []

    return conditions, universe


# ---------------------------------------------------------------------------
# Graph traversal — flat (build_flat_conditions_from_graph)
# ---------------------------------------------------------------------------

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

    incoming: Dict[str, List[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target].append(edge.source)

    output_nodes = [n for n in graph.nodes if n.data.node_type == "output"]
    if not output_nodes:
        raise ValueError("Graph must have an Output node")
    output_node = output_nodes[0]

    universe = "KOSPI"
    universe_nodes = [n for n in graph.nodes if n.data.node_type == "universe"]
    if universe_nodes:
        universe = universe_nodes[0].data.universe or "KOSPI"

    leaf_conditions: List[BaseCondition] = []
    node_meta: Dict[str, dict] = {}

    child_ids_set: set[str] = set()
    for n in graph.nodes:
        if n.data.child_node_ids:
            child_ids_set.update(n.data.child_node_ids)

    def _resolve_flat(node_id: str) -> List[int]:
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

        if node.data.node_type == "sector":
            node_meta[node_id] = {
                "node_type": "sector",
                "label": node.data.sector or "Sector",
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
