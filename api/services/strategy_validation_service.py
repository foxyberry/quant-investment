"""
Strategy Validation Service.

Runs cross-validation on a saved strategy's indicators and promotes
the strategy status from 'backtested' to 'validated' when all checks pass.
"""

import logging
from typing import List

from api.schemas.cross_validation import IndicatorComparison
from api.schemas.strategy_validation import (
    StrategyValidateResponse,
)
from api.services.cross_validation_service import run_cross_validation
from api.services.strategy_save_service import get_strategy_save_service

logger = logging.getLogger(__name__)

# Condition types that map to cross-validatable indicators
_CONDITION_TO_INDICATORS = {
    "rsi_oversold": ["RSI"],
    "rsi_overbought": ["RSI"],
    "macd_cross": ["MACD"],
    "macd_golden_cross": ["MACD"],
    "macd_above_signal": ["MACD"],
    "bb_squeeze": ["BB"],
    "bb_breakout": ["BB"],
    "bollinger_lower": ["BB"],
    "bollinger_upper": ["BB"],
}


def _extract_indicator_types(graph_dict: dict) -> List[str]:
    """Extract unique indicator types from a strategy graph.

    Looks at condition nodes and maps their condition_type to indicator groups.
    """
    indicator_types: set = set()
    nodes = graph_dict.get("nodes", [])
    for node in nodes:
        data = node.get("data", {})
        if data.get("node_type") != "condition":
            continue
        condition_type = data.get("condition_type", "")
        indicators = _CONDITION_TO_INDICATORS.get(condition_type, [])
        indicator_types.update(indicators)
    return sorted(indicator_types)


def _filter_comparisons(
    comparisons: List[IndicatorComparison],
    indicator_types: List[str],
) -> List[IndicatorComparison]:
    """Filter cross-validation comparisons to only include relevant indicators."""
    filtered = []
    for comp in comparisons:
        name_upper = comp.name.upper()
        for ind_type in indicator_types:
            if ind_type in name_upper:
                filtered.append(comp)
                break
    return filtered


def validate_strategy(
    strategy_id: str,
    ticker: str = "AAPL",
    period: str = "1y",
) -> StrategyValidateResponse:
    """Run cross-validation on a strategy's indicators and promote if all pass.

    Args:
        strategy_id: ID of the saved strategy.
        ticker: Ticker to use for cross-validation data.
        period: Data period for cross-validation.

    Returns:
        StrategyValidateResponse with comparisons and status update info.

    Raises:
        ValueError: If strategy not found or not in 'backtested' status.
    """
    svc = get_strategy_save_service()
    strategy = svc.get_strategy(strategy_id)
    if strategy is None:
        raise ValueError(f"Strategy not found: {strategy_id}")

    status_before = strategy.status

    # Extract indicator types from the graph
    graph_dict = strategy.graph
    if not isinstance(graph_dict, dict):
        graph_dict = graph_dict.model_dump() if hasattr(graph_dict, "model_dump") else {}
    indicator_types = _extract_indicator_types(graph_dict)

    if not indicator_types:
        return StrategyValidateResponse(
            strategy_id=strategy_id,
            indicators_tested=[],
            comparisons=[],
            all_pass=False,
            status_before=status_before,
            status_after=status_before,
            message="No cross-validatable indicators found in this strategy.",
        )

    # Run cross-validation
    cv_result = run_cross_validation(ticker=ticker, period=period)

    # Filter to only relevant comparisons
    relevant = _filter_comparisons(cv_result.comparisons, indicator_types)
    all_pass = len(relevant) > 0 and all(c.match for c in relevant)

    # Promote if all pass and strategy is in 'backtested' status
    status_after = status_before
    message = ""
    if all_pass and status_before == "backtested":
        try:
            svc.update_status(strategy_id, "validated")
            status_after = "validated"
            message = "All indicators passed cross-validation. Status promoted to 'validated'."
        except ValueError as e:
            message = f"Cross-validation passed but status update failed: {e}"
    elif all_pass:
        message = f"All indicators passed. Status not changed (current: '{status_before}', promotion requires 'backtested')."
    else:
        failed = [c.name for c in relevant if not c.match]
        message = f"Cross-validation failed for: {', '.join(failed)}. Status unchanged."

    return StrategyValidateResponse(
        strategy_id=strategy_id,
        indicators_tested=indicator_types,
        comparisons=relevant,
        all_pass=all_pass,
        status_before=status_before,
        status_after=status_after,
        message=message,
    )
