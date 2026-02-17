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
from screener.conditions import (
    # Base
    BaseCondition,
    # Composite
    AndCondition,
    OrCondition,
    NotCondition,
    # Price
    MinPriceCondition,
    MaxPriceCondition,
    PriceRangeCondition,
    PriceChangeCondition,
    # Volume
    MinVolumeCondition,
    VolumeAboveAvgCondition,
    VolumeSpikeCondition,
    # MA
    MATouchCondition,
    AboveMACondition,
    BelowMACondition,
    MACrossUpCondition,
    MACrossDownCondition,
    # RSI
    RSIOversoldCondition,
    RSIOverboughtCondition,
    RSIRangeCondition,
    # Accumulation Layer 1
    BollingerWidthCondition,
    VolumeBelowAvgCondition,
    PriceFlatCondition,
    OBVTrendCondition,
    StochasticLevelCondition,
    VPCITrendCondition,
    # Accumulation Layer 2
    OBVDivergenceCondition,
    StochasticDivergenceCondition,
    VPCIDivergenceCondition,
    # Breakout
    BottomBreakoutCondition,
    FreshBreakoutCondition,
    BreakoutWithVolumeCondition,
    ResistanceBreakoutCondition,
)
from screener import StockScreener
from api.services.screening_service import ScreeningService

logger = logging.getLogger(__name__)


# Maps condition type strings to their classes
CONDITION_CLASS_MAP: Dict[str, Type[BaseCondition]] = {
    # Price
    "min_price": MinPriceCondition,
    "max_price": MaxPriceCondition,
    "price_range": PriceRangeCondition,
    "price_change": PriceChangeCondition,
    # Volume
    "min_volume": MinVolumeCondition,
    "volume_above_avg": VolumeAboveAvgCondition,
    "volume_spike": VolumeSpikeCondition,
    # MA
    "ma_touch": MATouchCondition,
    "above_ma": AboveMACondition,
    "below_ma": BelowMACondition,
    "ma_cross_up": MACrossUpCondition,
    "ma_cross_down": MACrossDownCondition,
    # RSI
    "rsi_oversold": RSIOversoldCondition,
    "rsi_overbought": RSIOverboughtCondition,
    "rsi_range": RSIRangeCondition,
    # Accumulation Layer 1
    "bollinger_width": BollingerWidthCondition,
    "volume_below_avg": VolumeBelowAvgCondition,
    "price_flat": PriceFlatCondition,
    "obv_trend": OBVTrendCondition,
    "stochastic_level": StochasticLevelCondition,
    "vpci_trend": VPCITrendCondition,
    # Accumulation Layer 2
    "obv_divergence": OBVDivergenceCondition,
    "stochastic_divergence": StochasticDivergenceCondition,
    "vpci_divergence": VPCIDivergenceCondition,
    # Breakout
    "bottom_breakout": BottomBreakoutCondition,
    "fresh_breakout": FreshBreakoutCondition,
    "breakout_with_volume": BreakoutWithVolumeCondition,
    "resistance_breakout": ResistanceBreakoutCondition,
}

