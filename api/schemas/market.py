"""
Market data schemas for API responses.

Provides schemas for OHLCV data, quotes, and technical indicators.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

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


class MacroFxSnapshot(BaseModel):
    pair: str = Field(..., description="FX pair, e.g. USD/KRW")
    value: Optional[float] = Field(None, description="Latest FX value")
    change_pct: Optional[float] = Field(None, description="Short-term FX change percent")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class MacroFuturesSnapshot(BaseModel):
    symbol: str = Field(..., description="Futures symbol (or proxy ticker)")
    value: Optional[float] = Field(None, description="Latest futures/proxy value")
    basis: Optional[float] = Field(None, description="Futures basis versus spot proxy")
    change_pct: Optional[float] = Field(None, description="Short-term futures change percent")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class MacroInvestorFlowSnapshot(BaseModel):
    market: str = Field(..., description="Market name")
    foreign_net: Optional[float] = Field(None, description="Foreign net flow")
    institution_net: Optional[float] = Field(None, description="Institution net flow")
    individual_net: Optional[float] = Field(None, description="Individual net flow")
    window_min: Optional[int] = Field(None, description="Aggregation window in minutes")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    alignment: Optional[str] = Field(None, description="Foreign vs institution alignment (aligned_buy/aligned_sell/foreign_lead/institution_lead/unknown)")
    foreign_strength: Optional[str] = Field(None, description="Foreign flow strength (strong/moderate/weak)")
    kosdaq_foreign_net: Optional[float] = Field(None, description="KOSDAQ foreign net flow")
    kosdaq_institution_net: Optional[float] = Field(None, description="KOSDAQ institution net flow")
    kosdaq_individual_net: Optional[float] = Field(None, description="KOSDAQ individual net flow")


class MacroSignalComponent(BaseModel):
    raw: float = Field(..., description="Raw component score [-1, 1]")
    decay: float = Field(..., description="Freshness decay factor [0, 1]")
    weight: float = Field(..., description="Component weight in scoring")
    contribution: float = Field(..., description="Effective contribution (raw * decay * weight)")
    half_life_sec: Optional[int] = Field(None, description="Half-life used for decay calculation (seconds)")


class MacroReasonDetail(BaseModel):
    version: int = Field(1, description="Schema version for forward compatibility")
    summary: str = Field(..., description="Human-readable summary string")
    components: Dict[str, MacroSignalComponent] = Field(
        ..., description="Per-component scoring breakdown (fx, futures, flow)"
    )


class MacroSignal(BaseModel):
    macro_score: Optional[float] = Field(None, description="Composite macro score")
    regime: str = Field(..., description="Regime classification")
    reason: Optional[str] = Field(None, description="Human-readable scoring reason (backward compat)")
    reason_detail: Optional[MacroReasonDetail] = Field(None, description="Structured scoring breakdown")
    updated_at: Optional[str] = Field(None, description="Signal timestamp")


class MacroFreshness(BaseModel):
    fx_age_sec: Optional[int] = Field(None, description="FX data age in seconds")
    futures_age_sec: Optional[int] = Field(None, description="Futures data age in seconds")
    flow_age_sec: Optional[int] = Field(None, description="Flow data age in seconds")


class MacroInterpretation(BaseModel):
    entry_signal: Literal["buy_favorable", "wait", "caution"] = Field(..., description="Entry signal")
    fx_interpretation: str = Field(..., description="FX direction interpretation")
    futures_interpretation: str = Field(..., description="Futures basis interpretation")
    flow_interpretation: str = Field(..., description="Investor flow interpretation")


class MacroBondSnapshot(BaseModel):
    us_10y: Optional[float] = Field(None, description="US 10-Year Treasury Yield (%)")
    us_2y: Optional[float] = Field(None, description="US 2-Year Treasury Yield (%)")
    us_spread_2_10: Optional[float] = Field(None, description="US 10Y-2Y Spread (pp)")
    inverted: Optional[bool] = Field(None, description="Whether the yield curve is inverted")
    kr_10y: Optional[float] = Field(None, description="KR 10-Year Government Bond Yield (%)")
    kr_3y: Optional[float] = Field(None, description="KR 3-Year Government Bond Yield (%)")
    kr_us_spread_10y: Optional[float] = Field(None, description="KR-US 10Y Spread (pp)")
    source_updated_at: Optional[str] = Field(
        None, description="When the source data was last updated"
    )
    stale: Optional[bool] = Field(
        None, description="Whether the data is stale (e.g., weekend)"
    )


class MacroVolatilitySnapshot(BaseModel):
    vix: Optional[float] = Field(None, description="CBOE VIX index value")
    vix_change_pct: Optional[float] = Field(None, description="VIX daily change %")
    vix_as_of: Optional[str] = Field(None, description="VIX data timestamp")
    vkospi: Optional[float] = Field(None, description="VKOSPI index value")
    vkospi_change_pct: Optional[float] = Field(None, description="VKOSPI daily change %")
    vkospi_as_of: Optional[str] = Field(None, description="VKOSPI data timestamp")
    fear_greed: Optional[str] = Field(None, description="Fear/greed classification based on VIX")
    vkospi_vix_ratio: Optional[float] = Field(None, description="VKOSPI/VIX ratio (auxiliary)")


class MacroBundleResponse(BaseModel):
    fx: MacroFxSnapshot
    futures: MacroFuturesSnapshot
    flow: MacroInvestorFlowSnapshot
    signal: MacroSignal
    freshness: MacroFreshness
    interpretation: Optional[MacroInterpretation] = None
    cache_hit: Optional[bool] = Field(None, description="Whether this response was served from cache")
    generated_at: Optional[str] = Field(None, description="When this bundle was originally generated")
    is_market_hours: Optional[bool] = Field(None, description="Whether KRX is currently in market hours")
    bonds: Optional[MacroBondSnapshot] = Field(None, description="Bond rate snapshot (yields, spreads)")
    volatility: Optional[MacroVolatilitySnapshot] = Field(
        None, description="Volatility snapshot (VIX, VKOSPI)"
    )


class MacroHistoryPoint(BaseModel):
    timestamp: str = Field(..., description="Point timestamp")
    fx_value: Optional[float] = Field(None, description="FX value")
    futures_value: Optional[float] = Field(None, description="Futures/proxy value")
    foreign_net: Optional[float] = Field(None, description="Foreign net flow")
    macro_score: Optional[float] = Field(None, description="Macro score")
    regime: str = Field(..., description="Regime at timestamp")


class MacroHistoryResponse(BaseModel):
    window: str = Field(..., description="Requested window string")
    points: List[MacroHistoryPoint] = Field(default_factory=list, description="History points")
