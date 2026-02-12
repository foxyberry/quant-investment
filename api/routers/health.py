"""
Health check router.

Provides endpoints for monitoring application health status.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from api.config import get_settings
from api.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API server.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the current status, timestamp, and version of the API.
    Used for monitoring and load balancer health checks.

    Returns:
        HealthResponse: Health status information
    """
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.app_version,
    )
