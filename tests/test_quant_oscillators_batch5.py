import numpy as np
import pandas as pd

from screener.conditions.quant_oscillators import (
    BollingerSqueezeBreakoutCondition,
    BollingerPercentBCondition,
    PPOSignalCrossCondition,
    StochasticCrossSignalCondition,
    StochRSISignalCondition,
    AroonOscillatorSignalCondition,
    UltimateOscillatorSignalCondition,
    ChaikinMoneyFlowSignalCondition,
    ChaikinOscillatorSignalCondition,
    ADLineTrendCondition,
)
from screener.conditions.registry import get_condition_metadata


def _df(n=260):
    idx = pd.bdate_range("2024-01-02", periods=n)
    close = pd.Series(np.r_[np.linspace(120, 100, n // 2), np.linspace(101, 150, n - n // 2)], index=idx)
    open_ = close * 0.997
    high = close * 1.01
    low = close * 0.99
    volume = pd.Series(np.linspace(1_000_000, 2_000_000, n), index=idx)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def test_quant_oscillator_keys_registered():
    keys = set(get_condition_metadata().keys())
    expected = {
        "bollinger_squeeze_breakout",
        "bollinger_percent_b",
        "ppo_signal_cross",
        "stochastic_cross_signal",
        "stochrsi_signal",
        "aroon_oscillator_signal",
        "ultimate_oscillator_signal",
        "chaikin_money_flow_signal",
        "chaikin_oscillator_signal",
        "ad_line_trend",
    }
    assert expected.issubset(keys)


def test_quant_oscillator_conditions_compute():
    data = _df()
    assert "prev_width_pct" in BollingerSqueezeBreakoutCondition(max_width_pct=100).evaluate("T", data).details
    assert "percent_b" in BollingerPercentBCondition().evaluate("T", data).details
    assert "cross_day" in PPOSignalCrossCondition().evaluate("T", data).details
    assert "cross_day" in StochasticCrossSignalCondition().evaluate("T", data).details
    assert "stochrsi" in StochRSISignalCondition().evaluate("T", data).details
    assert "oscillator" in AroonOscillatorSignalCondition(min_oscillator=-100).evaluate("T", data).details
    assert "ultimate_oscillator" in UltimateOscillatorSignalCondition(min_value=-100).evaluate("T", data).details
    assert "cmf" in ChaikinMoneyFlowSignalCondition(min_cmf=-10).evaluate("T", data).details
    assert "chaikin_oscillator" in ChaikinOscillatorSignalCondition(min_value=-1e12).evaluate("T", data).details
    assert "ad_slope" in ADLineTrendCondition().evaluate("T", data).details


def test_insufficient_data_failsafe():
    data = _df(10)
    result = UltimateOscillatorSignalCondition().evaluate("T", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
