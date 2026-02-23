from types import SimpleNamespace

import pandas as pd

from screener.conditions import fundamental as fundamental_module
from utils.fundamental_cache import FundamentalCache
from api.services import strategy_service


def test_get_info_uses_persistent_cache(monkeypatch, tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "fund_cache"))
    monkeypatch.setattr(fundamental_module, "_persistent_cache", cache)
    fundamental_module.clear_info_cache()

    calls = {"count": 0}

    class FakeTicker:
        def __init__(self, ticker: str):
            calls["count"] += 1
            self.info = {"trailingPE": 10.5, "ticker": ticker}

    monkeypatch.setattr(fundamental_module.yf, "Ticker", FakeTicker)

    first = fundamental_module._get_info("AAPL")
    assert first["trailingPE"] == 10.5
    assert calls["count"] == 1

    # Clear only in-memory cache; second call should come from persistent cache.
    fundamental_module.clear_info_cache()

    class FailTicker:
        def __init__(self, ticker: str):
            raise AssertionError("yfinance should not be called when persistent cache is warm")

    monkeypatch.setattr(fundamental_module.yf, "Ticker", FailTicker)
    second = fundamental_module._get_info("AAPL")
    assert second["trailingPE"] == 10.5


def test_get_financial_statements_uses_persistent_cache(monkeypatch, tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "stmt_cache"))
    monkeypatch.setattr(fundamental_module, "_persistent_cache", cache)
    fundamental_module.clear_info_cache()

    income_df = pd.DataFrame({"2025": [100.0]}, index=["Net Income"])
    balance_df = pd.DataFrame({"2025": [1000.0]}, index=["Total Assets"])
    cashflow_df = pd.DataFrame({"2025": [120.0]}, index=["Operating Cash Flow"])

    calls = {"count": 0}

    class FakeTicker:
        def __init__(self, ticker: str):
            calls["count"] += 1
            self.income_stmt = income_df
            self.balance_sheet = balance_df
            self.cashflow = cashflow_df
            self.info = {}

    monkeypatch.setattr(fundamental_module.yf, "Ticker", FakeTicker)

    income, balance, cashflow = fundamental_module._get_financial_statements("MSFT")
    assert float(income.loc["Net Income"].iloc[0]) == 100.0
    assert float(balance.loc["Total Assets"].iloc[0]) == 1000.0
    assert float(cashflow.loc["Operating Cash Flow"].iloc[0]) == 120.0
    assert calls["count"] == 1

    # Clear in-memory caches; second call should deserialize persisted payload.
    fundamental_module.clear_info_cache()

    class FailTicker:
        def __init__(self, ticker: str):
            raise AssertionError("yfinance should not be called when statement cache is warm")

    monkeypatch.setattr(fundamental_module.yf, "Ticker", FailTicker)
    income2, balance2, cashflow2 = fundamental_module._get_financial_statements("MSFT")
    assert float(income2.loc["Net Income"].iloc[0]) == 100.0
    assert float(balance2.loc["Total Assets"].iloc[0]) == 1000.0
    assert float(cashflow2.loc["Operating Cash Flow"].iloc[0]) == 120.0


def test_fetch_us_fundamentals_uses_persistent_cache(monkeypatch, tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "us_fund_cache"))
    monkeypatch.setattr(strategy_service, "_fundamental_cache", cache)

    calls = {"count": 0}

    class FakeYFTicker:
        def __init__(self, ticker: str):
            calls["count"] += 1
            self.info = {"trailingPE": 22.0, "priceToBook": 4.0, "dividendYield": 0.02}

    class FakeYFTickers:
        def __init__(self, joined: str):
            self.tickers = {}

    fake_yf = SimpleNamespace(Ticker=FakeYFTicker, Tickers=FakeYFTickers)
    monkeypatch.setitem(__import__("sys").modules, "yfinance", fake_yf)

    first = strategy_service._fetch_us_fundamentals(["AAPL"])
    assert first["AAPL"]["per"] == 22.0
    assert calls["count"] == 1

    # Second call should hit persistent cache and avoid yfinance.
    second = strategy_service._fetch_us_fundamentals(["AAPL"])
    assert second["AAPL"]["per"] == 22.0
    assert calls["count"] == 1
