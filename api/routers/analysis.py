"""
Analysis router.

Provides endpoints for stock analysis and data enrichment operations.
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from api.schemas.analysis import (
    EnrichRequest,
    EnrichedStock,
    AnalysisRequest,
    AnalysisResult,
    OHLCVDataPoint,
    TickerTechnicalIndicators,
    TickerFundamental,
    TickerAnalysisResponse,
)
from api.services.analysis_service import get_analysis_service
from api.services.market_service import MarketService
from data_enrichment.fundamental import FundamentalEnricher
from data_enrichment.news import NewsEnricher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.post(
    "/enrich",
    response_model=EnrichedStock,
    summary="Enrich Stock Data",
    description="Enrich a single stock with technical indicators, fundamental data, "
                "and news information. This operation may take 10-30 seconds.",
)
def enrich_stock(request: EnrichRequest) -> EnrichedStock:
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
    description="Analyze a single stock using AI for valuation and risk assessment. "
                "Requires ANTHROPIC_API_KEY or OPENAI_API_KEY. May take 30+ seconds.",
)
def analyze_stock(request: AnalysisRequest) -> AnalysisResult:
    """
    Analyze a single stock with AI-powered valuation.

    Uses Claude AI to analyze:
    - Valuation score (1-10, higher is more undervalued)
    - Risk score (1-10, higher is riskier)
    - Entry recommendation (BUY, WAIT, AVOID)
    - Key risks and catalysts

    Note: Requires ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.
    This operation may take 30+ seconds due to API calls.

    Args:
        request: AnalysisRequest with ticker and options

    Returns:
        AnalysisResult with AI analysis

    Raises:
        HTTPException: If API key missing or analysis fails
    """
    service = get_analysis_service()

    if not service.is_ai_available():
        raise HTTPException(
            status_code=503,
            detail="AI API not available. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
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
    "/ticker/{ticker}",
    response_model=TickerAnalysisResponse,
    summary="Get Ticker Analysis",
    description="Get combined OHLCV data, technical indicators, and fundamental data for a ticker.",
)
def get_ticker_analysis(
    ticker: str,
    period: str = Query(
        default="6mo",
        description="Period for OHLCV data (1mo, 3mo, 6mo, 1y, 2y)"
    ),
    include_news: bool = Query(
        default=False,
        description="Include news articles (requires API key, adds latency)"
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

    # Reuse one OHLCV fetch for ohlcv/quote/technical to avoid redundant cache reads.
    shared_days = max(days, 300)
    shared_data = market_service.cache.get(ticker, days=shared_days)

    # Get OHLCV data
    ohlcv_result = market_service.get_ohlcv(ticker, days=days, data=shared_data)
    if ohlcv_result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Data not available for ticker: {ticker}"
        )

    # Get quote for current price and change
    quote = market_service.get_quote(ticker, data=shared_data, include_name=False)
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
    tech_result = market_service.get_technical_indicators(ticker, data=shared_data)
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
            prev_hist = tech_result.get("macd_prev_histogram")
            technical.macd = {
                "macd": macd_val,
                "signal": tech_result.get("macd_signal"),
                "histogram": hist,
                "prev_histogram": prev_hist,
                "trend": trend,
                "cross": tech_result.get("macd_cross", "none"),
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

        stoch_k = tech_result.get("stochastic_k")
        if stoch_k is not None:
            technical.stochastic = {
                "k": stoch_k,
                "d": tech_result.get("stochastic_d"),
            }

        obv_val = tech_result.get("obv")
        if obv_val is not None:
            technical.obv = {
                "value": obv_val,
                "trend": tech_result.get("obv_trend", "flat"),
            }

        # Volume analysis from OHLCV data
        if shared_data is not None and "volume" in shared_data.columns:
            vol_series = shared_data["volume"].dropna()
            if len(vol_series) >= 20:
                current_vol = float(vol_series.iloc[-1])
                avg_vol = float(vol_series.tail(20).mean())
                if avg_vol > 0:
                    technical.volume = {
                        "current": current_vol,
                        "average": round(avg_vol, 0),
                        "ratio": round(current_vol / avg_vol, 2),
                    }

    # Get fundamental data via FundamentalEnricher for richer fields
    fundamental = None
    try:
        enricher = FundamentalEnricher()
        fund_data = enricher.enrich(ticker)
        _core_fund_keys = ("pe_ratio", "market_cap", "eps", "revenue", "sector")
        has_meaningful_data = fund_data and any(
            fund_data.get(k) is not None for k in _core_fund_keys
        )
        if has_meaningful_data:
            enriched_name = fund_data.get("name")
            if enriched_name:
                name = enriched_name

            # For Korean tickers, prefer the native Korean name from pykrx
            if ticker.upper().endswith((".KS", ".KQ")):
                try:
                    from pykrx import stock as pykrx_stock

                    code = ticker.split(".")[0]
                    ko_name = pykrx_stock.get_market_ticker_name(code)
                    if ko_name:
                        name = ko_name
                except Exception:
                    pass  # fallback to enricher name

            # dividend_yield: frontend expects raw ratio (0.02 = 2%).
            # FundamentalEnricher usually returns percentage (2.0 = 2%),
            # but Korean fallback paths may return raw ratio. Normalize:
            #   > 1 → treat as percentage, divide by 100
            #   <= 1 → treat as raw ratio, keep as-is
            div_yield = fund_data.get("dividend_yield")
            if div_yield is not None and div_yield > 1:
                div_yield = div_yield / 100.0

            # Week52 data not in FundamentalEnricher; get from yfinance info
            week52_high = None
            week52_low = None
            try:
                info = market_service.get_ticker_info(ticker)
                if isinstance(info, dict):
                    week52_high = info.get("fiftyTwoWeekHigh")
                    week52_low = info.get("fiftyTwoWeekLow")
            except Exception:
                pass

            fundamental = TickerFundamental(
                market_cap=fund_data.get("market_cap"),
                pe_ratio=fund_data.get("pe_ratio"),
                forward_pe=fund_data.get("forward_pe"),
                pb_ratio=fund_data.get("pb_ratio"),
                ps_ratio=fund_data.get("ps_ratio"),
                peg_ratio=fund_data.get("peg_ratio"),
                dividend_yield=div_yield,
                eps=fund_data.get("eps"),
                revenue=fund_data.get("revenue"),
                revenue_growth=fund_data.get("revenue_growth"),
                profit_margin=fund_data.get("profit_margin"),
                roe=fund_data.get("roe"),
                roa=fund_data.get("roa"),
                debt_to_equity=fund_data.get("debt_to_equity"),
                current_ratio=fund_data.get("current_ratio"),
                enterprise_value=fund_data.get("enterprise_value"),
                sector=fund_data.get("sector"),
                industry=fund_data.get("industry"),
                description=fund_data.get("description"),
                week52_high=week52_high,
                week52_low=week52_low,
            )
        else:
            # Fallback to basic info from market_service
            info = market_service.get_ticker_info(ticker)
            if isinstance(info, dict) and info:
                name = info.get("shortName") or info.get("longName") or name
                fundamental = TickerFundamental(
                    market_cap=info.get("marketCap"),
                    pe_ratio=info.get("trailingPE"),
                    dividend_yield=info.get("dividendYield"),
                    eps=info.get("trailingEps"),
                    sector=info.get("sector"),
                    week52_high=info.get("fiftyTwoWeekHigh"),
                    week52_low=info.get("fiftyTwoWeekLow"),
                )
    except Exception as e:
        logger.warning(f"Failed to get fundamental data for {ticker}: {e}")

    # Get news (opt-in via query parameter)
    news_data = None
    if include_news:
        try:
            news_enricher = NewsEnricher()
            news_result = news_enricher.enrich(ticker, name=name)
            if news_result and news_result.get("articles"):
                news_data = {
                    "articles": news_result["articles"],
                    "sentiment_summary": news_result.get("sentiment_summary", "neutral"),
                }
        except Exception as e:
            logger.warning(f"Failed to get news for {ticker}: {e}")

    return TickerAnalysisResponse(
        ticker=ticker,
        name=name,
        current_price=current_price,
        change_pct=change_pct,
        timestamp=quote.get("timestamp") if quote else None,
        ohlcv=ohlcv_data,
        technical=technical,
        fundamental=fundamental,
        news=news_data,
    )


@router.get(
    "/status",
    summary="Analysis Service Status",
    description="Get analysis service status including Claude API availability.",
)
def get_status() -> dict:
    """
    Get analysis service status.

    Returns information about service availability including
    Claude API status and available enrichers.

    Returns:
        Dict with status information
    """
    service = get_analysis_service()

    return {
        "ai_available": service.is_ai_available(),
        "provider": service.provider,
        "claude_available": service.is_claude_available(),
        "cache_available": service.cache is not None,
        "enrichers": {
            "technical": True,
            "fundamental": True,
            "news": True,
        },
        "data_dir": str(service.cache.cache_dir) if service.cache else None,
    }
