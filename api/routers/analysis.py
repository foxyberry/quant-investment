"""
Analysis router.

Provides endpoints for stock analysis and data enrichment operations.
"""

import logging
from typing import List, Optional

import yfinance as yf
from fastapi import APIRouter, HTTPException, Query

from api.schemas.analysis import (
    EnrichRequest,
    EnrichedStock,
    AnalysisRequest,
    AnalysisResult,
    ReportSummary,
    ReportDetail,
    ReportListResponse,
    EnrichedDataResponse,
    OHLCVDataPoint,
    TickerTechnicalIndicators,
    TickerFundamental,
    TickerAnalysisResponse,
)
from api.services.analysis_service import get_analysis_service
from api.services.market_service import MarketService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.post(
    "/enrich",
    response_model=EnrichedStock,
    summary="Enrich Stock Data",
    description="Enrich a single stock with technical indicators, fundamental data, "
                "and news information. This operation may take 10-30 seconds.",
)
async def enrich_stock(request: EnrichRequest) -> EnrichedStock:
    """
    Enrich a single stock with comprehensive data.

    Fetches and calculates:
    - Technical indicators (RSI, MACD, Bollinger Bands, etc.)
    - Fundamental data (P/E, P/B, ROE, market cap, etc.)
    - Recent news with sentiment analysis

    Note: This is a synchronous operation that may take 10-30 seconds
    depending on data sources and API availability.

    Args:
        request: EnrichRequest with ticker symbol

    Returns:
        EnrichedStock with all enriched data

    Raises:
        HTTPException: If ticker data cannot be fetched
    """
    service = get_analysis_service()

    try:
        result = service.enrich_stock(
            ticker=request.ticker,
            include_news=True
        )
        return result

    except ValueError as e:
        logger.warning(f"Enrichment failed for {request.ticker}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Enrichment error for {request.ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Enrichment failed: {str(e)}"
        )


@router.post(
    "/analyze",
    response_model=AnalysisResult,
    summary="Analyze Stock with AI",
    description="Analyze a single stock using Claude AI for valuation and risk assessment. "
                "Requires ANTHROPIC_API_KEY environment variable. May take 30+ seconds.",
)
async def analyze_stock(request: AnalysisRequest) -> AnalysisResult:
    """
    Analyze a single stock with AI-powered valuation.

    Uses Claude AI to analyze:
    - Valuation score (1-10, higher is more undervalued)
    - Risk score (1-10, higher is riskier)
    - Entry recommendation (BUY, WAIT, AVOID)
    - Key risks and catalysts

    Note: Requires ANTHROPIC_API_KEY environment variable.
    This operation may take 30+ seconds due to API calls.

    Args:
        request: AnalysisRequest with ticker and options

    Returns:
        AnalysisResult with AI analysis

    Raises:
        HTTPException: If API key missing or analysis fails
    """
    service = get_analysis_service()

    if not service.is_claude_available():
        raise HTTPException(
            status_code=503,
            detail="Claude API not available. Please set ANTHROPIC_API_KEY environment variable."
        )

    try:
        result = service.analyze_stock(
            ticker=request.ticker,
            include_news=request.include_news
        )

        if result is None:
            raise HTTPException(
                status_code=503,
                detail="Analysis service unavailable"
            )

        return result

    except ValueError as e:
        logger.warning(f"Analysis failed for {request.ticker}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error for {request.ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get(
    "/reports",
    response_model=ReportListResponse,
    summary="Get Analysis Reports",
    description="Get list of available analysis reports with summaries.",
)
async def get_reports() -> ReportListResponse:
    """
    Get list of available analysis reports.

    Returns all stored analysis reports with summary information
    including date, market, stock count, and recommendation counts.

    Returns:
        ReportListResponse with list of report summaries
    """
    service = get_analysis_service()

    try:
        reports = service.get_reports()
        return ReportListResponse(
            reports=reports,
            total_count=len(reports)
        )

    except Exception as e:
        logger.error(f"Failed to get reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reports: {str(e)}"
        )


@router.get(
    "/reports/{date}",
    response_model=ReportDetail,
    summary="Get Report Detail",
    description="Get detailed analysis report for a specific date.",
)
async def get_report(
    date: str,
    market: Optional[str] = Query(
        default=None,
        description="Filter by market (KOSPI, SP500, etc.)"
    ),
) -> ReportDetail:
    """
    Get a specific analysis report by date.

    Returns the full report content in Markdown format along with
    associated enriched stock data if available.

    Args:
        date: Report date in YYYYMMDD format (e.g., 20260211)
        market: Optional market filter (KOSPI, SP500)

    Returns:
        ReportDetail with content and stocks

    Raises:
        HTTPException: If report not found
    """
    service = get_analysis_service()

    try:
        report = service.get_report(date=date, market=market)

        if report is None:
            raise HTTPException(
                status_code=404,
                detail=f"Report not found for date: {date}"
            )

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report {date}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve report: {str(e)}"
        )


