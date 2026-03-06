"""L1 semantic correctness tests for deterministic condition outcomes."""

from __future__ import annotations

from functools import partial as fp

import numpy as np
import pandas as pd
import pytest

import screener.conditions  # noqa: F401
from screener.conditions.registry import get_condition_class_map, get_condition_metadata
from tests.fixtures.synthetic_data import build_fixture

_meta = get_condition_metadata()
_cmap = get_condition_class_map()


def _make(key: str, **overrides):
    m = _meta[key]
    cls = _cmap[key]
    params = {p["name"]: p["default"] for p in m.get("params", [])}
    params.update(overrides)
    return cls(**params) if not isinstance(cls, fp) else cls(**params)


def _volume_last_day_spike() -> pd.DataFrame:
    df = build_fixture("flat", 200, "price_volume", seed=42)
    df["volume"] = 1_000_000.0
    df.loc[df.index[-1], "volume"] = 10_000_000.0
    return df


def _volume_last_day_dry() -> pd.DataFrame:
    df = build_fixture("flat", 200, "price_volume", seed=42)
    df["volume"] = 1_000_000.0
    df.loc[df.index[-1], "volume"] = 100_000.0
    return df


def _volume_increasing() -> pd.DataFrame:
    df = build_fixture("flat", 200, "price_volume", seed=42)
    df["volume"] = np.linspace(100_000, 300_000, len(df))
    return df


def _volume_decreasing() -> pd.DataFrame:
    df = build_fixture("flat", 200, "price_volume", seed=42)
    df["volume"] = np.linspace(300_000, 100_000, len(df))
    return df


def _volume_ma_ratio_true() -> pd.DataFrame:
    df = build_fixture("flat", 80, "price_volume", seed=42)
    vol = [100_000.0] * 70 + [150_000.0] * 10
    df["volume"] = vol
    return df


def _volume_ma_ratio_false() -> pd.DataFrame:
    df = build_fixture("flat", 80, "price_volume", seed=42)
    df["volume"] = 100_000.0
    return df


_CUSTOM_BUILDERS = {
    "volume_last_day_spike": _volume_last_day_spike,
    "volume_last_day_dry": _volume_last_day_dry,
    "volume_increasing": _volume_increasing,
    "volume_decreasing": _volume_decreasing,
    "volume_ma_ratio_true": _volume_ma_ratio_true,
    "volume_ma_ratio_false": _volume_ma_ratio_false,
}


def _build_data(shape: str, days: int, profile: str) -> pd.DataFrame:
    if shape.startswith("custom:"):
        return _CUSTOM_BUILDERS[shape.split(":", 1)[1]]()
    return build_fixture(shape=shape, days=days, profile=profile, seed=42)


