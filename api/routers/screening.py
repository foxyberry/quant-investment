"""
Screening router.

Provides endpoints for stock screening operations.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query

from api.schemas.screening import (
    ScreeningRequest,
    ScreeningResponse,
    ScreeningResultItem,
    PresetInfo,
    UniverseInfo,
    SingleStockRequest,
    find_invalid_universes,
    format_invalid_universe_error,
)
from api.services.screening_service import get_screening_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screening", tags=["Screening"])


@router.get(
    "/presets",
    response_model=List[PresetInfo],
    summary="Get Available Presets",
    description="Get list of available screening presets with their descriptions and conditions.",
)
def get_presets() -> List[PresetInfo]:
    """
    Get available screening presets.

    Returns a list of all available presets with their names,
    descriptions, and the conditions they contain.

    Returns:
        List of PresetInfo objects
    """
    service = get_screening_service()
    return service.get_available_presets()


@router.get(
    "/universes",
    response_model=List[UniverseInfo],
    summary="Get Available Universes",
    description="Get list of available stock universes (KOSPI, KOSDAQ, SP500, etc.).",
)
def get_universes() -> List[UniverseInfo]:
    """
    Get available stock universes.

    Returns a list of all available universes with their names,
    descriptions, and approximate stock counts.

    Returns:
        List of UniverseInfo objects
    """
    service = get_screening_service()
    return service.get_available_universes()


@router.post(
    "/run",
    response_model=ScreeningResponse,
    summary="Run Screening",
    description="Run stock screening with the specified preset and universe. "
                "This operation may take several minutes depending on the universe size.",
)
def run_screening(request: ScreeningRequest) -> ScreeningResponse:
    """
    Run stock screening.

    Executes screening on the specified universe using the given preset.
    Returns all stocks that match all conditions in the preset.

    Note: This is a synchronous operation that may take several minutes
    for large universes (e.g., KOSPI with 900+ stocks).

    Args:
        request: ScreeningRequest with preset, universe, and optional params

    Returns:
        ScreeningResponse with matched stocks

    Raises:
        HTTPException: If preset or universe is invalid
    """
    service = get_screening_service()

    invalid_universes = find_invalid_universes(request.universes)
    if invalid_universes:
        raise HTTPException(
            status_code=400,
            detail=format_invalid_universe_error(invalid_universes),
        )

    try:
        result = service.run_screening(
            preset=request.preset,
            universe=request.universe,
            universes=request.universes,
            params=request.params,
            reference_date=request.reference_date,
        )

        return ScreeningResponse(
            results=result["results"],
            total_count=result["total_count"],
            matched_count=result["matched_count"],
            universe=request.universe,
            universes=request.universes,
            reference_date=request.reference_date,
            elapsed_ms=result.get("elapsed_ms"),
        )

    except ValueError as e:
        logger.warning(f"Screening request failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Screening error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Screening failed: {str(e)}"
        )


@router.get(
    "/stock/{ticker}",
    response_model=ScreeningResultItem,
    summary="Check Single Stock",
    description="Check a single stock against screening conditions.",
)
def check_single_stock(
    ticker: str,
    preset: str = Query(
        default="accumulation_basic",
        description="Preset name for screening conditions"
    ),
) -> ScreeningResultItem:
    """
    Check a single stock against screening conditions.

    Evaluates the specified stock against the given preset conditions
    and returns detailed results for each condition.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, 005930.KS)
        preset: Preset name (default: accumulation_basic)

    Returns:
        ScreeningResultItem with evaluation results

    Raises:
        HTTPException: If ticker or preset is invalid
    """
    service = get_screening_service()

    try:
        result = service.check_single_stock(
            ticker=ticker,
            preset=preset,
            params=None
        )
        return result

    except ValueError as e:
        logger.warning(f"Single stock check failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Single stock check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Stock check failed: {str(e)}"
        )


@router.post(
    "/stock/{ticker}",
    response_model=ScreeningResultItem,
    summary="Check Single Stock with Params",
    description="Check a single stock against screening conditions with custom parameters.",
)
def check_single_stock_with_params(
    ticker: str,
    request: SingleStockRequest,
) -> ScreeningResultItem:
    """
    Check a single stock with custom parameters.

    Evaluates the specified stock against the given preset conditions
    with optional parameter overrides.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, 005930.KS)
        request: SingleStockRequest with preset and optional params

    Returns:
        ScreeningResultItem with evaluation results

    Raises:
        HTTPException: If ticker or preset is invalid
    """
    service = get_screening_service()

    try:
        result = service.check_single_stock(
            ticker=ticker,
            preset=request.preset,
            params=request.params
        )
        return result

    except ValueError as e:
        logger.warning(f"Single stock check failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Single stock check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Stock check failed: {str(e)}"
        )
