import numpy as np
import pandas as pd

import screener.conditions.quant_trend as quant_trend
from screener.conditions.quant_trend import (
    Momentum121Condition,
    VolatilityNDayCondition,
    DistanceFrom52WHighCondition,
    RelativeStrengthVsBenchmarkCondition,
    ADXTrendStrengthCondition,
    MARibbonAlignmentCondition,
    GoldenCross50200Condition,
    DeathCross50200Condition,
    DonchianChannelBreakoutCondition,
    KeltnerChannelBreakoutCondition,
    SupertrendSignalCondition,
)
from screener.conditions.registry import get_condition_metadata


def _df(n=320):
    idx = pd.bdate_range("2024-01-02", periods=n)
    close = pd.Series(np.r_[np.linspace(100, 90, n // 3), np.linspace(91, 140, n - n // 3)], index=idx)
    open_ = close * 0.998
    high = close * 1.01
    low = close * 0.99
    volume = pd.Series(np.linspace(1_000_000, 2_000_000, n), index=idx)
    benchmark = pd.Series(np.linspace(100, 120, n), index=idx)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume, "benchmark_close": benchmark}, index=idx)


def test_quant_trend_keys_registered():
    keys = set(get_condition_metadata().keys())
    expected = {
        "momentum_12_1",
        "volatility_n_day",
        "distance_from_52w_high",
        "relative_strength_vs_benchmark",
        "adx_trend_strength",
        "ma_ribbon_alignment",
        "golden_cross_50_200",
        "death_cross_50_200",
        "donchian_channel_breakout",
        "keltner_channel_breakout",
        "supertrend_signal",
    }
    assert expected.issubset(keys)


def test_quant_trend_conditions_compute():
    data = _df()
    assert "return_pct" in Momentum121Condition(min_return_pct=-100).evaluate("T", data).details
    assert "annualized_vol_pct" in VolatilityNDayCondition(max_annualized_vol_pct=100).evaluate("T", data).details
    assert "distance_pct" in DistanceFrom52WHighCondition(max_distance_pct=100).evaluate("T", data).details
    assert "excess_return_pct" in RelativeStrengthVsBenchmarkCondition(min_excess_return_pct=-100).evaluate("T", data).details
    assert "adx" in ADXTrendStrengthCondition(min_adx=0).evaluate("T", data).details
    assert "short" in MARibbonAlignmentCondition().evaluate("T", data).details
    assert "cross_day" in GoldenCross50200Condition(lookback_days=20).evaluate("T", data).details
    assert "cross_day" in DeathCross50200Condition(lookback_days=20).evaluate("T", data).details
    assert "upper_prev" in DonchianChannelBreakoutCondition(lookback_days=20).evaluate("T", data).details
    assert "upper" in KeltnerChannelBreakoutCondition().evaluate("T", data).details
    assert "direction" in SupertrendSignalCondition().evaluate("T", data).details


def test_relative_strength_without_benchmark_failsafe():
    data = _df().drop(columns=["benchmark_close"])
    result = RelativeStrengthVsBenchmarkCondition().evaluate("T", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"


def test_supertrend_signal_bullish_and_bearish_cross(monkeypatch):
    data = _df(80)
    close = data["close"]

    bullish_st = close + 10.0
    bullish_st.iloc[-2] = close.iloc[-2] + 1.0
    bullish_st.iloc[-1] = close.iloc[-1] - 1.0
    monkeypatch.setattr(quant_trend, "_supertrend", lambda d, p, m: bullish_st)
    bullish = SupertrendSignalCondition(direction="bullish", lookback_days=3).evaluate("T", data)
    assert bullish.matched is True
    assert bullish.details["cross_day"] == 1

    bearish_st = close - 10.0
    bearish_st.iloc[-2] = close.iloc[-2] - 1.0
    bearish_st.iloc[-1] = close.iloc[-1] + 1.0
    monkeypatch.setattr(quant_trend, "_supertrend", lambda d, p, m: bearish_st)
    bearish = SupertrendSignalCondition(direction="bearish", lookback_days=3).evaluate("T", data)
    assert bearish.matched is True
    assert bearish.details["cross_day"] == 1


def test_supertrend_signal_insufficient_and_nan_guard(monkeypatch):
    short = _df(8)
    insufficient = SupertrendSignalCondition(period=10, lookback_days=3).evaluate("T", short)
    assert insufficient.matched is False
    assert insufficient.details.get("error") == "Insufficient data"

    data = _df(80)
    monkeypatch.setattr(quant_trend, "_supertrend", lambda d, p, m: pd.Series(np.nan, index=d.index))
    nan_case = SupertrendSignalCondition(direction="bullish").evaluate("T", data)
    assert nan_case.matched is False
    assert nan_case.details.get("error") == "Insufficient data"