# Condition metadata for the palette (key -> label, category, params)
CONDITION_METADATA: Dict[str, Dict[str, Any]] = {
    # Price
    "min_price": {
        "label": "Min Price",
        "description": "Stock price >= threshold",
        "category": "Price",
        "params": [
            {"name": "min_price", "type": "float", "default": 5000, "description": "Minimum price"},
        ],
    },
    "max_price": {
        "label": "Max Price",
        "description": "Stock price <= threshold",
        "category": "Price",
        "params": [
            {"name": "max_price", "type": "float", "default": 100000, "description": "Maximum price"},
        ],
    },
    "price_range": {
        "label": "Price Range",
        "description": "Stock price within range",
        "category": "Price",
        "params": [
            {"name": "min_price", "type": "float", "default": 0, "description": "Min price"},
            {"name": "max_price", "type": "float", "default": 999999, "description": "Max price"},
        ],
    },
    "price_change": {
        "label": "Price Change %",
        "description": "Price change over N days",
        "category": "Price",
        "params": [
            {"name": "min_change_pct", "type": "float", "default": None, "description": "Min change %"},
            {"name": "max_change_pct", "type": "float", "default": None, "description": "Max change %"},
            {"name": "days", "type": "int", "default": 1, "description": "Period (days)"},
        ],
    },
    # Volume
    "min_volume": {
        "label": "Min Volume",
        "description": "Volume >= threshold",
        "category": "Volume",
        "params": [
            {"name": "min_volume", "type": "int", "default": 100000, "description": "Minimum volume"},
        ],
    },
    "volume_above_avg": {
        "label": "Volume Above Avg",
        "description": "Volume above moving average",
        "category": "Volume",
        "params": [
            {"name": "multiplier", "type": "float", "default": 1.5, "description": "Avg multiplier"},
            {"name": "period", "type": "int", "default": 20, "description": "Average period"},
        ],
    },
    "volume_spike": {
        "label": "Volume Spike",
        "description": "Sudden volume increase",
        "category": "Volume",
        "params": [
            {"name": "multiplier", "type": "float", "default": 2.0, "description": "Spike multiplier"},
            {"name": "period", "type": "int", "default": 20, "description": "Average period"},
        ],
    },
    # MA
    "ma_touch": {
        "label": "MA Touch",
        "description": "Price near moving average",
        "category": "Moving Average",
        "params": [
            {"name": "period", "type": "int", "default": 20, "description": "MA period"},
            {"name": "threshold", "type": "float", "default": 0.02, "description": "Touch threshold (ratio)"},
        ],
    },
    "above_ma": {
        "label": "Above MA",
        "description": "Price above moving average",
        "category": "Moving Average",
        "params": [
            {"name": "period", "type": "int", "default": 20, "description": "MA period"},
            {"name": "min_distance_pct", "type": "float", "default": 0, "description": "Min distance %"},
        ],
    },
    "below_ma": {
        "label": "Below MA",
        "description": "Price below moving average",
        "category": "Moving Average",
        "params": [
            {"name": "period", "type": "int", "default": 20, "description": "MA period"},
            {"name": "max_distance_pct", "type": "float", "default": 0, "description": "Max distance %"},
        ],
    },
    "ma_cross_up": {
        "label": "MA Cross Up",
        "description": "Golden cross (short MA crosses above long MA)",
        "category": "Moving Average",
        "params": [
            {"name": "short_period", "type": "int", "default": 20, "description": "Short MA period"},
            {"name": "long_period", "type": "int", "default": 60, "description": "Long MA period"},
            {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
        ],
    },
    "ma_cross_down": {
        "label": "MA Cross Down",
        "description": "Death cross (short MA crosses below long MA)",
        "category": "Moving Average",
        "params": [
            {"name": "short_period", "type": "int", "default": 20, "description": "Short MA period"},
            {"name": "long_period", "type": "int", "default": 60, "description": "Long MA period"},
            {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
        ],
    },
    # RSI
    "rsi_oversold": {
        "label": "RSI Oversold",
        "description": "RSI below threshold",
        "category": "RSI",
        "params": [
            {"name": "threshold", "type": "float", "default": 30, "description": "RSI threshold"},
            {"name": "period", "type": "int", "default": 14, "description": "RSI period"},
        ],
    },
    "rsi_overbought": {
        "label": "RSI Overbought",
        "description": "RSI above threshold",
        "category": "RSI",
        "params": [
            {"name": "threshold", "type": "float", "default": 70, "description": "RSI threshold"},
            {"name": "period", "type": "int", "default": 14, "description": "RSI period"},
        ],
    },
    "rsi_range": {
        "label": "RSI Range",
        "description": "RSI within range",
        "category": "RSI",
        "params": [
            {"name": "lower", "type": "float", "default": 30, "description": "Lower bound"},
            {"name": "upper", "type": "float", "default": 70, "description": "Upper bound"},
            {"name": "period", "type": "int", "default": 14, "description": "RSI period"},
        ],
    },
    # Accumulation Layer 1
    "bollinger_width": {
        "label": "Bollinger Width",
        "description": "BB width contraction",
        "category": "Accumulation",
        "params": [
            {"name": "max_width_pct", "type": "float", "default": 10.0, "description": "Max BB width %"},
            {"name": "period", "type": "int", "default": 20, "description": "BB period"},
            {"name": "std_dev", "type": "float", "default": 2.0, "description": "Std deviation"},
        ],
    },
    "volume_below_avg": {
        "label": "Volume Below Avg",
        "description": "Quiet volume zone",
        "category": "Accumulation",
        "params": [
            {"name": "multiplier", "type": "float", "default": 0.8, "description": "Max ratio to avg"},
            {"name": "period", "type": "int", "default": 20, "description": "Average period"},
        ],
    },
    "price_flat": {
        "label": "Price Flat",
        "description": "Price consolidation (low volatility)",
        "category": "Accumulation",
        "params": [
            {"name": "max_range_pct", "type": "float", "default": 5.0, "description": "Max range %"},
            {"name": "period", "type": "int", "default": 20, "description": "Period"},
        ],
    },
    "obv_trend": {
        "label": "OBV Trend",
        "description": "On-Balance Volume trend direction",
        "category": "Accumulation",
        "params": [
            {"name": "direction", "type": "str", "default": "up", "description": "Trend direction (up/down)"},
            {"name": "lookback", "type": "int", "default": 20, "description": "Lookback period"},
        ],
    },
    "stochastic_level": {
        "label": "Stochastic Level",
        "description": "Stochastic oscillator level",
        "category": "Accumulation",
        "params": [
            {"name": "threshold", "type": "float", "default": 20.0, "description": "Level threshold"},
            {"name": "condition", "type": "str", "default": "below", "description": "below or above"},
            {"name": "k_period", "type": "int", "default": 14, "description": "%K period"},
            {"name": "d_period", "type": "int", "default": 3, "description": "%D period"},
        ],
    },
    "vpci_trend": {
        "label": "VPCI Trend",
        "description": "Volume Price Confirmation Indicator trend",
        "category": "Accumulation",
        "params": [
            {"name": "direction", "type": "str", "default": "up", "description": "Trend direction (up/down)"},
            {"name": "short_period", "type": "int", "default": 5, "description": "Short period"},
            {"name": "long_period", "type": "int", "default": 20, "description": "Long period"},
            {"name": "lookback", "type": "int", "default": 10, "description": "Lookback period"},
        ],
    },
    # Accumulation Layer 2
    "obv_divergence": {
        "label": "OBV Divergence",
        "description": "Price flat + OBV rising (accumulation signal)",
        "category": "Accumulation",
        "params": [
            {"name": "price_max_range_pct", "type": "float", "default": 5.0, "description": "Price range %"},
            {"name": "obv_min_change_pct", "type": "float", "default": 5.0, "description": "OBV change %"},
            {"name": "period", "type": "int", "default": 20, "description": "Period"},
        ],
    },
    "stochastic_divergence": {
        "label": "Stochastic Divergence",
        "description": "Price lower low + Stochastic higher low",
        "category": "Accumulation",
        "params": [
            {"name": "k_period", "type": "int", "default": 14, "description": "%K period"},
            {"name": "d_period", "type": "int", "default": 3, "description": "%D period"},
            {"name": "lookback", "type": "int", "default": 20, "description": "Lookback period"},
            {"name": "divergence_threshold", "type": "float", "default": 5.0, "description": "Threshold %"},
        ],
    },
    "vpci_divergence": {
        "label": "VPCI Divergence",
        "description": "Price flat + VPCI rising (quiet accumulation)",
        "category": "Accumulation",
        "params": [
            {"name": "price_max_range_pct", "type": "float", "default": 5.0, "description": "Price range %"},
            {"name": "short_period", "type": "int", "default": 5, "description": "Short period"},
            {"name": "long_period", "type": "int", "default": 20, "description": "Long period"},
            {"name": "lookback", "type": "int", "default": 20, "description": "Lookback period"},
        ],
    },
    # Breakout
    "bottom_breakout": {
        "label": "Bottom Breakout",
        "description": "N-day low breakout",
        "category": "Breakout",
        "params": [
            {"name": "lookback_days", "type": "int", "default": 20, "description": "Lookback days"},
            {"name": "breakout_pct", "type": "float", "default": 5.0, "description": "Breakout %"},
        ],
    },
    "fresh_breakout": {
        "label": "Fresh Breakout",
        "description": "First-time breakout detection",
        "category": "Breakout",
        "params": [
            {"name": "lookback_days", "type": "int", "default": 20, "description": "Lookback days"},
            {"name": "breakout_pct", "type": "float", "default": 5.0, "description": "Breakout %"},
        ],
    },
    "breakout_with_volume": {
        "label": "Breakout + Volume",
        "description": "Breakout confirmed by volume spike",
        "category": "Breakout",
        "params": [
            {"name": "lookback_days", "type": "int", "default": 20, "description": "Lookback days"},
            {"name": "breakout_pct", "type": "float", "default": 5.0, "description": "Breakout %"},
            {"name": "volume_ratio", "type": "float", "default": 1.5, "description": "Volume ratio"},
            {"name": "volume_avg_days", "type": "int", "default": 10, "description": "Volume avg days"},
            {"name": "fresh_only", "type": "bool", "default": True, "description": "Fresh breakout only"},
        ],
    },
    "resistance_breakout": {
        "label": "Resistance Breakout",
        "description": "N-day high resistance breakout",
        "category": "Breakout",
        "params": [
            {"name": "lookback_days", "type": "int", "default": 20, "description": "Lookback days"},
            {"name": "breakout_margin_pct", "type": "float", "default": 0.0, "description": "Margin above resistance %"},
        ],
    },
}


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
