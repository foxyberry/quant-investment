import numpy as np
import pandas as pd

from screener.conditions.quant_fundamental_batch8 import (
    ReceivablesTurnoverRatioCondition,
    InventoryTurnoverRatioCondition,
    AssetTurnoverRatioCondition,
    CashflowToDebtRatioCondition,
    PriceToTangibleBookCondition,
    EVToSalesRatioCondition,
    EVToEbitdaRatioCondition,
    BookToMarketRatioCondition,
    EPSCAGR3YCondition,
    EPSGrowthYoYCondition,
)
from screener.conditions.registry import get_condition_metadata


def _df(n=80):
    idx = pd.bdate_range("2025-01-02", periods=n)
    base = pd.Series(np.linspace(100, 130, n), index=idx)
    return pd.DataFrame(
        {
            "open": base * 0.99,
            "high": base * 1.01,
            "low": base * 0.98,
            "close": base,
            "volume": np.linspace(1_000_000, 1_500_000, n),
            "revenue_ttm": np.full(n, 10_000_000.0),
            "receivables": np.full(n, 1_500_000.0),
            "cogs_ttm": np.full(n, 6_000_000.0),
            "inventory": np.full(n, 1_000_000.0),
            "total_assets": np.full(n, 15_000_000.0),
            "operating_cash_flow_ttm": np.full(n, 2_500_000.0),
            "total_debt": np.full(n, 5_000_000.0),
            "market_cap": np.full(n, 20_000_000.0),
            "tangible_book_value": np.full(n, 8_000_000.0),
            "enterprise_value": np.full(n, 22_000_000.0),
            "ebitda_ttm": np.full(n, 3_000_000.0),
            "book_value": np.full(n, 9_000_000.0),
            "eps_ttm": np.full(n, 4.0),
            "eps_3y_ago": np.full(n, 2.5),
            "eps_prev_year": np.full(n, 3.2),
        },
        index=idx,
    )


def test_quant_fundamental_batch8_keys_registered():
    keys = set(get_condition_metadata().keys())
    expected = {
        "receivables_turnover_ratio",
        "inventory_turnover_ratio",
        "asset_turnover_ratio",
        "cashflow_to_debt_ratio",
        "price_to_tangible_book",
        "ev_to_sales_ratio",
        "ev_to_ebitda_ratio",
        "book_to_market_ratio",
        "eps_cagr_3y",
        "eps_growth_yoy",
    }
    assert expected.issubset(keys)


def test_quant_fundamental_batch8_conditions_compute():
    data = _df()
    assert "ratio" in ReceivablesTurnoverRatioCondition(min_ratio=0).evaluate("T", data).details
    assert "ratio" in InventoryTurnoverRatioCondition(min_ratio=0).evaluate("T", data).details
    assert "ratio" in AssetTurnoverRatioCondition(min_ratio=0).evaluate("T", data).details
    assert "ratio" in CashflowToDebtRatioCondition(min_ratio=0).evaluate("T", data).details
    assert "ratio" in PriceToTangibleBookCondition(max_ratio=100).evaluate("T", data).details
    assert "ratio" in EVToSalesRatioCondition(max_ratio=100).evaluate("T", data).details
    assert "ratio" in EVToEbitdaRatioCondition(max_ratio=100).evaluate("T", data).details
    assert "ratio" in BookToMarketRatioCondition(min_ratio=0).evaluate("T", data).details
    assert "cagr_pct" in EPSCAGR3YCondition(min_cagr_pct=-100).evaluate("T", data).details
    assert "growth_pct" in EPSGrowthYoYCondition(min_growth_pct=-100).evaluate("T", data).details


def test_missing_fundamental_columns_failsafe():
    data = _df().drop(columns=["enterprise_value"])
    result = EVToSalesRatioCondition().evaluate("T", data)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
