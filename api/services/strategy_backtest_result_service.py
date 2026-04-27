"""
Strategy Backtest Result Service — compatibility shim.

All logic has been moved to api.services.strategy.strategy_analytics_service.
This module re-exports for backward compatibility.
"""

from api.services.strategy.strategy_analytics_service import (  # noqa: F401
    save_backtest_result,
    get_results,
    get_latest,
    _row_to_response,
)
