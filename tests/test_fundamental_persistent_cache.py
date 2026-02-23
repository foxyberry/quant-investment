import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
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


def test_clear_info_cache_with_persistent_option(monkeypatch, tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "clear_cache"))
    monkeypatch.setattr(fundamental_module, "_persistent_cache", cache)
    fundamental_module.clear_info_cache()

    cache.set("yf_info", "AAPL", {"trailingPE": 9.5})
    assert cache.get("yf_info", "AAPL", ttl_seconds=3600) is not None

    fundamental_module.clear_info_cache(include_persistent=True)
    assert cache.get("yf_info", "AAPL", ttl_seconds=3600) is None


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
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    first = strategy_service._fetch_us_fundamentals(["AAPL"])
    assert first["AAPL"]["per"] == 22.0
    assert calls["count"] == 1

    # Second call should hit persistent cache and avoid yfinance.
    second = strategy_service._fetch_us_fundamentals(["AAPL"])
    assert second["AAPL"]["per"] == 22.0
    assert calls["count"] == 1


def test_fetch_us_fundamentals_failure_not_cached(monkeypatch, tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "us_fund_cache_fail"))
    monkeypatch.setattr(strategy_service, "_fundamental_cache", cache)

    calls = {"count": 0}

    class FlakyYFTicker:
        def __init__(self, ticker: str):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary yfinance outage")
            self.info = {"trailingPE": 18.0, "priceToBook": 3.5, "dividendYield": 0.01}

    class FakeYFTickers:
        def __init__(self, joined: str):
            self.tickers = {}

    fake_yf = SimpleNamespace(Ticker=FlakyYFTicker, Tickers=FakeYFTickers)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    first = strategy_service._fetch_us_fundamentals(["MSFT"])
    assert first["MSFT"]["per"] is None
    assert calls["count"] == 1

    # Must re-fetch (not cached as None), and then succeed.
    second = strategy_service._fetch_us_fundamentals(["MSFT"])
    assert second["MSFT"]["per"] == 18.0
    assert calls["count"] == 2


def test_fetch_kr_fundamentals_uses_persistent_cache(monkeypatch, tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "kr_fund_cache"))
    monkeypatch.setattr(strategy_service, "_fundamental_cache", cache)

    calls = {"count": 0}

    def fake_get_market_fundamental_by_ticker(date: str, market: str):
        calls["count"] += 1
        return pd.DataFrame(
            {"PER": [11.0], "PBR": [0.9], "DIV": [2.2]},
            index=["005930"],
        )

    fake_pykrx_stock = SimpleNamespace(get_market_fundamental_by_ticker=fake_get_market_fundamental_by_ticker)
    fake_pykrx = SimpleNamespace(stock=fake_pykrx_stock)
    monkeypatch.setitem(sys.modules, "pykrx", fake_pykrx)

    first = strategy_service._fetch_kr_fundamentals(["005930.KS"])
    assert first["005930.KS"]["per"] == 11.0
    assert calls["count"] >= 1

    # Second call should hit cache and avoid pykrx function invocation.
    calls_before = calls["count"]
    second = strategy_service._fetch_kr_fundamentals(["005930.KS"])
    assert second["005930.KS"]["pbr"] == 0.9
    assert calls["count"] == calls_before


def test_fundamental_cache_ttl_expiry_and_corrupt_file(tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "ttl_cache"))
    cache.set("ns", "AAPL", {"per": 10.0})
    assert cache.get("ns", "AAPL", ttl_seconds=3600) == {"per": 10.0}
    assert cache.get("ns", "AAPL", ttl_seconds=0) is None

    bad_path = tmp_path / "ttl_cache" / "ns__MSFT.json"
    bad_path.write_text("{not-json}", encoding="utf-8")
    assert cache.get("ns", "MSFT", ttl_seconds=3600) is None

    stale_path = tmp_path / "ttl_cache" / "ns__GOOG.json"
    stale_path.write_text(
        json.dumps({"_updated_at": "2000-01-01T00:00:00+00:00", "payload": {"per": 9.0}}),
        encoding="utf-8",
    )
    removed = cache.clear_expired(ttl_seconds=60, namespace="ns")
    assert removed >= 1


def test_fundamental_cache_get_or_set_deduplicates_concurrent_loaders(tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "dedupe_cache"))
    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        time.sleep(0.05)
        return {"per": 12.3}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(cache.get_or_set, "ns", "AAPL", 3600, loader)
            for _ in range(5)
        ]
        results = [future.result() for future in futures]

    assert calls["count"] == 1
    assert all(result == {"per": 12.3} for result in results)


def test_get_info_concurrent_calls_use_single_yfinance_lookup(monkeypatch, tmp_path):
    cache = FundamentalCache(cache_dir=str(tmp_path / "info_lock_cache"))
    monkeypatch.setattr(fundamental_module, "_persistent_cache", cache)
    fundamental_module.clear_info_cache(include_persistent=True)

    calls = {"count": 0}

    class SlowTicker:
        def __init__(self, ticker: str):
            calls["count"] += 1
            time.sleep(0.05)
            self.info = {"trailingPE": 13.0, "ticker": ticker}

    monkeypatch.setattr(fundamental_module.yf, "Ticker", SlowTicker)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fundamental_module._get_info, "AAPL") for _ in range(5)]
        results = [future.result() for future in futures]

    assert calls["count"] == 1
    assert all(result.get("trailingPE") == 13.0 for result in results)
