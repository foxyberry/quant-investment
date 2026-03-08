"""
Market data router.

Provides endpoints for OHLCV data, quotes, and technical indicators.
"""

import logging
from typing import Annotated, List

from fastapi import APIRouter, HTTPException, Query

from api.schemas.market import (
    MacroBundleResponse,
    MacroHistoryResponse,
    OHLCVResponse,
    QuoteResponse,
    TechnicalIndicators,
)
from api.schemas.analysis import SearchResult
from api.services.market_service import MarketService
from api.services.macro_market_service import get_macro_market_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/market",
    tags=["Market Data"],
    responses={
        404: {"description": "Ticker not found or data unavailable"},
        500: {"description": "Internal server error"},
    },
)

# Service instance
_service = MarketService()
_macro_service = get_macro_market_service(_service)


@router.get(
    "/quote/{ticker}",
    response_model=QuoteResponse,
    summary="Get Current Quote",
    description="Retrieve current price quote for a stock ticker.",
)
def get_quote(ticker: str) -> QuoteResponse:
    """
    Get current quote for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', '005930.KS')

    Returns:
        QuoteResponse with current price, change, and volume

    Raises:
        HTTPException: 404 if ticker not found or data unavailable
    """
    result = _service.get_quote(ticker)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Quote data not available for ticker: {ticker}",
        )

    return QuoteResponse(**result)


@router.get(
    "/ohlcv/{ticker}",
    response_model=OHLCVResponse,
    summary="Get OHLCV Data",
    description="Retrieve historical OHLCV (Open-High-Low-Close-Volume) data.",
)
def get_ohlcv(
    ticker: str,
    days: Annotated[
        int,
        Query(
            ge=1,
            le=730,
            description="Number of days of historical data (1-730)",
        ),
    ] = 100,
) -> OHLCVResponse:
    """
    Get OHLCV data for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', '005930.KS')
        days: Number of days of historical data (default: 100, max: 730)

    Returns:
        OHLCVResponse with list of OHLCV data points

    Raises:
        HTTPException: 404 if ticker not found or data unavailable
    """
    result = _service.get_ohlcv(ticker, days=days)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"OHLCV data not available for ticker: {ticker}",
        )

    return OHLCVResponse(**result)


@router.get(
    "/technical/{ticker}",
    response_model=TechnicalIndicators,
    summary="Get Technical Indicators",
    description="Calculate technical indicators for a stock ticker.",
)
def get_technical_indicators(ticker: str) -> TechnicalIndicators:
    """
    Get technical indicators for a ticker.

    Calculates RSI, MACD, Bollinger Bands, and moving averages.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', '005930.KS')

    Returns:
        TechnicalIndicators with calculated values and signals

    Raises:
        HTTPException: 404 if ticker not found or data unavailable
    """
    result = _service.get_technical_indicators(ticker)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Technical indicator data not available for ticker: {ticker}",
        )

    return TechnicalIndicators(**result)


@router.get(
    "/macro/bundle",
    response_model=MacroBundleResponse,
    summary="Get Macro Bundle",
    description="Get aggregated macro snapshot for FX, futures, investor flow, and regime score.",
)
def get_macro_bundle() -> MacroBundleResponse:
    result = _macro_service.get_bundle()
    return MacroBundleResponse(**result)


@router.get(
    "/macro/history",
    response_model=MacroHistoryResponse,
    summary="Get Macro History",
    description="Get macro timeline points for a given window (e.g., 60m, 6h, 1d).",
)
def get_macro_history(
    window: Annotated[str, Query(min_length=2, max_length=8, description="Window string, e.g. 60m")]
    = "60m",
) -> MacroHistoryResponse:
    result = _macro_service.get_history(window=window)
    return MacroHistoryResponse(**result)