@router.get(
    "/enriched/{date}",
    response_model=EnrichedDataResponse,
    summary="Get Enriched Data",
    description="Get enriched JSON data for a specific date and market.",
)
async def get_enriched_data(
    date: str,
    market: str = Query(
        default="SP500",
        description="Market name (SP500, KOSPI, KOSDAQ)"
    ),
) -> EnrichedDataResponse:
    """
    Get enriched stock data for a specific date and market.

    Returns pre-computed enriched data including technical indicators,
    fundamental data, and news information for all analyzed stocks.

    Args:
        date: Data date in YYYYMMDD format (e.g., 20260211)
        market: Market name (SP500, KOSPI, KOSDAQ)

    Returns:
        EnrichedDataResponse with stock data

    Raises:
        HTTPException: If data not found
    """
    service = get_analysis_service()

    try:
        data = service.get_enriched_data(date=date, market=market)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Enriched data not found for date: {date}, market: {market}"
            )

        # Transform to response format
        stocks = []
        for stock_data in data.get("stocks", []):
            stocks.append(EnrichedStock(
                ticker=stock_data.get("ticker", ""),
                name=stock_data.get("name"),
                current_price=stock_data.get("current_price", 0),
                ma_240=stock_data.get("ma_240") or stock_data.get("ma_value"),
                distance_pct=stock_data.get("distance_pct"),
                technical=stock_data.get("technical", {}),
                fundamental=stock_data.get("fundamental", {}),
                news=stock_data.get("news"),
            ))

        return EnrichedDataResponse(
            date=date,
            market=data.get("market", market),
            stock_count=data.get("stock_count", len(stocks)),
            stocks=stocks,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get enriched data {date}/{market}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve enriched data: {str(e)}"
        )


@router.get(
    "/enriched",
    summary="List Enriched Data Files",
    description="List all available enriched data files.",
)
async def list_enriched_files() -> List[dict]:
    """
    List all available enriched data files.

    Returns information about all stored enriched data files
    including market and date information.

    Returns:
        List of dicts with market, date, and file info
    """
    service = get_analysis_service()

    try:
        return service.list_enriched_files()

    except Exception as e:
        logger.error(f"Failed to list enriched files: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list enriched files: {str(e)}"
        )


@router.get(
    "/ticker/{ticker}",
    response_model=TickerAnalysisResponse,
    summary="Get Ticker Analysis",
    description="Get combined OHLCV data, technical indicators, and fundamental data for a ticker.",
)
async def get_ticker_analysis(
    ticker: str,
    period: str = Query(
        default="6mo",
        description="Period for OHLCV data (1mo, 3mo, 6mo, 1y, 2y)"
    ),
) -> TickerAnalysisResponse:
    """
    Get combined analysis for a ticker including OHLCV, technical, and fundamental data.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, 005930.KS)
        period: Historical data period

    Returns:
        TickerAnalysisResponse with all data

    Raises:
        HTTPException: If ticker data unavailable
    """
    market_service = MarketService()

    # Map period string to days
    period_days_map = {
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
    }
    days = period_days_map.get(period, 180)

    # Get OHLCV data
    ohlcv_result = market_service.get_ohlcv(ticker, days=days)
    if ohlcv_result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Data not available for ticker: {ticker}"
        )

    # Get quote for current price and change
    quote = market_service.get_quote(ticker)
    current_price = quote["current_price"] if quote else 0.0
    change_pct = quote["change_pct"] if quote else 0.0
    name = (quote.get("name") if quote else None) or ticker

    # Convert OHLCV to response format
    ohlcv_data = [
        OHLCVDataPoint(
            time=item["date"],
            open=item["open"],
            high=item["high"],
            low=item["low"],
            close=item["close"],
            volume=item["volume"],
        )
        for item in ohlcv_result.get("data", [])
    ]

    # Get technical indicators
    technical = TickerTechnicalIndicators()
    tech_result = market_service.get_technical_indicators(ticker)
    if tech_result:
        rsi_val = tech_result.get("rsi")
        if rsi_val is not None:
            signal = "neutral"
            if rsi_val < 30:
                signal = "oversold"
            elif rsi_val > 70:
                signal = "overbought"
            technical.rsi = {"value": rsi_val, "signal": signal}

        macd_val = tech_result.get("macd")
        if macd_val is not None:
            hist = tech_result.get("macd_histogram", 0) or 0
            trend = "bullish" if hist > 0 else ("bearish" if hist < 0 else "neutral")
            technical.macd = {
                "macd": macd_val,
                "signal": tech_result.get("macd_signal"),
                "histogram": hist,
                "trend": trend,
            }

        bb_upper = tech_result.get("bb_upper")
        if bb_upper is not None:
            technical.bollingerBands = {
                "upper": bb_upper,
                "middle": tech_result.get("bb_middle"),
                "lower": tech_result.get("bb_lower"),
                "position": tech_result.get("bb_position", "within"),
            }

        ma_20 = tech_result.get("ma_20")
        if ma_20 is not None:
            technical.sma = {
                "sma20": ma_20,
                "sma50": tech_result.get("ma_60"),
                "sma200": tech_result.get("ma_240"),
            }

    # Get fundamental data
    fundamental = None
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if info:
            fundamental = TickerFundamental(
                market_cap=info.get("marketCap"),
                pe_ratio=info.get("trailingPE"),
                dividend_yield=info.get("dividendYield"),
                sector=info.get("sector"),
            )
    except Exception as e:
        logger.warning(f"Failed to get fundamental data for {ticker}: {e}")

    return TickerAnalysisResponse(
        ticker=ticker,
        name=name,
        current_price=current_price,
        change_pct=change_pct,
        ohlcv=ohlcv_data,
        technical=technical,
        fundamental=fundamental,
    )


@router.get(
    "/status",
    summary="Analysis Service Status",
    description="Get analysis service status including Claude API availability.",
)
async def get_status() -> dict:
    """
    Get analysis service status.

    Returns information about service availability including
    Claude API status and available enrichers.

    Returns:
        Dict with status information
    """
    service = get_analysis_service()

    return {
        "claude_available": service.is_claude_available(),
        "cache_available": service.cache is not None,
        "enrichers": {
            "technical": True,
            "fundamental": True,
            "news": True,
        },
        "data_dir": str(service.cache.cache_dir) if service.cache else None,
    }
