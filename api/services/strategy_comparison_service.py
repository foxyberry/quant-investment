"""
Strategy Comparison Service — compatibility shim.

All logic has been moved to api.services.strategy.strategy_analytics_service.
This module re-exports for backward compatibility.
"""

from api.services.strategy.strategy_analytics_service import (  # noqa: F401
    compare_strategies,
    get_leaderboard,
    _best_by,
    _SORT_COLUMNS,
)