# (test_id, key, overrides, shape, days, profile, expected)
SCENARIOS = [
    # Price
    ("min_price_true_uptrend", "min_price", {"min_price": 10}, "strong_uptrend", 200, "price_volume", True),
    ("min_price_false_uptrend", "min_price", {"min_price": 5000}, "strong_uptrend", 200, "price_volume", False),
    ("max_price_true_uptrend", "max_price", {"max_price": 3000}, "strong_uptrend", 200, "price_volume", True),
    ("max_price_false_uptrend", "max_price", {"max_price": 1000}, "strong_uptrend", 200, "price_volume", False),
    ("price_range_true_uptrend", "price_range", {"min_price": 10, "max_price": 5000}, "strong_uptrend", 200, "price_volume", True),
    ("price_range_false_uptrend", "price_range", {"min_price": 5000, "max_price": 10000}, "strong_uptrend", 200, "price_volume", False),
    ("price_change_true_uptrend", "price_change", {"days": 5, "min_change_pct": 5.0}, "strong_uptrend", 200, "price_volume", True),
    ("price_change_false_uptrend", "price_change", {"days": 5, "max_change_pct": 5.0}, "strong_uptrend", 200, "price_volume", False),
    ("drawdown_true_downtrend", "drawdown_from_high", {"lookback_days": 120, "min_drop_pct": 50.0}, "strong_downtrend", 200, "price_volume", True),
    ("drawdown_false_uptrend", "drawdown_from_high", {"lookback_days": 120, "min_drop_pct": 50.0}, "strong_uptrend", 200, "price_volume", False),
    ("return_turnaround_true_v_recovery", "return_turnaround", {"period_days": 99, "prev_max_return_pct": -5.0, "min_return_pct": 5.0}, "v_recovery", 200, "price_volume", True),
    ("return_turnaround_false_uptrend", "return_turnaround", {"period_days": 99, "prev_max_return_pct": -5.0, "min_return_pct": 5.0}, "strong_uptrend", 200, "price_volume", False),
    # Volume
    ("min_volume_true", "min_volume", {"min_volume": 100_000}, "flat", 200, "price_volume", True),
    ("min_volume_false", "min_volume", {"min_volume": 50_000_000}, "flat", 200, "price_volume", False),
    ("avg_trading_value_true", "avg_trading_value", {"lookback_days": 20, "min_value": 1.0}, "flat", 200, "price_volume", True),
    ("avg_trading_value_false", "avg_trading_value", {"lookback_days": 20, "min_value": 1e15}, "flat", 200, "price_volume", False),
    ("volume_above_avg_true_custom", "volume_above_avg", {"multiplier": 2.0, "period": 20}, "custom:volume_last_day_spike", 200, "price_volume", True),
    ("volume_above_avg_false_custom", "volume_above_avg", {"multiplier": 8.0, "period": 20}, "custom:volume_last_day_spike", 200, "price_volume", False),
    ("volume_spike_true_custom", "volume_spike", {"multiplier": 5.0, "period": 20}, "custom:volume_last_day_spike", 200, "price_volume", True),
    ("volume_spike_false_custom", "volume_spike", {"multiplier": 15.0, "period": 20}, "custom:volume_last_day_spike", 200, "price_volume", False),
    # Moving average
    ("above_ma_true_uptrend", "above_ma", {"period": 50}, "strong_uptrend", 200, "price_volume", True),
    ("above_ma_false_downtrend", "above_ma", {"period": 50}, "strong_downtrend", 200, "price_volume", False),
    ("below_ma_true_downtrend", "below_ma", {"period": 50}, "strong_downtrend", 200, "price_volume", True),
    ("below_ma_false_uptrend", "below_ma", {"period": 50}, "strong_uptrend", 200, "price_volume", False),
    # RSI
    ("rsi_oversold_true_downtrend", "rsi_oversold", {"threshold": 30, "period": 14}, "strong_downtrend", 200, "price_volume", True),
    ("rsi_oversold_false_uptrend", "rsi_oversold", {"threshold": 30, "period": 14}, "strong_uptrend", 200, "price_volume", False),
    ("rsi_overbought_true_uptrend", "rsi_overbought", {"threshold": 70, "period": 14}, "strong_uptrend", 200, "price_volume", True),
    ("rsi_overbought_false_downtrend", "rsi_overbought", {"threshold": 70, "period": 14}, "strong_downtrend", 200, "price_volume", False),
    ("rsi_range_true_flat", "rsi_range", {"lower": 20, "upper": 80, "period": 14}, "flat", 200, "price_volume", True),
    ("rsi_range_false_flat", "rsi_range", {"lower": 80, "upper": 100, "period": 14}, "flat", 200, "price_volume", False),
    # Momentum
    ("ema_slope_true_uptrend", "ema_slope", {"period": 20, "lookback_days": 5, "min_slope_pct": 0.0}, "strong_uptrend", 200, "price_volume", True),
    ("ema_slope_false_downtrend", "ema_slope", {"period": 20, "lookback_days": 5, "min_slope_pct": 0.0}, "strong_downtrend", 200, "price_volume", False),
    ("sma_slope_true_uptrend", "sma_slope", {"period": 20, "lookback_days": 5, "min_slope_pct": 0.0}, "strong_uptrend", 200, "price_volume", True),
    ("sma_slope_false_downtrend", "sma_slope", {"period": 20, "lookback_days": 5, "min_slope_pct": 0.0}, "strong_downtrend", 200, "price_volume", False),
    ("cci_overbought_true_uptrend", "cci_overbought_oversold", {"period": 20, "mode": "overbought", "threshold": 50}, "strong_uptrend", 200, "price_volume", True),
    ("cci_overbought_false_downtrend", "cci_overbought_oversold", {"period": 20, "mode": "overbought", "threshold": 50}, "strong_downtrend", 200, "price_volume", False),
    ("cci_oversold_true_downtrend", "cci_overbought_oversold", {"period": 20, "mode": "oversold", "threshold": 50}, "strong_downtrend", 200, "price_volume", True),
    ("cci_oversold_false_uptrend", "cci_overbought_oversold", {"period": 20, "mode": "oversold", "threshold": 50}, "strong_uptrend", 200, "price_volume", False),
    ("aroon_trend_up_true", "aroon_trend_signal", {"period": 25, "min_aroon": 70, "direction": "up"}, "strong_uptrend", 200, "price_volume", True),
    ("aroon_trend_up_false", "aroon_trend_signal", {"period": 25, "min_aroon": 70, "direction": "up"}, "strong_downtrend", 200, "price_volume", False),
    ("aroon_trend_down_true", "aroon_trend_signal", {"period": 25, "min_aroon": 70, "direction": "down"}, "strong_downtrend", 200, "price_volume", True),
    ("aroon_trend_down_false", "aroon_trend_signal", {"period": 25, "min_aroon": 70, "direction": "down"}, "strong_uptrend", 200, "price_volume", False),
    # Accumulation
    ("bollinger_width_true_flat", "bollinger_width", {"max_width_pct": 50.0, "period": 20}, "flat", 200, "price_volume", True),
    ("bollinger_width_false_uptrend", "bollinger_width", {"max_width_pct": 0.1, "period": 20}, "strong_uptrend", 200, "price_volume", False),
    ("obv_trend_up_true", "obv_trend", {"direction": "up", "lookback": 10}, "strong_uptrend", 200, "price_volume", True),
    ("obv_trend_up_false", "obv_trend", {"direction": "up", "lookback": 10}, "strong_downtrend", 200, "price_volume", False),
    ("obv_trend_down_true", "obv_trend", {"direction": "down", "lookback": 10}, "strong_downtrend", 200, "price_volume", True),
    ("obv_trend_down_false", "obv_trend", {"direction": "down", "lookback": 10}, "strong_uptrend", 200, "price_volume", False),
    ("price_flat_true", "price_flat", {"max_range_pct": 5.0, "period": 20}, "flat", 200, "price_volume", True),
    ("price_flat_false", "price_flat", {"max_range_pct": 0.001, "period": 20}, "strong_uptrend", 200, "price_volume", False),
    ("stochastic_below_true", "stochastic_level", {"threshold": 20.0, "condition": "below", "k_period": 14, "d_period": 3}, "strong_downtrend", 200, "price_volume", True),
    ("stochastic_below_false", "stochastic_level", {"threshold": 20.0, "condition": "below", "k_period": 14, "d_period": 3}, "strong_uptrend", 200, "price_volume", False),
    ("stochastic_above_true", "stochastic_level", {"threshold": 80.0, "condition": "above", "k_period": 14, "d_period": 3}, "strong_uptrend", 200, "price_volume", True),
    ("stochastic_above_false", "stochastic_level", {"threshold": 80.0, "condition": "above", "k_period": 14, "d_period": 3}, "strong_downtrend", 200, "price_volume", False),
    # Breakout
    ("bottom_breakout_true_uptrend", "bottom_breakout", {"lookback_days": 20, "breakout_pct": 5.0}, "strong_uptrend", 200, "price_volume", True),
    ("bottom_breakout_false_downtrend", "bottom_breakout", {"lookback_days": 20, "breakout_pct": 5.0}, "strong_downtrend", 200, "price_volume", False),
    ("resistance_breakout_true_uptrend", "resistance_breakout", {"lookback_days": 20, "breakout_margin_pct": 0.0}, "strong_uptrend", 200, "price_volume", True),
    ("resistance_breakout_false_downtrend", "resistance_breakout", {"lookback_days": 20, "breakout_margin_pct": 0.0}, "strong_downtrend", 200, "price_volume", False),
    # Risk / Trend / Oscillator / Indicator subsets
    ("downside_vol_true_flat", "downside_volatility_filter", {"lookback_days": 60, "max_downside_vol_pct": 50.0}, "flat", 200, "price_volume", True),
    ("downside_vol_false_random", "downside_volatility_filter", {"lookback_days": 60, "max_downside_vol_pct": 0.1}, "random_walk", 200, "price_volume", False),
    ("volatility_n_day_true_flat", "volatility_n_day", {"lookback_days": 60, "max_annualized_vol_pct": 200.0}, "flat", 200, "price_volume", True),
    ("volatility_n_day_false_random", "volatility_n_day", {"lookback_days": 60, "max_annualized_vol_pct": 1.0}, "random_walk", 200, "price_volume", False),
    ("adx_trend_true_uptrend", "adx_trend_strength", {"period": 14, "min_adx": 10.0, "di_direction": "any"}, "strong_uptrend", 200, "price_volume", True),
    ("adx_trend_false_flat", "adx_trend_strength", {"period": 14, "min_adx": 80.0, "di_direction": "any"}, "flat", 200, "price_volume", False),
    ("bollinger_percent_b_true", "bollinger_percent_b", {"period": 20, "std_mult": 2.0, "min_percent_b": -1.0, "max_percent_b": 2.0}, "flat", 200, "price_volume", True),
    ("bollinger_percent_b_false", "bollinger_percent_b", {"period": 20, "std_mult": 2.0, "min_percent_b": 2.5, "max_percent_b": 3.0}, "flat", 200, "price_volume", False),
    ("aroon_oscillator_true", "aroon_oscillator_signal", {"period": 25, "min_oscillator": -100.0}, "flat", 200, "price_volume", True),
    ("aroon_oscillator_false", "aroon_oscillator_signal", {"period": 25, "min_oscillator": 200.0}, "flat", 200, "price_volume", False),
    ("atr_percentile_true", "atr_percentile_filter", {"atr_period": 14, "lookback_days": 120, "max_percentile": 100.0}, "flat", 200, "price_volume", True),
    ("atr_percentile_false", "atr_percentile_filter", {"atr_period": 14, "lookback_days": 120, "max_percentile": 0.0}, "flat", 200, "price_volume", False),
    ("relative_volume_percentile_true", "relative_volume_percentile", {"lookback_days": 60, "min_percentile": 99.0}, "custom:volume_last_day_spike", 200, "price_volume", True),
    ("relative_volume_percentile_false", "relative_volume_percentile", {"lookback_days": 60, "min_percentile": 50.0}, "custom:volume_last_day_dry", 200, "price_volume", False),
    ("natr_true", "natr_filter", {"period": 14, "max_natr_pct": 100.0}, "flat", 200, "price_volume", True),
    ("natr_false", "natr_filter", {"period": 14, "max_natr_pct": 0.1}, "strong_uptrend", 200, "price_volume", False),
    # Basic catalog
    ("price_lag_gt_true_uptrend", "price_lag_compare", {"field": "close", "lag_a": 1, "lag_b": 3, "operator": "gt"}, "strong_uptrend", 200, "price_volume", True),
    ("price_lag_gt_false_downtrend", "price_lag_compare", {"field": "close", "lag_a": 1, "lag_b": 3, "operator": "gt"}, "strong_downtrend", 200, "price_volume", False),
    ("price_lag_lt_true_downtrend", "price_lag_compare", {"field": "close", "lag_a": 1, "lag_b": 3, "operator": "lt"}, "strong_downtrend", 200, "price_volume", True),
    ("price_lag_lt_false_uptrend", "price_lag_compare", {"field": "close", "lag_a": 1, "lag_b": 3, "operator": "lt"}, "strong_uptrend", 200, "price_volume", False),
    ("volume_lag_gt_true", "volume_lag_compare", {"lag_a": 1, "lag_b": 2, "operator": "gt"}, "custom:volume_increasing", 200, "price_volume", True),
    ("volume_lag_gt_false", "volume_lag_compare", {"lag_a": 1, "lag_b": 2, "operator": "gt"}, "custom:volume_decreasing", 200, "price_volume", False),
    ("return_pct_range_true_uptrend", "return_pct_range", {"lookback_days": 20, "min_return_pct": 40.0, "max_return_pct": 60.0}, "strong_uptrend", 200, "price_volume", True),
    ("return_pct_range_false_uptrend", "return_pct_range", {"lookback_days": 20, "min_return_pct": -10.0, "max_return_pct": 10.0}, "strong_uptrend", 200, "price_volume", False),
    ("volume_ma_ratio_true", "volume_ma_ratio", {"short_period": 2, "long_period": 20, "min_ratio": 1.1, "max_ratio": 2.0}, "custom:volume_ma_ratio_true", 80, "price_volume", True),
    ("volume_ma_ratio_false", "volume_ma_ratio", {"short_period": 2, "long_period": 20, "min_ratio": 1.1, "max_ratio": 2.0}, "custom:volume_ma_ratio_false", 80, "price_volume", False),
]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s[0])
def test_semantic_correctness(scenario):
    test_id, key, overrides, shape, days, profile, expected = scenario
    cond = _make(key, **overrides)
    data = _build_data(shape, days, profile)
    result = cond.evaluate("TEST", data)
    assert result.matched == expected, (
        f"{test_id}: expected matched={expected}, got {result.matched}. details={result.details}"
    )
