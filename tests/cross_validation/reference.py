"""
Reference indicator calculations using the `ta` library.

The `ta` library uses industry-standard formulas matching TradingView:
  - RSI: Wilder's EWM smoothing (alpha=1/period)
  - MACD: EWM with span (same as our implementation)
  - Bollinger Bands: SMA +/- N*std (same as our implementation)

Our `discovery/indicators.py` differs in RSI calculation:
  - Ours: SMA smoothing (.rolling().mean())
  - ta/TradingView: Wilder's EWM (.ewm(alpha=1/period).mean())
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD as TAMACD
from ta.volatility import BollingerBands


@dataclass
class ReferenceIndicators:
    """Reference indicator values from the `ta` library (TradingView-compatible)."""

    # RSI
    rsi_ema: Optional[float]  # Wilder's EWM — matches TradingView
    rsi_sma: Optional[float]  # SMA — matches our implementation

    # MACD
    macd_line: Optional[float]
    macd_signal: Optional[float]
    macd_histogram: Optional[float]

    # Bollinger Bands
    bb_upper: Optional[float]
    bb_middle: Optional[float]
    bb_lower: Optional[float]
    bb_width: Optional[float]  # (upper - lower) / middle * 100


def _safe_float(val) -> Optional[float]:
    """Convert to float, returning None for NaN/None."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        f = float(val)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def calculate_reference(close: pd.Series) -> Optional[ReferenceIndicators]:
    """Calculate reference indicators using the `ta` library.

    Args:
        close: Close price series with DatetimeIndex, at least 60 rows.

    Returns:
        ReferenceIndicators or None if data is insufficient.
    """
    if len(close) < 60:
        return None

    # --- RSI (EWM — TradingView method) ---
    rsi_ind = RSIIndicator(close=close, window=14, fillna=False)
    rsi_ema = _safe_float(rsi_ind.rsi().iloc[-1])

    # --- RSI (SMA — our method) ---
    rsi_sma = _rsi_sma(close, 14)

    # --- MACD ---
    macd_ind = TAMACD(close=close, window_fast=12, window_slow=26, window_sign=9, fillna=False)
    macd_line = _safe_float(macd_ind.macd().iloc[-1])
    macd_signal = _safe_float(macd_ind.macd_signal().iloc[-1])
    macd_hist = _safe_float(macd_ind.macd_diff().iloc[-1])

    # --- Bollinger Bands ---
    bb_ind = BollingerBands(close=close, window=20, window_dev=2, fillna=False)
    bb_upper = _safe_float(bb_ind.bollinger_hband().iloc[-1])
    bb_middle = _safe_float(bb_ind.bollinger_mavg().iloc[-1])
    bb_lower = _safe_float(bb_ind.bollinger_lband().iloc[-1])
    bb_width = None
    if bb_upper is not None and bb_lower is not None and bb_middle is not None:
        if bb_middle == 0:
            bb_width = 0.0
        else:
            bb_width = (bb_upper - bb_lower) / bb_middle * 100

    return ReferenceIndicators(
        rsi_ema=rsi_ema,
        rsi_sma=rsi_sma,
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_histogram=macd_hist,
        bb_upper=bb_upper,
        bb_middle=bb_middle,
        bb_lower=bb_lower,
        bb_width=bb_width,
    )


def _rsi_sma(close: pd.Series, period: int = 14) -> Optional[float]:
    """RSI using SMA smoothing (our method)."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return _safe_float(rsi.iloc[-1])
