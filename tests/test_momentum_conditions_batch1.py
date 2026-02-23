import numpy as np
import pandas as pd

from screener.conditions.momentum import (
    EMACrossCondition,
    EMASlopeCondition,
    SMASlopeCondition,
    MACDSignalCrossCondition,
    MACDHistogramSlopeCondition,
    CCIOverboughtOversoldCondition,
    WilliamsRReversalCondition,
    TRIXCrossCondition,
    AroonTrendSignalCondition,
    MoneyFlowIndexSignalCondition,
)
from screener.conditions.registry import get_condition_metadata


def _build_df(close: pd.Series) -> pd.DataFrame:
    high = close * 1.01
    low = close * 0.99
    open_ = close * 0.995
    volume = pd.Series(np.linspace(1_000_000, 2_000_000, len(close)), index=close.index)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


def test_momentum_condition_keys_registered():
    metadata = get_condition_metadata()
    expected = {
        "ema_cross",
        "ema_slope",
        "sma_slope",
        "macd_signal_cross",
        "macd_histogram_slope",
        "cci_overbought_oversold",
        "williams_r_reversal",
        "trix_cross",
        "aroon_trend_signal",
        "money_flow_index_signal",
    }
    assert expected.issubset(set(metadata.keys()))


def test_ema_cross_bullish_matches():
    close = pd.Series(np.r_[np.linspace(120, 90, 40), np.linspace(91, 130, 30)])
    data = _build_df(close)
    cond = EMACrossCondition(fast_period=5, slow_period=20, lookback_days=10, direction="bullish")
    result = cond.evaluate("TEST", data)
    assert result.matched is True


def test_ema_and_sma_slope_on_uptrend_match():
    close = pd.Series(np.linspace(100, 150, 80))
    data = _build_df(close)

    ema_result = EMASlopeCondition(period=20, lookback_days=5, min_slope_pct=0.1).evaluate("TEST", data)
    sma_result = SMASlopeCondition(period=20, lookback_days=5, min_slope_pct=0.1).evaluate("TEST", data)

    assert ema_result.matched is True
    assert sma_result.matched is True


def test_macd_related_conditions_compute():
    close = pd.Series(np.r_[np.linspace(100, 85, 35), np.linspace(86, 125, 45)])
    data = _build_df(close)

    cross = MACDSignalCrossCondition(direction="bullish", lookback_days=10).evaluate("TEST", data)
    slope = MACDHistogramSlopeCondition(lookback_days=3, min_slope=-0.5).evaluate("TEST", data)

    assert "macd" in cross.details
    assert slope.details["slope"] is not None


def test_cci_williams_trix_aroon_mfi_compute():
    close = pd.Series(np.r_[np.linspace(100, 80, 30), np.linspace(81, 130, 70)])
    data = _build_df(close)

    cci = CCIOverboughtOversoldCondition(mode="oversold", threshold=50).evaluate("TEST", data)
    wr = WilliamsRReversalCondition(direction="bullish").evaluate("TEST", data)
    trix = TRIXCrossCondition(direction="bullish", lookback_days=10).evaluate("TEST", data)
    aroon = AroonTrendSignalCondition(direction="up", min_aroon=50).evaluate("TEST", data)
    mfi = MoneyFlowIndexSignalCondition(mode="overbought", overbought=50).evaluate("TEST", data)

    assert "cci" in cci.details
    assert "williams_r" in wr.details
    assert "cross_day" in trix.details
    assert "aroon_up" in aroon.details
    assert "mfi" in mfi.details


def test_insufficient_data_returns_error():
    close = pd.Series(np.linspace(100, 105, 5))
    data = _build_df(close)
    result = MACDSignalCrossCondition().evaluate("TEST", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
