from types import SimpleNamespace

import pandas as pd

from api.services.market_service import MarketService


def _sample_ohlcv(rows: int = 5) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "open": [100 + i for i in range(rows)],
            "high": [101 + i for i in range(rows)],
            "low": [99 + i for i in range(rows)],
            "close": [100 + i for i in range(rows)],
            "volume": [1000 + i for i in range(rows)],
        },
        index=idx,
    )


def test_get_quote_caches_ticker_name_lookup(monkeypatch):
    class FakeCache:
        def get(self, ticker: str, days: int = 5):
            return _sample_ohlcv(5)

    calls = {"count": 0}

    class FakeTicker:
        def __init__(self, ticker: str):
            calls["count"] += 1
            self.info = {"shortName": "Apple Inc."}

    fake_yf = SimpleNamespace(Ticker=FakeTicker)
    monkeypatch.setitem(__import__("sys").modules, "yfinance", fake_yf)

    MarketService._ticker_info_cache.clear()
    service = MarketService(cache=FakeCache())

    first = service.get_quote("AAPL")
    second = service.get_quote("AAPL")

    assert first is not None and first["name"] == "Apple Inc."
    assert second is not None and second["name"] == "Apple Inc."
    assert calls["count"] == 1


def test_get_ohlcv_uses_provided_data_without_cache_hit():
    class FakeCache:
        def __init__(self):
            self.calls = 0

        def get(self, ticker: str, days: int = 100):
            self.calls += 1
            return _sample_ohlcv(days)

    cache = FakeCache()
    service = MarketService(cache=cache)
    shared = _sample_ohlcv(8)

    result = service.get_ohlcv("AAPL", days=5, data=shared)

    assert result is not None
    assert result["period_days"] == 5
    assert len(result["data"]) == 5
    assert cache.calls == 0
