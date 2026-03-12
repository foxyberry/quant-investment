"""
Market data router.

Provides endpoints for OHLCV data, quotes, and technical indicators.
"""

import logging
from typing import Annotated, List, Literal

from fastapi import APIRouter, HTTPException, Query

from api.schemas.market import (
    MacroBondSnapshot,
    MacroBundleResponse,
    MacroGlobalSnapshot,
    MacroHistoryResponse,
    MacroUsMarketSnapshot,
    MacroVolatilitySnapshot,
    OHLCVResponse,
    QuoteResponse,
    TechnicalIndicators,
)
from api.services.bond_rate_service import get_bond_rate_service
from api.schemas.analysis import SearchResult
from api.services.global_macro_service import get_global_macro_service
from api.services.market_service import MarketService
from api.services.macro_market_service import get_macro_market_service
from api.services.us_market_service import get_us_market_service
from api.services.volatility_service import get_volatility_service

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
_bond_service = get_bond_rate_service()
_volatility_service = get_volatility_service()
_global_macro_service = get_global_macro_service()
_us_market_service = get_us_market_service()


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
def get_macro_bundle(
    force: bool = Query(False, description="Bypass server cache and force fresh data collection"),
    mode: Literal["kr", "us"] = Query("kr", description="Market mode: 'kr' for Korean market, 'us' for US market"),
) -> MacroBundleResponse:
    is_kr = mode.lower() == "kr"

    if is_kr:
        result = _macro_service.get_bundle(force_refresh=force)
    else:
        # US mode: start from an empty bundle (all Optional fields default to None)
        result = MacroBundleResponse().model_dump()

    # Bonds — shared across modes
    try:
        snapshot = _bond_service.get_snapshot()
        if snapshot:
            bonds = MacroBondSnapshot(**snapshot)
            result["bonds"] = bonds.model_dump()
        else:
            result["bonds"] = None
    except Exception:
        logger.warning("Failed to fetch bond snapshot", exc_info=True)
        result["bonds"] = None

    # Volatility — shared across modes
    try:
        vol_snapshot = _volatility_service.get_snapshot()
        if vol_snapshot and (vol_snapshot.get("vix") is not None or vol_snapshot.get("vkospi") is not None):
            vol = MacroVolatilitySnapshot(**vol_snapshot)
            result["volatility"] = vol.model_dump()
        else:
            result["volatility"] = None
    except Exception:
        logger.warning("Failed to fetch volatility snapshot", exc_info=True)
        result["volatility"] = None

    # Global macro — shared across modes
    try:
        gm_snapshot = _global_macro_service.get_snapshot()
        if gm_snapshot:
            gm = MacroGlobalSnapshot(**gm_snapshot)
            result["global_macro"] = gm.model_dump()
        else:
            result["global_macro"] = None
    except Exception:
        logger.warning("Failed to fetch global macro snapshot", exc_info=True)
        result["global_macro"] = None

    # US market data — only in US mode
    if not is_kr:
        try:
            us_snapshot = _us_market_service.get_snapshot()
            if us_snapshot:
                us = MacroUsMarketSnapshot(**us_snapshot)
                result["us_market"] = us.model_dump()
            else:
                result["us_market"] = None
        except Exception:
            logger.warning("Failed to fetch US market snapshot", exc_info=True)
            result["us_market"] = None

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
