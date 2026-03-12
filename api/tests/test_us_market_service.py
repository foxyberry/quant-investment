"""Tests for US market snapshot service (S&P 500 + Fed Funds Rate)."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from api.services.us_market_service import UsMarketService


def test_fetch_sp500_from_history():
    service = UsMarketService()
    hist = pd.DataFrame(
        {"Close": [5100.0, 5200.0]},
        index=pd.to_datetime(["2026-03-10", "2026-03-11"]),
    )
    fake_ticker = SimpleNamespace(fast_info={}, history=lambda period: hist)
    fake_yf = SimpleNamespace(Ticker=lambda symbol: fake_ticker)

    with patch.dict(sys.modules, {"yfinance": fake_yf}):
        value, change_pct, as_of = service._fetch_sp500()

    assert value == 5200.0
    assert change_pct == round(((5200.0 - 5100.0) / 5100.0) * 100.0, 4)
    assert as_of == "2026-03-11T00:00:00"


def test_get_snapshot_returns_both_sp500_and_fed_rate():
    service = UsMarketService()

    with (
        patch.object(service, "_fetch_sp500", return_value=(5200.0, 1.9608, "2026-03-11")),
        patch.object(service, "_fetch_fed_funds_rate", return_value=(5.33, "2026-03-10")),
    ):
        snapshot = service.get_snapshot()

    assert snapshot["sp500_value"] == 5200.0
    assert snapshot["sp500_change_pct"] == 1.9608
    assert snapshot["sp500_as_of"] == "2026-03-11"
    assert snapshot["fed_funds_rate"] == 5.33
    assert snapshot["fed_funds_as_of"] == "2026-03-10"


def test_snapshot_cache_ttl():
    service = UsMarketService()

    # get_snapshot() calls time.monotonic() exactly once per invocation.
    # now=100 → cache miss (fetch), now=150 → cache hit (150-100=50 < 300), now=450 → cache miss (450-100=350 >= 300)
    with (
        patch("api.services.us_market_service.time.monotonic", side_effect=[100.0, 150.0, 450.0]),
        patch.object(service, "_get_cache_ttl", return_value=300),
        patch.object(service, "_fetch_sp500", return_value=(5200.0, 1.0, "2026-03-11")) as mock_sp500,
        patch.object(service, "_fetch_fed_funds_rate", return_value=(5.33, "2026-03-10")) as mock_fed,
    ):
        first = service.get_snapshot()
        second = service.get_snapshot()
        third = service.get_snapshot()

    assert first == second
    assert third == first
    assert mock_sp500.call_count == 2
    assert mock_fed.call_count == 2


def test_null_safe_when_yfinance_fails():
    service = UsMarketService()

    # Simulate yfinance import failure: _fetch_sp500 returns all None
    with (
        patch.object(service, "_fetch_sp500", return_value=(None, None, None)),
        patch.object(service, "_fetch_fed_funds_rate", return_value=(5.33, "2026-03-10")),
    ):
        snapshot = service.get_snapshot()

    assert snapshot["sp500_value"] is None
    assert snapshot["sp500_change_pct"] is None
    assert snapshot["sp500_as_of"] is None
    # Fed rate still comes through cleanly
    assert snapshot["fed_funds_rate"] == 5.33
    assert snapshot["fed_funds_as_of"] == "2026-03-10"
