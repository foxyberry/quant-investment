"""
Market data router.

Provides endpoints for OHLCV data, quotes, and technical indicators.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, List, Literal

from fastapi import APIRouter, HTTPException, Query

from api.schemas.market import (
    MacroBondSnapshot,
    MacroBundleResponse,
    MacroDataQuality,
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
from api.services.us_scoring_service import get_us_scoring_service
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
_us_scoring_service = get_us_scoring_service()


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

    # US market data + scoring — only in US mode
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

        # Compute US composite score from VIX, Treasury curve, S&P 500
        try:
            vol_data = result.get("volatility") or {}
            bonds_data = result.get("bonds") or {}
            us_market_data = result.get("us_market") or {}
            us_bundle = _us_scoring_service.compute_us_bundle(
                vix=vol_data.get("vix"),
                vix_as_of=vol_data.get("vix_as_of"),
                spread_2_10=bonds_data.get("us_spread_2_10"),
                bonds_updated_at=bonds_data.get("source_updated_at"),
                sp500_value=us_market_data.get("sp500_value"),
                sp500_change_pct=us_market_data.get("sp500_change_pct"),
                sp500_as_of=us_market_data.get("sp500_as_of"),
            )
            result["signal"] = us_bundle["signal"]
            result["interpretation"] = us_bundle["interpretation"]
        except Exception:
            logger.warning("Failed to compute US scoring", exc_info=True)

    # --- Data quality assessment ---
    dq = _compute_data_quality(result, is_kr)
    result["data_quality"] = dq.model_dump()

    return MacroBundleResponse(**result)


def _compute_data_quality(bundle: dict, is_kr: bool) -> MacroDataQuality:
    """Derive per-series quality from freshness ages and presence.

    Thresholds (seconds):
      FX:         1200 (20 min)
      Futures:    1200 (20 min)
      Flow:       1800 (30 min)
      Volatility: 7200 (2 h)   — external sources update less frequently
    """
    THRESHOLDS = {
        "fx": 1200,
        "futures": 1200,
        "flow": 1800,
    }

    freshness = bundle.get("freshness") or {}

    def _series_quality(key: str) -> str:
        age_key = f"{key}_age_sec"
        age_sec = freshness.get(age_key)
        # If the whole section is None, it's missing
        if bundle.get(key) is None:
            return "missing"
        if age_sec is None:
            return "missing"
        return "stale" if age_sec > THRESHOLDS.get(key, 3600) else "ok"

    # Volatility uses its own timestamp field
    def _vol_quality() -> str:
        vol = bundle.get("volatility")
        if vol is None:
            return "missing"
        if vol.get("vix") is None and vol.get("vkospi") is None:
            return "missing"
        # Use vix_as_of or vkospi_as_of to check staleness
        for ts_key in ("vix_as_of", "vkospi_as_of"):
            ts = vol.get(ts_key)
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - dt).total_seconds()
                    return "stale" if age > 7200 else "ok"
                except (ValueError, TypeError):
                    pass
        return "stale"  # has data but no timestamp → conservative

    if is_kr:
        return MacroDataQuality(
            fx=_series_quality("fx"),
            futures=_series_quality("futures"),
            flow=_series_quality("flow"),
            volatility=_vol_quality(),
        )
    else:
        # US mode: fx/futures/flow are not used
        return MacroDataQuality(
            fx=None,
            futures=None,
            flow=None,
            volatility=_vol_quality(),
        )


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

    # Compute data coverage: % of points with non-null macro_score
    points = result.get("points", [])
    if points:
        non_null = sum(1 for p in points if p.get("macro_score") is not None)
        result["data_coverage_pct"] = round(non_null / len(points) * 100, 1)
    else:
        result["data_coverage_pct"] = 0.0

    return MacroHistoryResponse(**result)
