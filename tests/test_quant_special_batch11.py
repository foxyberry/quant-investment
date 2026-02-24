import numpy as np
import pandas as pd

from screener.conditions.quant_special_batch11 import (
    ShortFloatPctFilterCondition,
    ShortInterestRatioFilterCondition,
    EarningsSurpriseFilterCondition,
    PostEarningsDriftCondition,
    PreEarningsDriftCondition,
    AccrualsRatioCondition,
    AssetGrowthRateCondition,
    GrossProfitabilityCondition,
    QualityScoreCondition,
)
from screener.conditions.registry import get_condition_metadata


def _df(n=50):
    idx = pd.bdate_range("2025-01-02", periods=n)
    base = pd.Series(np.linspace(70, 90, n), index=idx)
    return pd.DataFrame(
        {
            "open": base * 0.99,
            "high": base * 1.01,
            "low": base * 0.98,
            "close": base,
            "volume": np.linspace(700_000, 1_000_000, n),
            "short_float_pct": np.full(n, 8.0),
            "short_interest_ratio": np.full(n, 3.0),
            "earnings_surprise_pct": np.full(n, 4.0),
            "post_earnings_return_pct": np.full(n, 2.5),
            "pre_earnings_return_pct": np.full(n, 1.2),
            "net_income_ttm": np.full(n, 1_000_000.0),
            "operating_cash_flow_ttm": np.full(n, 1_100_000.0),
            "total_assets": np.full(n, 15_000_000.0),
            "total_assets_prev_year": np.full(n, 14_000_000.0),
            "gross_profit_ttm": np.full(n, 3_200_000.0),
        },
        index=idx,
    )


def test_quant_special_batch11_keys_registered():
    keys = set(get_condition_metadata().keys())
    expected = {
        "short_float_pct_filter",
        "short_interest_ratio_filter",
        "earnings_surprise_filter",
        "post_earnings_drift",
        "pre_earnings_drift",
        "accruals_ratio",
        "asset_growth_rate",
        "gross_profitability",
        "quality_score",
    }
    assert expected.issubset(keys)


def test_quant_special_batch11_conditions_compute():
    data = _df()
    assert "short_float_pct" in ShortFloatPctFilterCondition(max_short_float_pct=100).evaluate("T", data).details
    assert "short_interest_ratio" in ShortInterestRatioFilterCondition(max_ratio=100).evaluate("T", data).details
    assert "surprise_pct" in EarningsSurpriseFilterCondition(min_surprise_pct=-100).evaluate("T", data).details
    assert "return_pct" in PostEarningsDriftCondition(min_return_pct=-100).evaluate("T", data).details
    assert "return_pct" in PreEarningsDriftCondition(min_return_pct=-100).evaluate("T", data).details
    assert "accruals_ratio" in AccrualsRatioCondition(max_ratio=100).evaluate("T", data).details
    assert "growth_pct" in AssetGrowthRateCondition(max_growth_pct=100).evaluate("T", data).details
    assert "ratio" in GrossProfitabilityCondition(min_ratio=-100).evaluate("T", data).details
    assert "score" in QualityScoreCondition(min_score=-100).evaluate("T", data).details


def test_missing_column_failsafe():
    data = _df().drop(columns=["short_float_pct"])
    result = ShortFloatPctFilterCondition().evaluate("T", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
