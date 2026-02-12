"""
Market data router.

Provides endpoints for OHLCV data, quotes, and technical indicators.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from api.schemas.market import OHLCVResponse, QuoteResponse, TechnicalIndicators
from api.services.market_service import MarketService

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


@router.get(
    "/quote/{ticker}",
    response_model=QuoteResponse,
    summary="Get Current Quote",
    description="Retrieve current price quote for a stock ticker.",
)
async def get_quote(ticker: str) -> QuoteResponse:
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
async def get_ohlcv(
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
async def get_technical_indicators(ticker: str) -> TechnicalIndicators:
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
