"""Tests for VIX/VKOSPI volatility aggregation service."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from api.services.volatility_service import VolatilityService


def test_fetch_vix_snapshot_from_fast_info_and_history():
    service = VolatilityService()
    hist = pd.DataFrame(
        {"Close": [19.0, 20.0]},
        index=pd.to_datetime(["2026-03-10", "2026-03-11"]),
    )
    fake_ticker = SimpleNamespace(fast_info={"lastPrice": 20.5}, history=lambda period: hist)
    fake_yf = SimpleNamespace(Ticker=lambda symbol: fake_ticker)

    with patch.dict(sys.modules, {"yfinance": fake_yf}):
        vix, change, as_of = service._fetch_vix()

    assert vix == 20.5
    assert change == 5.2632
    assert as_of == "2026-03-11T00:00:00"


def test_fetch_vkospi_snapshot_with_primary_and_range_change():
    service = VolatilityService()
    today_df = pd.DataFrame(
        {"종가": [30.0]},
        index=pd.to_datetime(["2026-03-11"]),
    )
    range_df = pd.DataFrame(
        {"종가": [28.0, 30.0]},
        index=pd.to_datetime(["2026-03-10", "2026-03-11"]),
    )

    def fake_get_index_ohlcv_by_date(fromdate, todate, ticker, **kwargs):
        if fromdate == todate:
            return today_df
        return range_df

    fake_stock = SimpleNamespace(get_index_ohlcv_by_date=fake_get_index_ohlcv_by_date)
    fake_pykrx = SimpleNamespace(stock=fake_stock)

    with patch.dict(sys.modules, {"pykrx": fake_pykrx}):
        vkospi, change, as_of = service._fetch_vkospi()

    assert vkospi == 30.0
    assert change == 7.1429
    assert as_of == "2026-03-11T00:00:00"


def test_get_snapshot_is_null_safe_on_partial_failures():
    service = VolatilityService()
    with (
        patch.object(service, "_fetch_vix", return_value=(None, None, None)),
        patch.object(service, "_fetch_vkospi", return_value=(24.0, 1.25, "2026-03-11")),
    ):
        snapshot = service.get_snapshot()

    assert snapshot["vix"] is None
    assert snapshot["vkospi"] == 24.0
    assert snapshot["fear_greed"] is None
    assert snapshot["vkospi_vix_ratio"] is None


def test_classify_fear_greed_thresholds():
    service = VolatilityService()

    assert service._classify_fear_greed(14.99) == "low_vol"
    assert service._classify_fear_greed(15.0) == "normal"
    assert service._classify_fear_greed(19.99) == "normal"
    assert service._classify_fear_greed(20.0) == "elevated"
    assert service._classify_fear_greed(24.99) == "elevated"
    assert service._classify_fear_greed(25.0) == "high"
    assert service._classify_fear_greed(29.99) == "high"
    assert service._classify_fear_greed(30.0) == "extreme"


def test_vkospi_vix_ratio_guard_for_zero_and_none():
    service = VolatilityService()

    with (
        patch.object(service, "_fetch_vix", return_value=(20.0, None, "2026-03-11")),
        patch.object(service, "_fetch_vkospi", return_value=(30.0, None, "2026-03-11")),
    ):
        snapshot = service.get_snapshot()
    assert snapshot["vkospi_vix_ratio"] == 1.5

    service = VolatilityService()
    with (
        patch.object(service, "_fetch_vix", return_value=(0.0, None, "2026-03-11")),
        patch.object(service, "_fetch_vkospi", return_value=(30.0, None, "2026-03-11")),
    ):
        snapshot = service.get_snapshot()
    assert snapshot["vkospi_vix_ratio"] is None

    service = VolatilityService()
    with (
        patch.object(service, "_fetch_vix", return_value=(None, None, None)),
        patch.object(service, "_fetch_vkospi", return_value=(30.0, None, "2026-03-11")),
    ):
        snapshot = service.get_snapshot()
    assert snapshot["vkospi_vix_ratio"] is None


def test_snapshot_cache_ttl_with_monotonic_clock():
    service = VolatilityService()

    with (
        patch("api.services.volatility_service.time.monotonic", side_effect=[100.0, 150.0, 450.0]),
        patch.object(service, "_get_cache_ttl", return_value=300),
        patch.object(service, "_fetch_vix", return_value=(20.0, 1.0, "2026-03-11")) as mock_vix,
        patch.object(service, "_fetch_vkospi", return_value=(30.0, 2.0, "2026-03-11")) as mock_vkospi,
    ):
        first = service.get_snapshot()
        second = service.get_snapshot()
        third = service.get_snapshot()

    assert first == second
    assert third == first
    assert mock_vix.call_count == 2
    assert mock_vkospi.call_count == 2
