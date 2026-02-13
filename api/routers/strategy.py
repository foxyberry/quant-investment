"""
Strategy Router.

Endpoints for the visual strategy builder.
"""

import logging

from fastapi import APIRouter, HTTPException

from api.schemas.strategy import (
    ConditionsListResponse,
    StrategyExecuteRequest,
    StrategyExecuteResponse,
)
from api.services.strategy_service import (
    execute_strategy,
    get_available_conditions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategy", tags=["Strategy"])


@router.get(
    "/conditions",
    response_model=ConditionsListResponse,
    summary="Get available conditions",
    description="Return all available condition types with their parameter schemas.",
)
async def list_conditions() -> ConditionsListResponse:
    """Return available condition types for the node palette."""
    conditions = get_available_conditions()
    categories = sorted(set(c.category for c in conditions))
    return ConditionsListResponse(conditions=conditions, categories=categories)


@router.post(
    "/run",
    response_model=StrategyExecuteResponse,
    summary="Execute visual strategy",
    description="Execute a visual strategy graph and return screening results.",
)
async def run_strategy(request: StrategyExecuteRequest) -> StrategyExecuteResponse:
    """Execute a visual strategy graph."""
    try:
        result = execute_strategy(
            graph=request.graph,
            universe_override=request.universe_override,
        )
        return StrategyExecuteResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Strategy execution failed")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")
