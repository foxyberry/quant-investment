"""
Market data schemas for API responses.

Provides schemas for OHLCV data, quotes, and technical indicators.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OHLCVItem(BaseModel):
    """
    Single OHLCV (Open-High-Low-Close-Volume) data point.

    Attributes:
        date: Trading date in ISO 8601 format
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        volume: Trading volume
    """

    date: str = Field(..., description="Trading date (ISO 8601)")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")


class OHLCVResponse(BaseModel):
    """
    OHLCV data response.

    Attributes:
        ticker: Stock ticker symbol
        data: List of OHLCV data points
        period_days: Number of days in the response
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    data: List[OHLCVItem] = Field(..., description="OHLCV data points")
    period_days: int = Field(..., description="Number of days in response")


class QuoteResponse(BaseModel):
    """
    Current quote response.

    Attributes:
        ticker: Stock ticker symbol
        name: Company name (if available)
        current_price: Current/latest price
        change: Price change from previous close
        change_pct: Price change percentage
        volume: Trading volume
        timestamp: Quote timestamp (ISO 8601)
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    name: Optional[str] = Field(None, description="Company name")
    current_price: float = Field(..., description="Current/latest price")
    change: float = Field(..., description="Price change from previous close")
    change_pct: float = Field(..., description="Price change percentage")
    volume: int = Field(..., description="Trading volume")
    timestamp: str = Field(..., description="Quote timestamp (ISO 8601)")


class TechnicalIndicators(BaseModel):
    """
    Technical indicators response.

    Attributes:
        ticker: Stock ticker symbol
        rsi: Relative Strength Index (0-100)
        rsi_signal: RSI signal interpretation (oversold/neutral/overbought)
        macd: MACD line value
        macd_signal: MACD signal line value
        macd_histogram: MACD histogram value
        bb_upper: Bollinger Bands upper band
        bb_middle: Bollinger Bands middle band (SMA)
        bb_lower: Bollinger Bands lower band
        bb_position: Price position relative to BB (above/middle/below)
        ma_20: 20-day moving average
        ma_60: 60-day moving average
        ma_120: 120-day moving average
        ma_240: 240-day moving average
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    rsi: Optional[float] = Field(None, description="RSI value (0-100)")
    rsi_signal: Optional[str] = Field(
        None, description="RSI signal (oversold/neutral/overbought)"
    )
    macd: Optional[float] = Field(None, description="MACD line value")
    macd_signal: Optional[float] = Field(None, description="MACD signal line value")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram value")
    bb_upper: Optional[float] = Field(None, description="Bollinger Bands upper band")
    bb_middle: Optional[float] = Field(None, description="Bollinger Bands middle band")
    bb_lower: Optional[float] = Field(None, description="Bollinger Bands lower band")
    bb_position: Optional[str] = Field(
        None, description="Price position (above/middle/below)"
    )
    ma_20: Optional[float] = Field(None, description="20-day moving average")
    ma_60: Optional[float] = Field(None, description="60-day moving average")
    ma_120: Optional[float] = Field(None, description="120-day moving average")
    ma_240: Optional[float] = Field(None, description="240-day moving average")
