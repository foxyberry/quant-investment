"""
Technical Indicators Enrichment Module

Canonical location. Moved from data_enrichment/technical.py.

This module provides technical analysis enrichment for OHLCV data,
calculating various indicators and their signal interpretations.

Usage:
    from data_sources.technical.technical import TechnicalEnricher

    enricher = TechnicalEnricher()
    result = enricher.enrich("AAPL", ohlcv_data)
    print(f"RSI: {result['rsi']} ({result['rsi_signal']})")
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import numpy as np


class RSISignal(str, Enum):
    """RSI signal interpretation"""
    OVERSOLD = "oversold"
    NEUTRAL = "neutral"
    OVERBOUGHT = "overbought"


class MACDCross(str, Enum):
    """MACD crossover signal"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NONE = "none"


class BBPosition(str, Enum):
    """Bollinger Bands position"""
    ABOVE = "above"
    MIDDLE = "middle"
    BELOW = "below"


class OBVTrend(str, Enum):
    """OBV trend direction"""
    RISING = "rising"
    FALLING = "falling"
    FLAT = "flat"


@dataclass
class TechnicalEnricherConfig:
    """Configuration for technical indicator calculations"""
    # RSI
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0

    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # Bollinger Bands
    bb_period: int = 20
    bb_std_dev: float = 2.0

    # Stochastic
    stoch_k_period: int = 14
    stoch_d_period: int = 3

    # OBV trend detection
    obv_trend_period: int = 10
    obv_trend_threshold: float = 0.02  # 2% change threshold


