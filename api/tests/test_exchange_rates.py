"""
Tests for exchange rates API endpoint.
"""

from datetime import datetime, timezone
from unittest.mock import patch


class TestExchangeRatesEndpoint:
    """Tests for GET /api/exchange-rates."""

    def test_get_exchange_rates_default_base(self, client):
        with patch("api.routers.exchange_rates.get_exchange_rate_service") as mock_factory:
            mock_service = mock_factory.return_value
            mock_service.get_rates.return_value = {
                "base": "USD",
                "rates": {"KRW": 1350.5, "JPY": 149.8},
                "updated_at": datetime.now(timezone.utc),
            }

            response = client.get("/api/exchange-rates")

            assert response.status_code == 200
            data = response.json()
            assert data["base"] == "USD"
            assert "KRW" in data["rates"]
            mock_service.get_rates.assert_called_once_with(base="USD")

    def test_get_exchange_rates_custom_base(self, client):
        with patch("api.routers.exchange_rates.get_exchange_rate_service") as mock_factory:
            mock_service = mock_factory.return_value
            mock_service.get_rates.return_value = {
                "base": "SGD",
                "rates": {"USD": 0.74, "KRW": 996.0},
                "updated_at": datetime.now(timezone.utc),
            }

            response = client.get("/api/exchange-rates?base=sgd")

            assert response.status_code == 200
            assert response.json()["base"] == "SGD"
            mock_service.get_rates.assert_called_once_with(base="sgd")

    def test_get_exchange_rates_upstream_unavailable(self, client):
        with patch("api.routers.exchange_rates.get_exchange_rate_service") as mock_factory:
            mock_service = mock_factory.return_value
            mock_service.get_rates.side_effect = RuntimeError("Exchange rate unavailable for base USD")

            response = client.get("/api/exchange-rates")

            assert response.status_code == 503
            assert "Exchange rate unavailable" in response.json()["detail"]
