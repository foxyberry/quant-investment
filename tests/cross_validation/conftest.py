"""Fixtures for cross-validation tests."""

import os

import pytest
import pandas as pd


# Tickers to cross-validate: 1 US, 1 KR
CROSS_VALIDATE_TICKERS = [
    ("AAPL", "US"),
    ("005930.KS", "KR"),
]

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_csv_fixture(ticker: str) -> pd.DataFrame:
    """Load static CSV fixture for a ticker."""
    safe_name = ticker.replace(".", "_")
    path = os.path.join(FIXTURES_DIR, f"{safe_name}.csv")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [c.lower() for c in df.columns]
    return df


@pytest.fixture(scope="session", params=CROSS_VALIDATE_TICKERS, ids=lambda t: t[0])
def ticker_data(request) -> tuple:
    """Load OHLCV data from static CSV fixtures.

    Returns:
        (ticker, market, DataFrame) with columns: open, high, low, close, volume
    """
    ticker, market = request.param
    df = _load_csv_fixture(ticker)
    assert len(df) >= 60, f"Need >=60 rows for {ticker}, got {len(df)}"
    return ticker, market, df


@pytest.fixture(scope="session", params=CROSS_VALIDATE_TICKERS, ids=lambda t: t[0])
def ticker_data_live(request) -> tuple:
    """Fetch live OHLCV data via yfinance (integration test).

    Returns:
        (ticker, market, DataFrame) with columns: open, high, low, close, volume
    """
    import yfinance as yf

    ticker, market = request.param
    df = yf.download(ticker, period="1y", auto_adjust=True, progress=False)
    if df.empty:
        pytest.skip(f"No data for {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [c.lower() for c in df.columns]
    assert len(df) >= 60, f"Need >=60 rows for {ticker}, got {len(df)}"
    return ticker, market, df
