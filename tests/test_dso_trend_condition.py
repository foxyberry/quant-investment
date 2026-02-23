import pandas as pd

from screener.conditions.fundamental import DsoTrendFilterCondition
from screener.conditions.registry import get_condition_metadata


def _make_income(total_revenue_recent: float, total_revenue_past: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "2024": [total_revenue_recent],
            "2023": [total_revenue_past],
        },
        index=["Total Revenue"],
    )


def _make_balance(receivables_recent: float, receivables_past: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "2024": [receivables_recent],
            "2023": [receivables_past],
        },
        index=["Accounts Receivable"],
    )


def test_dso_trend_filter_matches_deterioration(monkeypatch):
    from screener.conditions import fundamental as fundamental_module

    income = _make_income(total_revenue_recent=365.0, total_revenue_past=365.0)
    balance = _make_balance(receivables_recent=120.0, receivables_past=100.0)
    cashflow = pd.DataFrame()
    monkeypatch.setattr(
        fundamental_module,
        "_get_financial_statements",
        lambda _ticker: (income, balance, cashflow),
    )

    cond = DsoTrendFilterCondition(lookback_years=1, min_dso_increase_pct=10.0)
    result = cond.evaluate("TEST", pd.DataFrame())

    assert result.matched is True
    assert result.details["dso_recent"] == 120.0
    assert result.details["dso_past"] == 100.0
    assert result.details["dso_change_pct"] == 20.0


def test_dso_trend_filter_not_matched_when_improving(monkeypatch):
    from screener.conditions import fundamental as fundamental_module

    income = _make_income(total_revenue_recent=365.0, total_revenue_past=365.0)
    balance = _make_balance(receivables_recent=90.0, receivables_past=100.0)
    cashflow = pd.DataFrame()
    monkeypatch.setattr(
        fundamental_module,
        "_get_financial_statements",
        lambda _ticker: (income, balance, cashflow),
    )

    cond = DsoTrendFilterCondition(lookback_years=1, min_dso_increase_pct=5.0)
    result = cond.evaluate("TEST", pd.DataFrame())

    assert result.matched is False
    assert result.details["dso_change_pct"] < 0


def test_dso_trend_filter_handles_missing_data(monkeypatch):
    from screener.conditions import fundamental as fundamental_module

    income = pd.DataFrame({"2024": [365.0]}, index=["Total Revenue"])
    balance = pd.DataFrame({"2024": [120.0]}, index=["Accounts Receivable"])
    cashflow = pd.DataFrame()
    monkeypatch.setattr(
        fundamental_module,
        "_get_financial_statements",
        lambda _ticker: (income, balance, cashflow),
    )

    cond = DsoTrendFilterCondition(lookback_years=1, min_dso_increase_pct=5.0)
    result = cond.evaluate("TEST", pd.DataFrame())

    assert result.matched is False
    assert "error" in result.details


def test_dso_trend_filter_registered_metadata():
    metadata = get_condition_metadata()
    assert "dso_trend_filter" in metadata
    assert metadata["dso_trend_filter"]["category"] == "Fundamental"
