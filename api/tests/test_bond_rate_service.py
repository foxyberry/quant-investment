"""Tests for FRED/ECOS clients and bond rate aggregation service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api.services.bond_rate_service import BondRateService
from api.services.ecos_service import EcosService
from api.services.fred_service import FredService


def test_fred_service_returns_none_without_api_key():
    with patch.dict("os.environ", {}, clear=True):
        svc = FredService()
        with patch("api.services.fred_service.requests.get") as mock_get:
            assert svc.get_series("DGS10") is None
            mock_get.assert_not_called()


def test_fred_service_returns_latest_value_from_response():
    with patch.dict("os.environ", {"FRED_API_KEY": "test-key"}, clear=True):
        svc = FredService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": [{"value": "4.21", "date": "2026-03-10"}],
        }
        mock_response.raise_for_status.return_value = None

        with patch("api.services.fred_service.requests.get", return_value=mock_response) as mock_get:
            value = svc.get_series("DGS10")

        assert value == 4.21
        mock_get.assert_called_once()


def test_fred_service_skips_dot_values():
    """FRED uses '.' for missing data — should skip to next valid observation."""
    with patch.dict("os.environ", {"FRED_API_KEY": "test-key"}, clear=True):
        svc = FredService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": [
                {"value": ".", "date": "2026-03-10"},
                {"value": "4.15", "date": "2026-03-07"},
            ],
        }
        mock_response.raise_for_status.return_value = None

        with patch("api.services.fred_service.requests.get", return_value=mock_response):
            value = svc.get_series("DGS10")

        assert value == 4.15


def test_fred_service_returns_observation_date():
    with patch.dict("os.environ", {"FRED_API_KEY": "test-key"}, clear=True):
        svc = FredService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": [{"value": "4.21", "date": "2026-03-10"}],
        }
        mock_response.raise_for_status.return_value = None

        with patch("api.services.fred_service.requests.get", return_value=mock_response):
            value, obs_date = svc.get_series_with_date("DGS10")

        assert value == 4.21
        assert obs_date == "2026-03-10"


def test_ecos_service_returns_none_without_api_key():
    with patch.dict("os.environ", {}, clear=True):
        svc = EcosService()
        with patch("api.services.ecos_service.requests.get") as mock_get:
            assert svc.get_stat_value("817Y002", "010210000") is None
            mock_get.assert_not_called()


def test_bond_rate_service_returns_snapshot():
    fred = MagicMock()
    fred.get_series_with_date.return_value = (4.10, "2026-03-10")
    fred.get_series.side_effect = lambda s: {
        "DGS2": 4.30,
        "T10Y2Y": -0.20,
    }.get(s)
    ecos = MagicMock()
    ecos.get_stat_value.side_effect = lambda stat, item: {
        ("817Y002", "010210000"): 3.20,
        ("817Y002", "010200000"): 3.00,
    }.get((stat, item))

    service = BondRateService(fred=fred, ecos=ecos)
    snapshot = service.get_snapshot()

    assert snapshot["us_10y"] == 4.10
    assert snapshot["us_2y"] == 4.30
    assert snapshot["us_spread_2_10"] == -0.20
    assert snapshot["inverted"] is True
    assert snapshot["kr_10y"] == 3.20
    assert snapshot["kr_3y"] == 3.00
    assert snapshot["kr_us_spread_10y"] == pytest.approx(-0.9)
    assert snapshot["source_updated_at"] == "2026-03-10"
    assert snapshot["stale"] is False


def test_bond_rate_service_is_null_safe_on_partial_failures():
    fred = MagicMock()
    fred.get_series_with_date.return_value = (None, None)
    fred.get_series.side_effect = lambda s: {
        "DGS2": 4.30,
        "T10Y2Y": None,
    }.get(s)
    ecos = MagicMock()
    ecos.get_stat_value.side_effect = lambda stat, item: {
        ("817Y002", "010210000"): 3.20,
        ("817Y002", "010200000"): None,
    }.get((stat, item))

    service = BondRateService(fred=fred, ecos=ecos)
    snapshot = service.get_snapshot()

    assert snapshot["us_10y"] is None
    assert snapshot["kr_3y"] is None
    assert snapshot["kr_us_spread_10y"] is None
    assert snapshot["inverted"] is None
    assert snapshot["stale"] is False  # kr_10y and us_2y are not None


def test_bond_rate_service_stale_when_all_none():
    fred = MagicMock()
    fred.get_series_with_date.return_value = (None, None)
    fred.get_series.return_value = None
    ecos = MagicMock()
    ecos.get_stat_value.return_value = None

    service = BondRateService(fred=fred, ecos=ecos)
    snapshot = service.get_snapshot()

    assert snapshot["stale"] is True


def test_bond_rate_service_inverted_flag_false_when_spread_positive():
    fred = MagicMock()
    fred.get_series_with_date.return_value = (4.10, "2026-03-10")
    fred.get_series.side_effect = lambda s: {
        "DGS2": 3.90,
        "T10Y2Y": 0.20,
    }.get(s)
    ecos = MagicMock()
    ecos.get_stat_value.side_effect = lambda stat, item: {
        ("817Y002", "010210000"): 3.20,
        ("817Y002", "010200000"): 3.00,
    }.get((stat, item))

    service = BondRateService(fred=fred, ecos=ecos)
    snapshot = service.get_snapshot()

    assert snapshot["inverted"] is False
