import numpy as np
import pandas as pd

from screener.conditions.quant_shareholder_batch10 import (
    NetMarginCondition,
    GrossMarginCondition,
    OperatingMarginCondition,
    FreeCashFlowMarginCondition,
    PayoutRatioFilterCondition,
    DividendGrowth5YCondition,
    ShareholderYieldFilterCondition,
    NetShareIssuanceFilterCondition,
    BuybackYieldFilterCondition,
    InsiderNetBuyingCondition,
)
from screener.conditions.registry import get_condition_metadata


def _df(n=60):
    idx = pd.bdate_range("2025-01-02", periods=n)
    base = pd.Series(np.linspace(80, 110, n), index=idx)
    return pd.DataFrame(
        {
            "open": base * 0.99,
            "high": base * 1.01,
            "low": base * 0.98,
            "close": base,
            "volume": np.linspace(800_000, 1_300_000, n),
            "net_income_ttm": np.full(n, 1_200_000.0),
            "revenue_ttm": np.full(n, 10_000_000.0),
            "gross_profit_ttm": np.full(n, 3_500_000.0),
            "operating_income_ttm": np.full(n, 1_700_000.0),
            "free_cash_flow_ttm": np.full(n, 1_100_000.0),
            "dividends_paid_ttm": np.full(n, -400_000.0),
            "dividend_per_share_ttm": np.full(n, 1.25),
            "dividend_per_share_5y_ago": np.full(n, 0.9),
            "dividend_yield_pct": np.full(n, 2.0),
            "buyback_yield_pct": np.full(n, 1.5),
            "net_share_issuance_pct": np.full(n, 0.5),
            "insider_net_buying_pct": np.full(n, 0.8),
        },
        index=idx,
    )


def test_quant_shareholder_batch10_keys_registered():
    keys = set(get_condition_metadata().keys())
    expected = {
        "net_margin",
        "gross_margin",
        "operating_margin",
        "free_cash_flow_margin",
        "payout_ratio_filter",
        "dividend_growth_5y",
        "shareholder_yield_filter",
        "net_share_issuance_filter",
        "buyback_yield_filter",
        "insider_net_buying",
    }
    assert expected.issubset(keys)


def test_quant_shareholder_batch10_conditions_compute():
    data = _df()
    assert "margin_pct" in NetMarginCondition(min_margin_pct=0).evaluate("T", data).details
    assert "margin_pct" in GrossMarginCondition(min_margin_pct=0).evaluate("T", data).details
    assert "margin_pct" in OperatingMarginCondition(min_margin_pct=0).evaluate("T", data).details
    assert "margin_pct" in FreeCashFlowMarginCondition(min_margin_pct=0).evaluate("T", data).details
    assert "payout_pct" in PayoutRatioFilterCondition(max_payout_pct=100).evaluate("T", data).details
    assert "growth_pct" in DividendGrowth5YCondition(min_growth_pct=-100).evaluate("T", data).details
    assert "shareholder_yield_pct" in ShareholderYieldFilterCondition(min_yield_pct=-100).evaluate("T", data).details
    assert "issuance_pct" in NetShareIssuanceFilterCondition(max_issuance_pct=100).evaluate("T", data).details
    assert "buyback_yield_pct" in BuybackYieldFilterCondition(min_yield_pct=-100).evaluate("T", data).details
    assert "net_buying_pct" in InsiderNetBuyingCondition(min_net_buying_pct=-100).evaluate("T", data).details


def test_missing_column_failsafe():
    data = _df().drop(columns=["revenue_ttm"])
    result = NetMarginCondition().evaluate("T", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
