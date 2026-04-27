"""
Strategy Service — compatibility shim.

All logic has been moved to the api.services.strategy sub-package.
This module re-exports everything so that existing import paths continue
to work without modification:

    from api.services.strategy_service import execute_strategy
    from api.services.strategy_service import CONDITION_CLASS_MAP
    ...
"""

from api.services.strategy import (  # noqa: F401
    CONDITION_CLASS_MAP,
    CONDITION_METADATA,
    WARN_TICKERS_THRESHOLD,
    MAX_TICKERS_PER_RUN,
    _to_optional_float,
    _is_korean_ticker,
    _extract_krx_code,
    _sanitize_value,
    _coerce_param,
    _build_condition,
    get_available_conditions,
    build_conditions_from_graph,
    build_flat_conditions_from_graph,
    enrich_fundamentals,
    execute_strategy,
    execute_strategy_with_progress,
    _build_weighted_portfolio,
    _build_ranking_outputs,
    _compute_node_survivors,
    _passes_node,
    _resolve_execution_universes,
    save_backtest_result,
    get_results,
    get_latest,
    compare_strategies,
    get_leaderboard,
)
