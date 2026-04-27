"""
api.services.strategy — strategy sub-package.

Re-exports all public symbols so that existing callers using:
    from api.services.strategy_service import <name>
can instead use:
    from api.services.strategy import <name>

The legacy flat module (api.services.strategy_service) still exists as a
thin compatibility shim that imports from here.
"""

# Core — condition registry, graph traversal, helpers
from api.services.strategy.strategy_core_service import (
    CONDITION_CLASS_MAP,
    CONDITION_METADATA,
    WARN_TICKERS_THRESHOLD,
    MAX_TICKERS_PER_RUN,
    _LEGACY_ALIAS_MAP,
    _to_optional_float,
    _is_korean_ticker,
    _extract_krx_code,
    _sanitize_value,
    _coerce_param,
    _build_condition,
    get_available_conditions,
    build_conditions_from_graph,
    build_flat_conditions_from_graph,
)

# Fundamentals — PER/PBR/dividend_yield enrichment + cache/fetch (for monkeypatching)
from api.services.strategy.strategy_fundamentals import (
    enrich_fundamentals,
    _fundamental_cache,
    _fetch_us_fundamentals,
    _fetch_kr_fundamentals,
)

# Portfolio helpers — weight math, ranking, node survivors (internal)
from api.services.strategy.strategy_portfolio_helpers import (
    build_weighted_portfolio as _build_weighted_portfolio,
    build_ranking_outputs as _build_ranking_outputs,
    compute_node_survivors as _compute_node_survivors,
    passes_node as _passes_node,
    _compute_inverse_vol_weights,
    _compute_risk_parity_weights,
    _estimate_return_matrix,
)

# Execution — universe resolution + main run
from api.services.strategy.strategy_execution_service import (
    execute_strategy,
    execute_strategy_with_progress,
    _resolve_execution_universes,
)

# Analytics — backtest results, comparison, leaderboard
from api.services.strategy.strategy_analytics_service import (
    save_backtest_result,
    get_results,
    get_latest,
    compare_strategies,
    get_leaderboard,
)

__all__ = [
    # Core
    "CONDITION_CLASS_MAP",
    "CONDITION_METADATA",
    "WARN_TICKERS_THRESHOLD",
    "MAX_TICKERS_PER_RUN",
    "_LEGACY_ALIAS_MAP",
    "_to_optional_float",
    "_is_korean_ticker",
    "_extract_krx_code",
    "_sanitize_value",
    "_coerce_param",
    "_build_condition",
    "get_available_conditions",
    "build_conditions_from_graph",
    "build_flat_conditions_from_graph",
    # Fundamentals
    "enrich_fundamentals",
    "_fundamental_cache",
    "_fetch_us_fundamentals",
    "_fetch_kr_fundamentals",
    # Portfolio helpers (exposed under legacy private names for shim compat)
    "_build_weighted_portfolio",
    "_build_ranking_outputs",
    "_compute_node_survivors",
    "_passes_node",
    "_compute_inverse_vol_weights",
    "_compute_risk_parity_weights",
    "_estimate_return_matrix",
    # Execution
    "execute_strategy",
    "execute_strategy_with_progress",
    "_resolve_execution_universes",
    # Analytics
    "save_backtest_result",
    "get_results",
    "get_latest",
    "compare_strategies",
    "get_leaderboard",
]
