"""L3 property-based tests for condition invariants."""

from __future__ import annotations

import pandas as pd
from hypothesis import assume, given, settings
from hypothesis.strategies import floats, integers

from screener.conditions.ma import AboveMACondition
from screener.conditions.momentum import EMASlopeCondition, SMASlopeCondition
from screener.conditions.price import MaxPriceCondition, MinPriceCondition, PriceChangeCondition
from screener.conditions.quant_oscillators import BollingerPercentBCondition
from screener.conditions.rsi import RSIOverboughtCondition, RSIOversoldCondition, RSIRangeCondition
from tests.fixtures.synthetic_data import build_fixture

PRICE_COLS = ["open", "high", "low", "close"]


def _scale_prices(data: pd.DataFrame, scale: float) -> pd.DataFrame:
    scaled = data.copy()
    scaled[PRICE_COLS] = scaled[PRICE_COLS] * scale
    return scaled


def _append_rising_day(data: pd.DataFrame, gain_pct: float) -> pd.DataFrame:
    extended = data.copy()
    last = extended.iloc[-1]
    new_close = float(last["close"]) * (1.0 + gain_pct / 100.0)
    new_open = float(last["close"]) * (1.0 + (gain_pct / 2.0) / 100.0)
    new_high = max(new_open, new_close) * 1.003
    new_low = min(new_open, new_close) * 0.997
    new_volume = float(last["volume"])

    next_index = len(extended)
    extended.loc[next_index] = {
        "open": new_open,
        "high": new_high,
        "low": new_low,
        "close": new_close,
        "volume": new_volume,
    }
    return extended


def _prepend_burn_in(data: pd.DataFrame, burn_in_days: int, seed: int = 7) -> pd.DataFrame:
    burn_in = build_fixture("random_walk", burn_in_days, "price_volume", seed=seed)
    return pd.concat([burn_in, data], ignore_index=True)


@given(scale=floats(min_value=0.1, max_value=100.0))
@settings(max_examples=30, deadline=None)
def test_rsi_oversold_scale_invariant(scale: float):
    data = build_fixture("strong_downtrend", 200, "price_volume")
    cond = RSIOversoldCondition(threshold=30, period=14)

    base = cond.evaluate("TEST", data)
    scaled = cond.evaluate("TEST", _scale_prices(data, scale))

    assert base.matched == scaled.matched


@given(scale=floats(min_value=0.1, max_value=100.0))
@settings(max_examples=30, deadline=None)
def test_rsi_overbought_scale_invariant(scale: float):
    data = build_fixture("strong_uptrend", 200, "price_volume")
    cond = RSIOverboughtCondition(threshold=70, period=14)

    base = cond.evaluate("TEST", data)
    scaled = cond.evaluate("TEST", _scale_prices(data, scale))

    assert base.matched == scaled.matched


@given(scale=floats(min_value=0.1, max_value=100.0))
@settings(max_examples=30, deadline=None)
def test_rsi_range_scale_invariant(scale: float):
    data = build_fixture("random_walk", 200, "price_volume", seed=42)
    cond = RSIRangeCondition(lower=30, upper=70, period=14)

    base = cond.evaluate("TEST", data)
    scaled = cond.evaluate("TEST", _scale_prices(data, scale))

    assert base.matched == scaled.matched


@given(scale=floats(min_value=0.1, max_value=100.0))
@settings(max_examples=30, deadline=None)
def test_ema_slope_scale_invariant(scale: float):
    data = build_fixture("strong_uptrend", 200, "price_volume")
    cond = EMASlopeCondition(period=20, lookback_days=5, min_slope_pct=0.0)

    base = cond.evaluate("TEST", data)
    scaled = cond.evaluate("TEST", _scale_prices(data, scale))

    assert base.matched == scaled.matched
    assert abs(base.details["slope_pct"] - scaled.details["slope_pct"]) < 1e-9


@given(scale=floats(min_value=0.1, max_value=100.0))
@settings(max_examples=30, deadline=None)
def test_sma_slope_scale_invariant(scale: float):
    data = build_fixture("strong_uptrend", 200, "price_volume")
    cond = SMASlopeCondition(period=20, lookback_days=5, min_slope_pct=0.0)

    base = cond.evaluate("TEST", data)
    scaled = cond.evaluate("TEST", _scale_prices(data, scale))

    assert base.matched == scaled.matched
    assert abs(base.details["slope_pct"] - scaled.details["slope_pct"]) < 1e-9


@given(scale=floats(min_value=0.1, max_value=100.0))
@settings(max_examples=30, deadline=None)
def test_price_change_scale_invariant(scale: float):
    data = build_fixture("strong_uptrend", 200, "price_volume")
    cond = PriceChangeCondition(days=10, min_change_pct=5.0, max_change_pct=50.0)

    base = cond.evaluate("TEST", data)
    scaled = cond.evaluate("TEST", _scale_prices(data, scale))

    assert base.matched == scaled.matched
    assert abs(base.details["change_pct"] - scaled.details["change_pct"]) < 1e-9


