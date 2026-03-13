"""
Cross-Validation Service.

Compares our indicator calculations (discovery/indicators.py) against
TradingView-compatible reference values (ta library).

Known divergences:
  - RSI: Ours uses SMA smoothing; TradingView uses Wilder's EWM (~5pt diff)
  - BB: Ours uses ddof=1 (sample std); ta uses ddof=0 (population std) (~2.6% width diff)
  - MACD: Perfect match (both use EWM)
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

from api.schemas.cross_validation import (
    CrossValidationResponse,
    IndicatorComparison,
)

logger = logging.getLogger(__name__)

# Tolerances for each indicator
_RSI_ABS_TOL = 6.0  # RSI SMA vs EWM can differ ~5pt
_MACD_ABS_TOL = 0.01  # MACD should be near-perfect
_BB_PCT_TOL = 3.0  # BB width ~2.6% diff due to ddof

KNOWN_DIVERGENCES = [
    "RSI: Our method uses SMA smoothing; TradingView uses Wilder's EWM (alpha=1/period). "
    "Expect up to ~5pt divergence, especially on Korean stocks with volatile returns.",
    "Bollinger Bands: Our std uses ddof=1 (sample std); ta library uses ddof=0 (population std). "
    "Expect ~2.6% band width divergence.",
    "MACD: Both use EWM with span. Should match exactly.",
]


def _safe_float(val) -> Optional[float]:
    """Convert to float, returning None for NaN/None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _compare(
    name: str,
    our: Optional[float],
    ref: Optional[float],
    abs_tol: float = 0.01,
    pct_tol: Optional[float] = None,
    note: Optional[str] = None,
) -> IndicatorComparison:
    """Build a comparison record."""
    if our is None or ref is None:
        return IndicatorComparison(
            name=name,
            our_value=our,
            reference_value=ref,
            difference=None,
            pct_difference=None,
            match=our is None and ref is None,
            note=note or "One or both values unavailable",
        )

    diff = our - ref
    if ref == 0:
        pct_diff = None
        is_match = abs(diff) <= abs_tol
    else:
        pct_diff = round(abs(diff / ref) * 100, 4)
        if pct_tol is not None:
            is_match = pct_diff <= pct_tol
        else:
            is_match = abs(diff) <= abs_tol

    return IndicatorComparison(
        name=name,
        our_value=round(our, 6),
        reference_value=round(ref, 6),
        difference=round(diff, 6),
        pct_difference=pct_diff,
        match=is_match,
        note=note,
    )


