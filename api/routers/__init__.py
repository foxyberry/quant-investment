"""
API Routers module.

Export all routers for registration in the main application.
"""

from api.routers.health import router as health_router

__all__ = ["health_router"]