class TechnicalEnricher:
    """
    Technical Indicators Enricher

    Calculates technical indicators from OHLCV data and provides
    structured output with signal interpretations.
    """

    def __init__(self, config: Optional[TechnicalEnricherConfig] = None):
        """
        Initialize the enricher with optional configuration.

        Args:
            config: Configuration for indicator calculations.
                   Uses defaults if not provided.
        """
        self.config = config or TechnicalEnricherConfig()

    def enrich(self, ticker: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Enrich OHLCV data with technical indicators.

        Args:
            ticker: Stock ticker symbol (for reference/logging)
            data: DataFrame with columns: open, high, low, close, volume
                  Index should be datetime

        Returns:
            Dictionary containing:
                - rsi: float - RSI value (0-100)
                - rsi_signal: str - 'oversold', 'neutral', 'overbought'
                - macd: float - MACD line value
                - macd_signal: float - Signal line value
                - macd_histogram: float - MACD histogram value
                - macd_cross: str - 'bullish', 'bearish', 'none'
                - bb_upper: float - Upper Bollinger Band
                - bb_middle: float - Middle Bollinger Band (SMA)
                - bb_lower: float - Lower Bollinger Band
                - bb_position: str - 'above', 'middle', 'below'
                - obv: float - On-Balance Volume
                - obv_trend: str - 'rising', 'falling', 'flat'
                - stochastic_k: float - Stochastic %K (0-100)
                - stochastic_d: float - Stochastic %D (0-100)

        Raises:
            ValueError: If required columns are missing from data
        """
        self._validate_data(data)

        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume = data["volume"]

        # Calculate all indicators
        rsi = self._calculate_rsi(close)
        macd_line, signal_line, histogram = self._calculate_macd(close)
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(close)
        obv = self._calculate_obv(close, volume)
        stoch_k, stoch_d = self._calculate_stochastic(high, low, close)

        # Get latest values
        rsi_value = self._safe_last(rsi)
        macd_value = self._safe_last(macd_line)
        signal_value = self._safe_last(signal_line)
        histogram_value = self._safe_last(histogram)
        prev_histogram_value = (
            float(histogram.iloc[-2])
            if histogram is not None and len(histogram) >= 2 and not pd.isna(histogram.iloc[-2])
            else None
        )
        bb_upper_value = self._safe_last(bb_upper)
        bb_middle_value = self._safe_last(bb_middle)
        bb_lower_value = self._safe_last(bb_lower)
        obv_value = self._safe_last(obv)
        stoch_k_value = self._safe_last(stoch_k)
        stoch_d_value = self._safe_last(stoch_d)
        current_price = self._safe_last(close)

        # Determine signals
        rsi_signal = self._interpret_rsi(rsi_value)
        macd_cross = self._detect_macd_cross(macd_line, signal_line)
        bb_position = self._interpret_bb_position(
            current_price, bb_upper_value, bb_middle_value, bb_lower_value
        )
        obv_trend = self._interpret_obv_trend(obv)

        return {
            "ticker": ticker,
            "rsi": rsi_value,
            "rsi_signal": rsi_signal,
            "macd": macd_value,
            "macd_signal": signal_value,
            "macd_histogram": histogram_value,
            "macd_prev_histogram": prev_histogram_value,
            "macd_cross": macd_cross,
            "bb_upper": bb_upper_value,
            "bb_middle": bb_middle_value,
            "bb_lower": bb_lower_value,
            "bb_position": bb_position,
            "obv": obv_value,
            "obv_trend": obv_trend,
            "stochastic_k": stoch_k_value,
            "stochastic_d": stoch_d_value,
        }

    def _validate_data(self, data: pd.DataFrame) -> None:
        """Validate that required columns exist in the DataFrame."""
        required_columns = {"open", "high", "low", "close", "volume"}
        # Handle case-insensitive column names
        data_columns = {col.lower() for col in data.columns}

        missing = required_columns - data_columns
        if missing:
            raise ValueError(
                f"Missing required columns: {missing}. "
                f"Expected: {required_columns}"
            )

    def _safe_last(self, series: pd.Series) -> Optional[float]:
        """Safely extract the last value from a series."""
        if series is None or series.empty:
            return None
        val = series.iloc[-1]
        if pd.isna(val):
            return None
        return float(val)

    # =========================================================================
    # Indicator Calculations
    # =========================================================================

    def _calculate_rsi(self, close: pd.Series) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        period = self.config.rsi_period
        delta = close.diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta.where(delta < 0, 0))

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(
        self, close: pd.Series
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        fast = self.config.macd_fast
        slow = self.config.macd_slow
        signal_period = self.config.macd_signal

        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def _calculate_bollinger_bands(
        self, close: pd.Series
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands.

        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        period = self.config.bb_period
        std_dev = self.config.bb_std_dev

        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return upper, middle, lower

    def _calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Calculate On-Balance Volume (OBV).

        OBV adds volume on up days and subtracts on down days.
        """
        # Use vectorized approach for performance
        direction = np.sign(close.diff())
        direction.iloc[0] = 0  # First value has no direction

        obv = (direction * volume).cumsum()

        return obv

    def _calculate_stochastic(
        self, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Stochastic Oscillator.

        %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        %D = SMA of %K

        Returns:
            Tuple of (stoch_k, stoch_d)
        """
        k_period = self.config.stoch_k_period
        d_period = self.config.stoch_d_period

        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        # Avoid division by zero
        range_hl = highest_high - lowest_low
        range_hl = range_hl.replace(0, np.nan)

        stoch_k = 100 * (close - lowest_low) / range_hl
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return stoch_k, stoch_d

    # =========================================================================
    # Signal Interpretation
    # =========================================================================

    def _interpret_rsi(self, rsi_value: Optional[float]) -> str:
        """Interpret RSI value as a signal."""
        if rsi_value is None:
            return RSISignal.NEUTRAL.value

        if rsi_value <= self.config.rsi_oversold:
            return RSISignal.OVERSOLD.value
        elif rsi_value >= self.config.rsi_overbought:
            return RSISignal.OVERBOUGHT.value
        else:
            return RSISignal.NEUTRAL.value

    def _detect_macd_cross(
        self, macd_line: pd.Series, signal_line: pd.Series
    ) -> str:
        """
        Detect MACD crossover signal.

        Bullish: MACD crosses above signal line
        Bearish: MACD crosses below signal line
        """
        if len(macd_line) < 2 or len(signal_line) < 2:
            return MACDCross.NONE.value

        macd_current = macd_line.iloc[-1]
        macd_prev = macd_line.iloc[-2]
        signal_current = signal_line.iloc[-1]
        signal_prev = signal_line.iloc[-2]

        if pd.isna(macd_current) or pd.isna(signal_current):
            return MACDCross.NONE.value
        if pd.isna(macd_prev) or pd.isna(signal_prev):
            return MACDCross.NONE.value

        # Bullish crossover: MACD was below signal, now above
        if macd_prev <= signal_prev and macd_current > signal_current:
            return MACDCross.BULLISH.value

        # Bearish crossover: MACD was above signal, now below
        if macd_prev >= signal_prev and macd_current < signal_current:
            return MACDCross.BEARISH.value

        return MACDCross.NONE.value

    def _interpret_bb_position(
        self,
        price: Optional[float],
        upper: Optional[float],
        middle: Optional[float],
        lower: Optional[float],
    ) -> str:
        """Interpret current price position relative to Bollinger Bands."""
        if price is None or upper is None or lower is None:
            return BBPosition.MIDDLE.value

        if price >= upper:
            return BBPosition.ABOVE.value
        elif price <= lower:
            return BBPosition.BELOW.value
        else:
            return BBPosition.MIDDLE.value

    def _interpret_obv_trend(self, obv: pd.Series) -> str:
        """
        Interpret OBV trend direction.

        Compares recent OBV change to threshold.
        """
        period = self.config.obv_trend_period
        threshold = self.config.obv_trend_threshold

        if len(obv) < period:
            return OBVTrend.FLAT.value

        recent_obv = obv.tail(period)
        if recent_obv.empty or recent_obv.iloc[0] == 0:
            return OBVTrend.FLAT.value

        # Calculate percentage change over the period
        start_val = recent_obv.iloc[0]
        end_val = recent_obv.iloc[-1]

        if pd.isna(start_val) or pd.isna(end_val) or start_val == 0:
            return OBVTrend.FLAT.value

        pct_change = (end_val - start_val) / abs(start_val)

        if pct_change > threshold:
            return OBVTrend.RISING.value
        elif pct_change < -threshold:
            return OBVTrend.FALLING.value
        else:
            return OBVTrend.FLAT.value


# Convenience function for quick enrichment
def enrich_technical(ticker: str, data: pd.DataFrame) -> Dict[str, Any]:
    """
    Convenience function to enrich OHLCV data with technical indicators.

    Args:
        ticker: Stock ticker symbol
        data: OHLCV DataFrame

    Returns:
        Dictionary with all technical indicators and signals
    """
    enricher = TechnicalEnricher()
    return enricher.enrich(ticker, data)
