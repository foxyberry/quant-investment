"""
Cross-Validation Router.

Endpoint for comparing our indicator calculations against TradingView-compatible
reference values using the ta library.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas.cross_validation import CrossValidationResponse
from api.services.cross_validation_service import run_cross_validation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cross-validation", tags=["Cross-Validation"])

_VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}


@router.get(
    "/{ticker}",
    response_model=CrossValidationResponse,
    summary="Cross-validate indicators for a ticker",
    description="Compare our indicator calculations (RSI, MACD, BB) against "
    "TradingView-compatible reference values. Returns a comparison table "
    "with match status and known divergence explanations.",
)
def cross_validate(
    ticker: str,
    period: Optional[str] = Query(
        default="1y",
        description="Data period: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
    ),
) -> CrossValidationResponse:
    """Run cross-validation for a ticker's technical indicators."""
    if period not in _VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Valid: {', '.join(sorted(_VALID_PERIODS))}",
        )
    try:
        result = run_cross_validation(ticker=ticker, period=period)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.exception("Cross-validation server error for %s", ticker)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger.exception("Cross-validation failed for %s", ticker)
        raise HTTPException(
            status_code=500, detail="Cross-validation failed. Check server logs."
        )