def _calculate_our_rsi(close: pd.Series, period: int = 14) -> Optional[float]:
    """RSI using SMA smoothing (our method)."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return _safe_float(rsi.iloc[-1])


def _calculate_our_macd(close: pd.Series):
    """MACD using EWM (our method)."""
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal
    return (
        _safe_float(macd_line.iloc[-1]),
        _safe_float(signal.iloc[-1]),
        _safe_float(histogram.iloc[-1]),
    )


def _calculate_our_bb(close: pd.Series, period: int = 20, std_dev: float = 2.0):
    """Bollinger Bands (our method, ddof=1)."""
    middle = _safe_float(close.rolling(period).mean().iloc[-1])
    std = _safe_float(close.rolling(period).std().iloc[-1])  # ddof=1 by default
    if middle is None or std is None:
        return None, None, None, None
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    width = (upper - lower) / middle * 100 if middle != 0 else 0.0
    return upper, middle, lower, width


def run_cross_validation(
    ticker: str,
    period: str = "1y",
    data: Optional[pd.DataFrame] = None,
) -> CrossValidationResponse:
    """Run cross-validation for a ticker.

    Args:
        ticker: Ticker symbol (e.g., 'AAPL', '005930.KS').
        period: yfinance period string (e.g., '1y', '6mo').
        data: Optional pre-loaded OHLCV DataFrame (columns: Open/High/Low/Close/Volume or lowercase).

    Returns:
        CrossValidationResponse with indicator comparisons.

    Raises:
        ValueError: If insufficient data or ticker fetch fails.
    """
    if data is None:
        import yfinance as yf

        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError(f"No data available for ticker '{ticker}' with period '{period}'")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        data = df

    # Normalize column names to title case for consistency
    col_map = {c.lower(): c for c in data.columns}
    close_col = col_map.get("close", "Close")
    if close_col not in data.columns:
        raise ValueError(f"DataFrame must contain a 'Close' column. Found: {list(data.columns)}")
    close = data[close_col]

    if len(close) < 60:
        raise ValueError(f"Insufficient data for cross-validation: {len(close)} rows (need >=60)")

    # Calculate reference indicators using ta library
    try:
        from ta.momentum import RSIIndicator
        from ta.trend import MACD as TAMACD
        from ta.volatility import BollingerBands
    except ImportError:
        raise RuntimeError(
            "ta library is required for cross-validation. Install with: pip install ta"
        )

    comparisons = []

    # --- RSI ---
    our_rsi = _calculate_our_rsi(close, 14)
    rsi_ind = RSIIndicator(close=close, window=14, fillna=False)
    ref_rsi = _safe_float(rsi_ind.rsi().iloc[-1])
    comparisons.append(_compare(
        "RSI (14)",
        our_rsi, ref_rsi,
        abs_tol=_RSI_ABS_TOL,
        note="Our method: SMA smoothing. Reference: Wilder's EWM (TradingView).",
    ))

    # --- MACD ---
    our_macd, our_signal, our_hist = _calculate_our_macd(close)
    macd_ind = TAMACD(close=close, window_fast=12, window_slow=26, window_sign=9, fillna=False)
    ref_macd = _safe_float(macd_ind.macd().iloc[-1])
    ref_signal = _safe_float(macd_ind.macd_signal().iloc[-1])
    ref_hist = _safe_float(macd_ind.macd_diff().iloc[-1])

    comparisons.append(_compare("MACD Line", our_macd, ref_macd, abs_tol=_MACD_ABS_TOL))
    comparisons.append(_compare("MACD Signal", our_signal, ref_signal, abs_tol=_MACD_ABS_TOL))
    comparisons.append(_compare("MACD Histogram", our_hist, ref_hist, abs_tol=_MACD_ABS_TOL))

    # --- Bollinger Bands ---
    our_bb_upper, our_bb_middle, our_bb_lower, our_bb_width = _calculate_our_bb(close)
    bb_ind = BollingerBands(close=close, window=20, window_dev=2, fillna=False)
    ref_bb_upper = _safe_float(bb_ind.bollinger_hband().iloc[-1])
    ref_bb_middle = _safe_float(bb_ind.bollinger_mavg().iloc[-1])
    ref_bb_lower = _safe_float(bb_ind.bollinger_lband().iloc[-1])
    ref_bb_width = None
    if ref_bb_upper is not None and ref_bb_lower is not None and ref_bb_middle is not None:
        ref_bb_width = (ref_bb_upper - ref_bb_lower) / ref_bb_middle * 100 if ref_bb_middle != 0 else 0.0

    comparisons.append(_compare(
        "BB Upper", our_bb_upper, ref_bb_upper,
        pct_tol=1.0,
        note="ddof=1 (ours) vs ddof=0 (ta). Small divergence expected.",
    ))
    comparisons.append(_compare("BB Middle", our_bb_middle, ref_bb_middle, abs_tol=0.001))
    comparisons.append(_compare(
        "BB Lower", our_bb_lower, ref_bb_lower,
        pct_tol=1.0,
        note="ddof=1 (ours) vs ddof=0 (ta). Small divergence expected.",
    ))
    comparisons.append(_compare(
        "BB Width (%)", our_bb_width, ref_bb_width,
        pct_tol=_BB_PCT_TOL,
        note="Width diverges due to different std ddof.",
    ))

    overall_pass = all(c.match for c in comparisons)

    return CrossValidationResponse(
        ticker=ticker,
        period=period,
        data_points=len(close),
        comparisons=comparisons,
        overall_pass=overall_pass,
        known_divergences=KNOWN_DIVERGENCES,
    )
