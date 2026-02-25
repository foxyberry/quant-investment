"""
API Routers module.

Export all routers for registration in the main application.
"""

from api.routers.analysis import router as analysis_router
from api.routers.broker import router as broker_router
from api.routers.exchange_rates import router as exchange_rates_router
from api.routers.health import router as health_router
from api.routers.kiwoom import router as kiwoom_router
from api.routers.market import router as market_router
from api.routers.portfolio import router as portfolio_router
from api.routers.screening import router as screening_router
from api.routers.search import router as search_router
from api.routers.backtest import router as backtest_router
from api.routers.strategy import router as strategy_router

__all__ = [
    "analysis_router",
    "backtest_router",
    "broker_router",
    "exchange_rates_router",
    "health_router",
    "kiwoom_router",
    "market_router",
    "portfolio_router",
    "screening_router",
    "search_router",
    "strategy_router",
]