@given(scale=floats(min_value=0.1, max_value=100.0))
@settings(max_examples=30, deadline=None)
def test_bollinger_percent_b_scale_invariant(scale: float):
    data = build_fixture("random_walk", 200, "price_volume", seed=99)
    cond = BollingerPercentBCondition(period=20, std_mult=2.0, min_percent_b=-1.0, max_percent_b=2.0)

    base = cond.evaluate("TEST", data)
    scaled = cond.evaluate("TEST", _scale_prices(data, scale))

    assert base.matched == scaled.matched
    assert abs(base.details["percent_b"] - scaled.details["percent_b"]) < 1e-9


@given(gain_pct=floats(min_value=0.2, max_value=5.0))
@settings(max_examples=25, deadline=None)
def test_above_ma_monotonic_after_up_extension(gain_pct: float):
    data = build_fixture("strong_uptrend", 200, "price_volume")
    cond = AboveMACondition(period=20, min_distance_pct=0.0)

    base = cond.evaluate("TEST", data)
    assume(base.matched)

    extended = _append_rising_day(data, gain_pct)
    after = cond.evaluate("TEST", extended)

    assert after.matched


@given(gain_pct=floats(min_value=0.2, max_value=5.0))
@settings(max_examples=25, deadline=None)
def test_ema_slope_monotonic_after_up_extension(gain_pct: float):
    data = build_fixture("strong_uptrend", 200, "price_volume")
    cond = EMASlopeCondition(period=20, lookback_days=5, min_slope_pct=0.0)

    base = cond.evaluate("TEST", data)
    assume(base.matched)

    extended = _append_rising_day(data, gain_pct)
    after = cond.evaluate("TEST", extended)

    assert after.matched


@given(gain_pct=floats(min_value=0.2, max_value=5.0))
@settings(max_examples=25, deadline=None)
def test_rsi_overbought_monotonic_after_up_extension(gain_pct: float):
    data = build_fixture("strong_uptrend", 200, "price_volume")
    cond = RSIOverboughtCondition(threshold=70, period=14)

    base = cond.evaluate("TEST", data)
    assume(base.matched)

    extended = _append_rising_day(data, gain_pct)
    after = cond.evaluate("TEST", extended)

    assert after.matched


@given(burn_in_days=integers(min_value=50, max_value=100))
@settings(max_examples=25, deadline=None)
def test_min_price_suffix_stable_with_burn_in(burn_in_days: int):
    base = build_fixture("strong_uptrend", 200, "price_volume")
    padded = _prepend_burn_in(base, burn_in_days)
    cond = MinPriceCondition(min_price=100)

    assert cond.evaluate("TEST", base).matched == cond.evaluate("TEST", padded).matched


@given(burn_in_days=integers(min_value=50, max_value=100))
@settings(max_examples=25, deadline=None)
def test_max_price_suffix_stable_with_burn_in(burn_in_days: int):
    base = build_fixture("strong_downtrend", 200, "price_volume")
    padded = _prepend_burn_in(base, burn_in_days)
    cond = MaxPriceCondition(max_price=100)

    assert cond.evaluate("TEST", base).matched == cond.evaluate("TEST", padded).matched


@given(burn_in_days=integers(min_value=50, max_value=100))
@settings(max_examples=25, deadline=None)
def test_rsi_oversold_suffix_stable_with_burn_in(burn_in_days: int):
    base = build_fixture("strong_downtrend", 200, "price_volume")
    padded = _prepend_burn_in(base, burn_in_days)
    cond = RSIOversoldCondition(threshold=30, period=14)

    assert cond.evaluate("TEST", base).matched == cond.evaluate("TEST", padded).matched


@given(burn_in_days=integers(min_value=50, max_value=100))
@settings(max_examples=25, deadline=None)
def test_above_ma_suffix_stable_with_burn_in(burn_in_days: int):
    base = build_fixture("strong_uptrend", 200, "price_volume")
    padded = _prepend_burn_in(base, burn_in_days)
    cond = AboveMACondition(period=20, min_distance_pct=0.0)

    assert cond.evaluate("TEST", base).matched == cond.evaluate("TEST", padded).matched


@given(
    oversold_threshold=floats(min_value=10.0, max_value=40.0),
    overbought_threshold=floats(min_value=60.0, max_value=90.0),
)
@settings(max_examples=30, deadline=None)
def test_rsi_negation_consistency(oversold_threshold: float, overbought_threshold: float):
    data = build_fixture("random_walk", 200, "price_volume", seed=123)

    oversold = RSIOversoldCondition(threshold=oversold_threshold, period=14).evaluate("TEST", data)
    overbought = RSIOverboughtCondition(threshold=overbought_threshold, period=14).evaluate("TEST", data)

    assert not (oversold.matched and overbought.matched), (
        f"RSI cannot be both oversold (<{oversold_threshold}) and "
        f"overbought (>{overbought_threshold}) at the same time"
    )
