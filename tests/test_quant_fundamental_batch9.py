import numpy as np
import pandas as pd

from screener.conditions.quant_fundamental_batch9 import (
    RevenueCAGR3YCondition,
    RevenueGrowthYoYCondition,
    RevenueStabilityScoreCondition,
    EarningsStabilityScoreCondition,
    DebtServiceCoverageRatioCondition,
    NetDebtToEbitdaCondition,
    InterestCoverageRatioCondition,
    CashConversionRatioCondition,
    ROCEFilterCondition,
    ROAFilterCondition,
)
from screener.conditions.registry import get_condition_metadata


def _df(n=60):
    idx = pd.bdate_range("2025-01-02", periods=n)
    base = pd.Series(np.linspace(90, 120, n), index=idx)
    return pd.DataFrame(
        {
            "open": base * 0.99,
            "high": base * 1.01,
            "low": base * 0.98,
            "close": base,
            "volume": np.linspace(900_000, 1_200_000, n),
            "revenue_ttm": np.full(n, 10_000_000.0),
            "revenue_3y_ago": np.full(n, 7_000_000.0),
            "revenue_prev_year": np.full(n, 9_100_000.0),
            "revenue_y0": np.full(n, 10_000_000.0),
            "revenue_y1": np.full(n, 9_700_000.0),
            "revenue_y2": np.full(n, 9_500_000.0),
            "revenue_y3": np.full(n, 9_200_000.0),
            "revenue_y4": np.full(n, 9_000_000.0),
            "net_income_y0": np.full(n, 1_000_000.0),
            "net_income_y1": np.full(n, 950_000.0),
            "net_income_y2": np.full(n, 920_000.0),
            "net_income_y3": np.full(n, 900_000.0),
            "net_income_y4": np.full(n, 880_000.0),
            "operating_income_ttm": np.full(n, 1_800_000.0),
            "debt_service_ttm": np.full(n, 1_000_000.0),
            "total_debt": np.full(n, 5_000_000.0),
            "cash_and_equivalents": np.full(n, 1_200_000.0),
            "ebitda_ttm": np.full(n, 2_000_000.0),
            "ebit_ttm": np.full(n, 1_700_000.0),
            "interest_expense_ttm": np.full(n, -300_000.0),
            "operating_cash_flow_ttm": np.full(n, 1_300_000.0),
            "net_income_ttm": np.full(n, 1_100_000.0),
            "total_assets": np.full(n, 20_000_000.0),
            "current_liabilities": np.full(n, 6_000_000.0),
        },
        index=idx,
    )


def test_quant_fundamental_batch9_keys_registered():
    keys = set(get_condition_metadata().keys())
    expected = {
        "revenue_cagr_3y",
        "revenue_growth_yoy",
        "revenue_stability_score",
        "earnings_stability_score",
        "debt_service_coverage_ratio",
        "net_debt_to_ebitda",
        "interest_coverage_ratio",
        "cash_conversion_ratio",
        "roce_filter",
        "roa_filter",
    }
    assert expected.issubset(keys)


def test_quant_fundamental_batch9_conditions_compute():
    data = _df()
    assert "cagr_pct" in RevenueCAGR3YCondition(min_cagr_pct=-100).evaluate("T", data).details
    assert "growth_pct" in RevenueGrowthYoYCondition(min_growth_pct=-100).evaluate("T", data).details
    assert "score" in RevenueStabilityScoreCondition(max_cv=1).evaluate("T", data).details
    assert "score" in EarningsStabilityScoreCondition(max_cv=1).evaluate("T", data).details
    assert "ratio" in DebtServiceCoverageRatioCondition(min_ratio=0).evaluate("T", data).details
    assert "ratio" in NetDebtToEbitdaCondition(max_ratio=100).evaluate("T", data).details
    assert "ratio" in InterestCoverageRatioCondition(min_ratio=0).evaluate("T", data).details
    assert "ratio" in CashConversionRatioCondition(min_ratio=0).evaluate("T", data).details
    assert "roce_pct" in ROCEFilterCondition(min_roce_pct=-100).evaluate("T", data).details
    assert "roa_pct" in ROAFilterCondition(min_roa_pct=-100).evaluate("T", data).details


def test_missing_column_failsafe():
    data = _df().drop(columns=["revenue_3y_ago"])
    result = RevenueCAGR3YCondition().evaluate("T", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
