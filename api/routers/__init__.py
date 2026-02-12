"""
API Routers module.

Export all routers for registration in the main application.
"""

from api.routers.health import router as health_router
from api.routers.market import router as market_router
from api.routers.screening import router as screening_router

__all__ = ["health_router", "market_router", "screening_router"]
