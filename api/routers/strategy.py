"""
Strategy Router.

Endpoints for the visual strategy builder.
"""

import logging

from fastapi import APIRouter, HTTPException

from api.schemas.strategy import (
    ConditionsListResponse,
    SavedStrategiesListResponse,
    SavedStrategyResponse,
    SectorInfo,
    SectorListResponse,
    StrategyExecuteRequest,
    StrategyExecuteResponse,
    StrategySaveRequest,
    StrategyUpdateRequest,
)
from api.services.strategy_save_service import get_strategy_save_service
from api.services.strategy_service import (
    execute_strategy,
    get_available_conditions,
)
from screener.sector_fetcher import get_sector_fetcher

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
    conditions.sort(key=lambda c: (not c.recommended, c.order, c.key))
    categories = sorted(set(c.category for c in conditions))
    return ConditionsListResponse(conditions=conditions, categories=categories)


@router.get(
    "/saved",
    response_model=SavedStrategiesListResponse,
    summary="List saved strategies",
    description="Return all saved strategy graphs.",
)
async def list_saved_strategies() -> SavedStrategiesListResponse:
    """List all saved strategies."""
    service = get_strategy_save_service()
    strategies = service.list_strategies()
    return SavedStrategiesListResponse(
        strategies=strategies,
        total_count=len(strategies),
    )


@router.post(
    "/saved",
    response_model=SavedStrategyResponse,
    status_code=201,
    summary="Save strategy",
    description="Save a new strategy graph.",
)
async def save_strategy(data: StrategySaveRequest) -> SavedStrategyResponse:
    """Save a new strategy graph."""
    service = get_strategy_save_service()
    try:
        return service.save_strategy(data)
    except Exception as e:
        logger.error(f"Failed to save strategy: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save strategy: {str(e)}",
        )


@router.get(
    "/saved/{strategy_id}",
    response_model=SavedStrategyResponse,
    summary="Get saved strategy",
    description="Get one saved strategy by ID.",
)
async def get_saved_strategy(strategy_id: str) -> SavedStrategyResponse:
    """Get one saved strategy."""
    service = get_strategy_save_service()
    try:
        strategy = service.get_strategy(strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        return strategy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get strategy: {str(e)}",
        )


@router.put(
    "/saved/{strategy_id}",
    response_model=SavedStrategyResponse,
    summary="Update saved strategy",
    description="Update an existing saved strategy.",
)
async def update_saved_strategy(
    strategy_id: str,
    data: StrategyUpdateRequest,
) -> SavedStrategyResponse:
    """Update one saved strategy."""
    service = get_strategy_save_service()
    try:
        strategy = service.update_strategy(strategy_id, data)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        return strategy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update strategy: {str(e)}",
        )


@router.delete(
    "/saved/{strategy_id}",
    status_code=204,
    summary="Delete saved strategy",
    description="Delete a saved strategy.",
)
async def delete_saved_strategy(strategy_id: str) -> None:
    """Delete one saved strategy."""
    service = get_strategy_save_service()
    try:
        success = service.delete_strategy(strategy_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete strategy: {str(e)}",
        )


@router.get(
    "/sectors",
    response_model=SectorListResponse,
    summary="Get available sectors",
    description="Return all available sectors for a given market with stock counts.",
)
async def list_sectors(market: str = "KOSPI") -> SectorListResponse:
    """Return available sectors for the node palette."""
    market_upper = market.upper()
    if market_upper not in ("KOSPI", "KOSDAQ"):
        raise HTTPException(
            status_code=400,
            detail=f"Sector listing is only supported for KOSPI and KOSDAQ, got: {market}",
        )
    try:
        fetcher = get_sector_fetcher()
        sector_counts = fetcher.get_sector_counts(market_upper)
        sectors = [
            SectorInfo(name=name, stock_count=count)
            for name, count in sorted(sector_counts.items())
        ]
        return SectorListResponse(
            market=market_upper,
            sectors=sectors,
            total_sectors=len(sectors),
        )
    except Exception as e:
        logger.exception("Failed to fetch sectors for %s", market)
        raise HTTPException(status_code=500, detail="Failed to fetch sector data")


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
