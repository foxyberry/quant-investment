"""
Analysis API schemas.

Pydantic models for stock analysis request/response validation.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class EnrichRequest(BaseModel):
    """
    Request for enriching a single stock with data.

    Attributes:
        ticker: Stock ticker symbol
    """

    ticker: str = Field(
        ...,
        description="Stock ticker symbol (e.g., AAPL, 005930.KS)",
        examples=["AAPL", "005930.KS"]
    )


class EnrichedStock(BaseModel):
    """
    Enriched stock data with technical, fundamental, and news information.

    Attributes:
        ticker: Stock ticker symbol
        name: Company name
        current_price: Current stock price
        ma_240: 240-day moving average
        distance_pct: Distance from 240-day MA as percentage
        technical: Technical indicators
        fundamental: Fundamental data
        news: News information
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    name: Optional[str] = Field(None, description="Company name")
    current_price: float = Field(..., description="Current stock price")
    ma_240: Optional[float] = Field(None, description="240-day moving average")
    distance_pct: Optional[float] = Field(
        None,
        description="Distance from 240-day MA as percentage"
    )
    technical: Dict[str, Any] = Field(
        default_factory=dict,
        description="Technical indicators (RSI, MACD, BB, etc.)"
    )
    fundamental: Dict[str, Any] = Field(
        default_factory=dict,
        description="Fundamental data (P/E, P/B, ROE, etc.)"
    )
    news: Optional[Dict[str, Any]] = Field(
        default=None,
        description="News information with articles and sentiment"
    )


class AnalysisRequest(BaseModel):
    """
    Request for analyzing a single stock.

    Attributes:
        ticker: Stock ticker symbol
        include_news: Whether to include news in analysis
    """

    ticker: str = Field(
        ...,
        description="Stock ticker symbol",
        examples=["AAPL", "005930.KS"]
    )
    include_news: bool = Field(
        default=True,
        description="Whether to include news in analysis"
    )


class AnalysisResult(BaseModel):
    """
    Complete analysis result for a stock.

    Attributes:
        ticker: Stock ticker symbol
        name: Company name
        current_price: Current stock price
        valuation_score: Valuation score (1-10)
        risk_score: Risk score (1-10)
        entry_recommendation: Entry recommendation (BUY, WAIT, AVOID)
        reasoning: Analysis reasoning
        key_risks: List of key risks
        catalysts: List of potential catalysts
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    current_price: float = Field(..., description="Current stock price")
    valuation_score: float = Field(
        ...,
        description="Valuation score (1-10, higher is more undervalued)",
        ge=1,
        le=10
    )
    risk_score: float = Field(
        ...,
        description="Risk score (1-10, higher is riskier)",
        ge=1,
        le=10
    )
    entry_recommendation: str = Field(
        ...,
        description="Entry recommendation",
        examples=["BUY", "WAIT", "AVOID"]
    )
    reasoning: str = Field(..., description="Analysis reasoning")
    key_risks: List[str] = Field(
        default_factory=list,
        description="List of key risks"
    )
    catalysts: List[str] = Field(
        default_factory=list,
        description="List of potential catalysts"
    )


class ReportSummary(BaseModel):
    """
    Summary of an analysis report.

    Attributes:
        date: Report date (YYYYMMDD format)
        market: Market name (SP500, KOSPI, etc.)
        total_stocks: Total number of stocks analyzed
        buy_count: Number of BUY recommendations
        wait_count: Number of WAIT recommendations
        avoid_count: Number of AVOID recommendations
    """

    date: str = Field(..., description="Report date (YYYYMMDD)")
    market: str = Field(..., description="Market name")
    total_stocks: int = Field(..., description="Total stocks analyzed")
    buy_count: int = Field(default=0, description="Number of BUY recommendations")
    wait_count: int = Field(default=0, description="Number of WAIT recommendations")
    avoid_count: int = Field(default=0, description="Number of AVOID recommendations")


class ReportDetail(BaseModel):
    """
    Detailed analysis report.

    Attributes:
        date: Report date (YYYYMMDD format)
        market: Market name
        content: Full report content in Markdown
        stocks: List of analyzed stocks
    """

    date: str = Field(..., description="Report date (YYYYMMDD)")
    market: str = Field(..., description="Market name")
    content: str = Field(..., description="Report content in Markdown format")
    stocks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of analyzed stocks with their data"
    )


class ReportListResponse(BaseModel):
    """
    Response containing list of available reports.

    Attributes:
        reports: List of report summaries
        total_count: Total number of reports
    """

    reports: List[ReportSummary] = Field(
        default_factory=list,
        description="List of available reports"
    )
    total_count: int = Field(..., description="Total number of reports")


class EnrichedDataResponse(BaseModel):
    """
    Response containing enriched stock data for a specific date and market.

    Attributes:
        date: Data date (YYYYMMDD format)
        market: Market name
        stock_count: Number of stocks
        stocks: List of enriched stock data
    """

    date: str = Field(..., description="Data date (YYYYMMDD)")
    market: str = Field(..., description="Market name")
    stock_count: int = Field(..., description="Number of stocks")
    stocks: List[EnrichedStock] = Field(
        default_factory=list,
        description="List of enriched stock data"
    )


class OHLCVDataPoint(BaseModel):
    """Single OHLCV data point for ticker analysis."""

    time: str = Field(..., description="Date string (YYYY-MM-DD)")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: Optional[int] = Field(None, description="Trading volume")


class TickerTechnicalIndicators(BaseModel):
    """Technical indicators for ticker analysis."""

    rsi: Optional[Dict[str, Any]] = Field(None, description="RSI with value and signal")
    macd: Optional[Dict[str, Any]] = Field(None, description="MACD with macd, signal, histogram, trend")
    bollingerBands: Optional[Dict[str, Any]] = Field(None, description="Bollinger Bands")
    sma: Optional[Dict[str, Any]] = Field(None, description="Simple Moving Averages")
    volume: Optional[Dict[str, Any]] = Field(None, description="Volume analysis")


class TickerFundamental(BaseModel):
    """Fundamental data for ticker analysis."""

    market_cap: Optional[float] = Field(None, description="Market capitalization")
    pe_ratio: Optional[float] = Field(None, description="Price-to-earnings ratio")
    dividend_yield: Optional[float] = Field(None, description="Dividend yield")
    sector: Optional[str] = Field(None, description="Industry sector")


class TickerAnalysisResponse(BaseModel):
    """
    Combined ticker analysis response with OHLCV, technical, and fundamental data.

    Attributes:
        ticker: Stock ticker symbol
        name: Company name
        current_price: Current stock price
        change_pct: Price change percentage
        ohlcv: Historical OHLCV data
        technical: Technical indicators
        fundamental: Fundamental data
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    current_price: float = Field(..., description="Current stock price")
    change_pct: float = Field(0.0, description="Price change percentage")
    ohlcv: List[OHLCVDataPoint] = Field(default_factory=list, description="OHLCV data")
    technical: TickerTechnicalIndicators = Field(
        default_factory=TickerTechnicalIndicators,
        description="Technical indicators"
    )
    fundamental: Optional[TickerFundamental] = Field(None, description="Fundamental data")


class SearchResult(BaseModel):
    """Single search result."""

    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
