import pandas as pd

from utils.data_cache import OHLCVCache


def test_fetch_from_yfinance_returns_dataframe(monkeypatch, tmp_path):
    cache = OHLCVCache(cache_dir=str(tmp_path / "ohlcv"))

    sample = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [101.0, 102.0],
            "Low": [99.0, 100.0],
            "Close": [100.5, 101.5],
            "Volume": [1000, 1200],
        },
        index=pd.to_datetime(["2026-02-20", "2026-02-21"]),
    )

    class FakeTicker:
        def __init__(self, ticker: str):
            self.ticker = ticker

        def history(self, period: str):
            return sample

    import utils.data_cache as data_cache_module

    monkeypatch.setattr(data_cache_module, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(data_cache_module.yf, "Ticker", FakeTicker)

    df = cache._fetch_from_yfinance("AAPL", days=5)
    assert df is not None
    assert "close" in df.columns
    assert float(df["close"].iloc[-1]) == 101.5


def test_batch_fetch_merges_with_existing_parquet(monkeypatch, tmp_path):
    cache = OHLCVCache(cache_dir=str(tmp_path / "ohlcv"))
    cache_path = cache._get_cache_path("AAPL")
    store = {}

    def fake_to_parquet(df, path, *args, **kwargs):
        store[str(path)] = df.copy()

    def fake_read_parquet(path, *args, **kwargs):
        key = str(path)
        if key not in store:
            raise FileNotFoundError(key)
        return store[key].copy()

    # Existing historical parquet (older date)
    existing = pd.DataFrame(
        {
            "open": [95.0],
            "high": [96.0],
            "low": [94.0],
            "close": [95.5],
            "volume": [900],
            "ticker": ["AAPL"],
        },
        index=pd.to_datetime(["2026-02-19"]),
    )
    fake_to_parquet(existing, cache_path)

    # Batch download payload (newer date, MultiIndex column format)
    cols = pd.MultiIndex.from_product([["AAPL"], ["Open", "High", "Low", "Close", "Volume"]])
    downloaded = pd.DataFrame(
        [[100.0, 101.0, 99.0, 100.5, 1000]],
        index=pd.to_datetime(["2026-02-21"]),
        columns=cols,
    )

    import utils.data_cache as data_cache_module

    monkeypatch.setattr(data_cache_module, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(data_cache_module.yf, "download", lambda **kwargs: downloaded)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)
    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)

    # Force cache_path.exists() to track our in-memory store.
    monkeypatch.setattr(type(cache_path), "exists", lambda self: str(self) in store)

    prices = cache._fetch_latest_prices_batch(["AAPL"])
    assert prices["AAPL"] == 100.5

    merged = fake_read_parquet(cache_path)
    # Must preserve old row and append new row (no truncation).
    assert len(merged) == 2
    assert float(merged["close"].iloc[0]) == 95.5
    assert float(merged["close"].iloc[-1]) == 100.5
