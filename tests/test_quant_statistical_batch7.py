import numpy as np
import pandas as pd

from screener.conditions.quant_statistical import (
    ParabolicSARFlipCondition,
    LinearRegressionSlopeFilterCondition,
    LinearRegressionAngleFilterCondition,
    LinearRegressionR2FilterCondition,
    BetaToBenchmarkCondition,
    CorrelationToBenchmarkCondition,
    SupportRetestSignalCondition,
    ResistanceRetestSignalCondition,
    AnalystRevision1MCondition,
    AnalystRevision3MCondition,
)
from screener.conditions.registry import get_condition_metadata


def _df(n=280):
    idx = pd.bdate_range("2024-01-02", periods=n)
    close = pd.Series(np.r_[np.linspace(120, 95, n // 2), np.linspace(96, 170, n - n // 2)], index=idx)
    open_ = close * 0.998
    high = close * 1.01
    low = close * 0.99
    volume = pd.Series(np.linspace(1_000_000, 2_000_000, n), index=idx)
    benchmark = pd.Series(np.linspace(100, 130, n), index=idx)
    ar1m = pd.Series(np.linspace(-2.0, 4.0, n), index=idx)
    ar3m = pd.Series(np.linspace(-5.0, 8.0, n), index=idx)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "benchmark_close": benchmark,
            "analyst_revision_1m": ar1m,
            "analyst_revision_3m": ar3m,
        },
        index=idx,
    )


def test_quant_statistical_keys_registered():
    keys = set(get_condition_metadata().keys())
    expected = {
        "parabolic_sar_flip",
        "linear_regression_slope_filter",
        "linear_regression_angle_filter",
        "linear_regression_r2_filter",
        "beta_to_benchmark",
        "correlation_to_benchmark",
        "support_retest_signal",
        "resistance_retest_signal",
        "analyst_revision_1m",
        "analyst_revision_3m",
    }
    assert expected.issubset(keys)


def test_quant_statistical_conditions_compute():
    data = _df()
    assert "flip_day" in ParabolicSARFlipCondition(lookback_days=20).evaluate("T", data).details
    assert "slope" in LinearRegressionSlopeFilterCondition(min_slope=-1e9).evaluate("T", data).details
    assert "angle_deg" in LinearRegressionAngleFilterCondition(min_angle_deg=-90).evaluate("T", data).details
    assert "r2" in LinearRegressionR2FilterCondition(min_r2=0).evaluate("T", data).details
    assert "beta" in BetaToBenchmarkCondition(max_beta=10).evaluate("T", data).details
    assert "correlation" in CorrelationToBenchmarkCondition(max_corr=1).evaluate("T", data).details
    assert "support" in SupportRetestSignalCondition().evaluate("T", data).details
    assert "resistance" in ResistanceRetestSignalCondition().evaluate("T", data).details
    assert "revision_pct" in AnalystRevision1MCondition(min_revision_pct=-100).evaluate("T", data).details
    assert "revision_pct" in AnalystRevision3MCondition(min_revision_pct=-100).evaluate("T", data).details


def test_benchmark_missing_failsafe():
    data = _df().drop(columns=["benchmark_close"])
    result = BetaToBenchmarkCondition().evaluate("T", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
