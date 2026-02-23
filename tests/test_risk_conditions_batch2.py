import numpy as np
import pandas as pd

from screener.conditions.registry import get_condition_metadata
from screener.conditions.risk import (
    DownsideVolatilityFilterCondition,
    SemivarianceFilterCondition,
    RollingSharpeFilterCondition,
    RollingSortinoFilterCondition,
    UlcerIndexFilterCondition,
    CalmarRatioFilterCondition,
    MaxDrawdownWindowFilterCondition,
    ReturnSkewnessFilterCondition,
    ReturnKurtosisFilterCondition,
    IntradayReturnFilterCondition,
)


def _df(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close * 0.998,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.linspace(1_000_000, 1_500_000, len(close)),
        }
    )


def test_risk_condition_keys_registered():
    metadata = get_condition_metadata()
    expected = {
        "downside_volatility_filter",
        "semivariance_filter",
        "rolling_sharpe_filter",
        "rolling_sortino_filter",
        "ulcer_index_filter",
        "calmar_ratio_filter",
        "max_drawdown_window_filter",
        "return_skewness_filter",
        "return_kurtosis_filter",
        "intraday_return_filter",
    }
    assert expected.issubset(set(metadata.keys()))


def test_risk_conditions_evaluate_on_uptrend():
    close = pd.Series(np.linspace(100, 150, 300))
    data = _df(close)

    assert "downside_vol_pct" in DownsideVolatilityFilterCondition().evaluate("T", data).details
    assert "semivariance" in SemivarianceFilterCondition().evaluate("T", data).details
    assert "sharpe" in RollingSharpeFilterCondition(min_sharpe=-10).evaluate("T", data).details
    assert "sortino" in RollingSortinoFilterCondition(min_sortino=-10).evaluate("T", data).details
    assert "ulcer_index" in UlcerIndexFilterCondition(max_ulcer_index=100).evaluate("T", data).details
    assert "calmar" in CalmarRatioFilterCondition(min_calmar=-10).evaluate("T", data).details
    assert "max_drawdown_pct" in MaxDrawdownWindowFilterCondition(max_drawdown_pct=100).evaluate("T", data).details
    assert "skewness" in ReturnSkewnessFilterCondition(min_skewness=-10).evaluate("T", data).details
    assert "kurtosis" in ReturnKurtosisFilterCondition(max_kurtosis=100).evaluate("T", data).details
    assert "intraday_return_pct" in IntradayReturnFilterCondition(min_intraday_return_pct=-100).evaluate("T", data).details


def test_insufficient_data_risk_condition():
    close = pd.Series(np.linspace(100, 102, 3))
    data = _df(close)
    result = DownsideVolatilityFilterCondition(lookback_days=60).evaluate("T", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
