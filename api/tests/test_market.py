"""
Tests for market data API endpoints.

Tests the market router endpoints including quotes, OHLCV data,
and technical indicators.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestQuoteEndpoint:
    """Tests for GET /api/market/quote/{ticker} endpoint."""

    def test_get_quote_valid_ticker(self, client):
        """Test GET /api/market/quote/{ticker} with valid ticker."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange
            mock_service.get_quote.return_value = {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "current_price": 175.50,
                "change": 2.30,
                "change_pct": 1.33,
                "volume": 50000000,
                "timestamp": "2026-02-12T10:00:00"
            }

            # Act
            response = client.get("/api/market/quote/AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "AAPL"
            assert data["current_price"] == 175.50
            assert data["change"] == 2.30
            assert data["change_pct"] == 1.33
            assert "volume" in data
            assert "timestamp" in data

    def test_get_quote_korean_ticker(self, client):
        """Test GET /api/market/quote/{ticker} with Korean stock ticker."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange
            mock_service.get_quote.return_value = {
                "ticker": "005930.KS",
                "name": "Samsung Electronics",
                "current_price": 70000.0,
                "change": 500.0,
                "change_pct": 0.72,
                "volume": 10000000,
                "timestamp": "2026-02-12T15:30:00"
            }

            # Act
            response = client.get("/api/market/quote/005930.KS")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "005930.KS"
            assert data["current_price"] == 70000.0

    def test_get_quote_invalid_ticker_returns_404(self, client):
        """Test GET /api/market/quote/{ticker} with invalid ticker returns 404."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange
            mock_service.get_quote.return_value = None

            # Act
            response = client.get("/api/market/quote/INVALIDTICKER123")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not available" in data["detail"]


class TestOHLCVEndpoint:
    """Tests for GET /api/market/ohlcv/{ticker} endpoint."""

    def test_get_ohlcv_default_days(self, client):
        """Test GET /api/market/ohlcv/{ticker} returns OHLCV data with default days."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange
            mock_service.get_ohlcv.return_value = {
                "ticker": "AAPL",
                "data": [
                    {
                        "date": "2026-02-11",
                        "open": 174.00,
                        "high": 176.00,
                        "low": 173.50,
                        "close": 175.50,
                        "volume": 50000000
                    },
                    {
                        "date": "2026-02-10",
                        "open": 172.00,
                        "high": 175.00,
                        "low": 171.50,
                        "close": 173.20,
                        "volume": 45000000
                    }
                ],
                "period_days": 2
            }

            # Act
            response = client.get("/api/market/ohlcv/AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "AAPL"
            assert "data" in data
            assert isinstance(data["data"], list)
            assert len(data["data"]) == 2
            assert "period_days" in data

    def test_get_ohlcv_with_days_parameter(self, client):
        """Test GET /api/market/ohlcv/{ticker} with custom days parameter."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange
            mock_service.get_ohlcv.return_value = {
                "ticker": "AAPL",
                "data": [{"date": "2026-02-11", "open": 174, "high": 176, "low": 173, "close": 175, "volume": 50000000}],
                "period_days": 30
            }

            # Act
            response = client.get("/api/market/ohlcv/AAPL?days=30")

            # Assert
            assert response.status_code == 200
            mock_service.get_ohlcv.assert_called_once_with("AAPL", days=30)

    def test_get_ohlcv_invalid_ticker_returns_404(self, client):
        """Test GET /api/market/ohlcv/{ticker} with invalid ticker returns 404."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange
            mock_service.get_ohlcv.return_value = None

            # Act
            response = client.get("/api/market/ohlcv/INVALIDTICKER")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    def test_get_ohlcv_days_validation_min(self, client):
        """Test GET /api/market/ohlcv/{ticker} validates minimum days parameter."""
        # Act - days must be >= 1
        response = client.get("/api/market/ohlcv/AAPL?days=0")

        # Assert
        assert response.status_code == 422  # Validation error

    def test_get_ohlcv_days_validation_max(self, client):
        """Test GET /api/market/ohlcv/{ticker} validates maximum days parameter."""
        # Act - days must be <= 730
        response = client.get("/api/market/ohlcv/AAPL?days=1000")

        # Assert
        assert response.status_code == 422  # Validation error


class TestTechnicalIndicatorsEndpoint:
    """Tests for GET /api/market/technical/{ticker} endpoint."""

    def test_get_technical_indicators(self, client):
        """Test GET /api/market/technical/{ticker} returns indicators."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange
            mock_service.get_technical_indicators.return_value = {
                "ticker": "AAPL",
                "rsi": 55.5,
                "rsi_signal": "neutral",
                "macd": 2.5,
                "macd_signal": 1.8,
                "macd_histogram": 0.7,
                "bb_upper": 180.0,
                "bb_middle": 175.0,
                "bb_lower": 170.0,
                "bb_position": "middle",
                "ma_20": 174.5,
                "ma_60": 172.0,
                "ma_120": 170.0,
                "ma_240": 165.0
            }

            # Act
            response = client.get("/api/market/technical/AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "AAPL"
            assert data["rsi"] == 55.5
            assert data["rsi_signal"] == "neutral"
            assert data["macd"] == 2.5
            assert data["bb_upper"] == 180.0
            assert data["ma_20"] == 174.5
            assert data["ma_240"] == 165.0

    def test_get_technical_indicators_with_partial_data(self, client):
        """Test GET /api/market/technical/{ticker} with partial data."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange - Some indicators may be None
            mock_service.get_technical_indicators.return_value = {
                "ticker": "NEWSTOCK",
                "rsi": 45.0,
                "rsi_signal": "neutral",
                "macd": None,  # Not enough data
                "macd_signal": None,
                "macd_histogram": None,
                "bb_upper": 50.0,
                "bb_middle": 48.0,
                "bb_lower": 46.0,
                "bb_position": "middle",
                "ma_20": 47.5,
                "ma_60": None,  # Not enough data
                "ma_120": None,
                "ma_240": None
            }

            # Act
            response = client.get("/api/market/technical/NEWSTOCK")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "NEWSTOCK"
            assert data["rsi"] == 45.0
            assert data["macd"] is None
            assert data["ma_240"] is None

    def test_get_technical_indicators_invalid_ticker_returns_404(self, client):
        """Test GET /api/market/technical/{ticker} with invalid ticker returns 404."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange
            mock_service.get_technical_indicators.return_value = None

            # Act
            response = client.get("/api/market/technical/INVALIDTICKER")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not available" in data["detail"]

    def test_get_technical_indicators_rsi_signals(self, client):
        """Test that RSI signal interpretation is correct."""
        with patch("api.routers.market._service") as mock_service:
            # Arrange - Oversold RSI
            mock_service.get_technical_indicators.return_value = {
                "ticker": "AAPL",
                "rsi": 25.0,
                "rsi_signal": "oversold",
                "macd": None,
                "macd_signal": None,
                "macd_histogram": None,
                "bb_upper": None,
                "bb_middle": None,
                "bb_lower": None,
                "bb_position": None,
                "ma_20": None,
                "ma_60": None,
                "ma_120": None,
                "ma_240": None
            }

            # Act
            response = client.get("/api/market/technical/AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["rsi_signal"] == "oversold"


class TestMacroEndpoints:
    """Tests for macro bundle/history endpoints."""

    def test_get_macro_bundle(self, client):
        with patch("api.routers.market._macro_service") as mock_macro_service, patch(
            "api.routers.market._bond_service"
        ) as mock_bond_service, patch("api.routers.market._volatility_service") as mock_vol_service:
            mock_macro_service.get_bundle.return_value = {
                "fx": {
                    "pair": "USD/KRW",
                    "value": 1340.5,
                    "change_pct": 0.12,
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "futures": {
                    "symbol": "069500.KS",
                    "value": 400.2,
                    "basis": 1.4,
                    "change_pct": -0.22,
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "flow": {
                    "market": "KOSPI",
                    "foreign_net": -1500000000.0,
                    "institution_net": 900000000.0,
                    "individual_net": 600000000.0,
                    "window_min": 5,
                    "updated_at": "2026-03-07T12:58:00+00:00",
                },
                "signal": {
                    "macro_score": 0.64,
                    "regime": "risk_off",
                    "reason": "risk_off: fx=0.80 (decay=1.00)",
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "freshness": {
                    "fx_age_sec": 5,
                    "futures_age_sec": 3,
                    "flow_age_sec": 120,
                },
            }
            mock_bond_service.get_snapshot.return_value = None
            mock_vol_service.get_snapshot.return_value = None

            response = client.get("/api/market/macro/bundle")

            assert response.status_code == 200
            payload = response.json()
            assert payload["fx"]["pair"] == "USD/KRW"
            assert payload["signal"]["regime"] == "risk_off"
            assert "freshness" in payload
            assert payload.get("bonds") is None
            assert payload.get("volatility") is None

    def test_get_macro_bundle_with_bonds(self, client):
        with patch("api.routers.market._macro_service") as mock_macro_service, patch(
            "api.routers.market._bond_service"
        ) as mock_bond_service, patch("api.routers.market._volatility_service") as mock_vol_service:
            mock_macro_service.get_bundle.return_value = {
                "fx": {
                    "pair": "USD/KRW",
                    "value": 1340.5,
                    "change_pct": 0.12,
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "futures": {
                    "symbol": "069500.KS",
                    "value": 400.2,
                    "basis": 1.4,
                    "change_pct": -0.22,
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "flow": {
                    "market": "KOSPI",
                    "foreign_net": -1500000000.0,
                    "institution_net": 900000000.0,
                    "individual_net": 600000000.0,
                    "window_min": 5,
                    "updated_at": "2026-03-07T12:58:00+00:00",
                },
                "signal": {
                    "macro_score": 0.64,
                    "regime": "risk_off",
                    "reason": "risk_off: fx=0.80 (decay=1.00)",
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "freshness": {
                    "fx_age_sec": 5,
                    "futures_age_sec": 3,
                    "flow_age_sec": 120,
                },
            }
            mock_bond_service.get_snapshot.return_value = {
                "us_10y": 4.10,
                "us_2y": 4.30,
                "us_spread_2_10": -0.20,
                "inverted": True,
                "kr_10y": 3.20,
                "kr_3y": 3.00,
                "kr_us_spread_10y": -0.90,
                "source_updated_at": "2026-03-10",
                "stale": False,
            }
            mock_vol_service.get_snapshot.return_value = None

            response = client.get("/api/market/macro/bundle")

            assert response.status_code == 200
            payload = response.json()
            assert payload["bonds"]["us_10y"] == 4.10
            assert payload["bonds"]["inverted"] is True
            assert payload["bonds"]["kr_us_spread_10y"] == -0.90
            assert payload.get("volatility") is None

    def test_get_macro_bundle_with_volatility(self, client):
        with patch("api.routers.market._macro_service") as mock_macro_service, patch(
            "api.routers.market._bond_service"
        ) as mock_bond_service, patch("api.routers.market._volatility_service") as mock_vol_service:
            mock_macro_service.get_bundle.return_value = {
                "fx": {
                    "pair": "USD/KRW",
                    "value": 1340.5,
                    "change_pct": 0.12,
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "futures": {
                    "symbol": "069500.KS",
                    "value": 400.2,
                    "basis": 1.4,
                    "change_pct": -0.22,
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "flow": {
                    "market": "KOSPI",
                    "foreign_net": -1500000000.0,
                    "institution_net": 900000000.0,
                    "individual_net": 600000000.0,
                    "window_min": 5,
                    "updated_at": "2026-03-07T12:58:00+00:00",
                },
                "signal": {
                    "macro_score": 0.64,
                    "regime": "risk_off",
                    "reason": "risk_off: fx=0.80 (decay=1.00)",
                    "updated_at": "2026-03-07T13:00:00+00:00",
                },
                "freshness": {
                    "fx_age_sec": 5,
                    "futures_age_sec": 3,
                    "flow_age_sec": 120,
                },
            }
            mock_bond_service.get_snapshot.return_value = None
            mock_vol_service.get_snapshot.return_value = {
                "vix": 21.3,
                "vix_change_pct": 2.51,
                "vix_as_of": "2026-03-11T20:59:00+00:00",
                "vkospi": 18.9,
                "vkospi_change_pct": -0.8,
                "vkospi_as_of": "2026-03-11T06:00:00+00:00",
                "fear_greed": "elevated",
                "vkospi_vix_ratio": 0.887,
            }

            response = client.get("/api/market/macro/bundle")

            assert response.status_code == 200
            payload = response.json()
            assert payload["volatility"]["vix"] == 21.3
            assert payload["volatility"]["fear_greed"] == "elevated"
            assert payload["volatility"]["vkospi_vix_ratio"] == 0.887

    def test_get_macro_history(self, client):
        with patch("api.routers.market._macro_service") as mock_macro_service:
            mock_macro_service.get_history.return_value = {
                "window": "60m",
                "points": [
                    {
                        "timestamp": "2026-03-07T12:50:00+00:00",
                        "fx_value": 1339.1,
                        "futures_value": 401.0,
                        "foreign_net": -1200000000.0,
                        "macro_score": 0.52,
                        "regime": "neutral",
                    }
                ],
            }

            response = client.get("/api/market/macro/history?window=60m")

            assert response.status_code == 200
            payload = response.json()
            assert payload["window"] == "60m"
            assert len(payload["points"]) == 1
            assert payload["points"][0]["regime"] == "neutral"
