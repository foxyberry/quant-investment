"""
Tests for screening API endpoints.

Tests the screening router endpoints including presets, universes,
and screening operations.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestScreeningPresets:
    """Tests for GET /api/screening/presets endpoint."""

    def test_get_presets_returns_list(self, client, mock_screening_service):
        """Test that GET /api/screening/presets returns a list of presets."""
        # Arrange
        mock_screening_service.get_available_presets.return_value = [
            {
                "name": "accumulation_basic",
                "description": "Basic accumulation zone screening",
                "conditions": ["price_near_ma240", "low_volatility"]
            },
            {
                "name": "value_basic",
                "description": "Basic value screening",
                "conditions": ["low_pe", "high_roe"]
            }
        ]

        # Act
        response = client.get("/api/screening/presets")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "accumulation_basic"
        assert "conditions" in data[0]

    def test_get_presets_returns_empty_list(self, client, mock_screening_service):
        """Test that GET /api/screening/presets handles empty list."""
        # Arrange
        mock_screening_service.get_available_presets.return_value = []

        # Act
        response = client.get("/api/screening/presets")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestScreeningUniverses:
    """Tests for GET /api/screening/universes endpoint."""

    def test_get_universes_returns_list(self, client, mock_screening_service):
        """Test that GET /api/screening/universes returns list of universes."""
        # Arrange
        mock_screening_service.get_available_universes.return_value = [
            {"name": "KOSPI", "description": "Korea Large-Cap", "stock_count": 900},
            {"name": "SP500", "description": "US Large-Cap", "stock_count": 500}
        ]

        # Act
        response = client.get("/api/screening/universes")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "KOSPI"
        assert data[0]["stock_count"] == 900


class TestRunScreening:
    """Tests for POST /api/screening/run endpoint."""

    def test_run_screening_with_valid_preset(self, client, mock_screening_service):
        """Test POST /api/screening/run with valid preset and universe."""
        # Arrange
        mock_screening_service.run_screening.return_value = {
            "results": [
                {
                    "ticker": "005930.KS",
                    "name": "Samsung Electronics",
                    "current_price": 70000,
                    "matched": True,
                    "conditions": [
                        {"condition_name": "price_near_ma240", "matched": True, "details": {}}
                    ]
                }
            ],
            "total_count": 900,
            "matched_count": 1
        }

        request_data = {
            "preset": "accumulation_basic",
            "universe": "KOSPI"
        }

        # Act
        response = client.post("/api/screening/run", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_count" in data
        assert "matched_count" in data
        assert "universe" in data
        assert "universes" in data
        assert data["matched_count"] == 1
        assert data["universe"] == "KOSPI"
        assert data["universes"] == ["KOSPI"]
        assert len(data["results"]) == 1
        assert data["results"][0]["ticker"] == "005930.KS"
        mock_screening_service.run_screening.assert_called_once_with(
            preset="accumulation_basic",
            universe="KOSPI",
            universes=["KOSPI"],
            params=None,
        )

    def test_run_screening_with_invalid_preset_returns_400(
        self, client, mock_screening_service
    ):
        """Test POST /api/screening/run with invalid preset returns 400."""
        # Arrange
        mock_screening_service.run_screening.side_effect = ValueError(
            "Invalid preset: nonexistent_preset"
        )

        request_data = {
            "preset": "nonexistent_preset",
            "universe": "KOSPI"
        }

        # Act
        response = client.post("/api/screening/run", json=request_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid preset" in data["detail"]

    def test_run_screening_with_invalid_universe_returns_400(
        self, client, mock_screening_service
    ):
        """Test POST /api/screening/run with invalid universe returns 400."""
        # Arrange
        mock_screening_service.run_screening.side_effect = ValueError(
            "Invalid universe: INVALID"
        )

        request_data = {
            "preset": "accumulation_basic",
            "universe": "INVALID"
        }

        # Act
        response = client.post("/api/screening/run", json=request_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_run_screening_with_multi_universe_keeps_backward_compatibility(
        self, client, mock_screening_service
    ):
        """Multi-universe request should normalize and execute with primary universe."""
        # Arrange
        mock_screening_service.run_screening.return_value = {
            "results": [],
            "total_count": 1000,
            "matched_count": 0
        }
        request_data = {
            "preset": "accumulation_basic",
            "universe": "kospi,kosdaq"
        }

        # Act
        response = client.post("/api/screening/run", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["universe"] == "KOSPI"
        assert data["universes"] == ["KOSPI", "KOSDAQ"]
        mock_screening_service.run_screening.assert_called_once_with(
            preset="accumulation_basic",
            universe="KOSPI",
            universes=["KOSPI", "KOSDAQ"],
            params=None,
        )

    def test_run_screening_invalid_universe_uses_standard_message(
        self, client, mock_screening_service
    ):
        """Invalid universe should return standard 400 message before service execution."""
        # Arrange
        request_data = {
            "preset": "accumulation_basic",
            "universes": ["KOSPI", "INVALID"],
        }

        # Act
        response = client.post("/api/screening/run", json=request_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert (
            data["detail"]
            == "Invalid universe value(s): INVALID. Allowed values: KOSPI, KOSDAQ, SP500, NASDAQ100"
        )
        mock_screening_service.run_screening.assert_not_called()

    def test_run_screening_with_params(self, client, mock_screening_service):
        """Test POST /api/screening/run with custom parameters."""
        # Arrange
        mock_screening_service.run_screening.return_value = {
            "results": [],
            "total_count": 500,
            "matched_count": 0
        }

        request_data = {
            "preset": "accumulation_basic",
            "universe": "SP500",
            "params": {"min_price": 100}
        }

        # Act
        response = client.post("/api/screening/run", json=request_data)

        # Assert
        assert response.status_code == 200
        mock_screening_service.run_screening.assert_called_once()
        call_args = mock_screening_service.run_screening.call_args
        assert call_args[1]["params"] == {"min_price": 100}

    def test_run_screening_internal_error_returns_500(
        self, client, mock_screening_service
    ):
        """Test POST /api/screening/run handles internal errors."""
        # Arrange
        mock_screening_service.run_screening.side_effect = Exception(
            "Database connection failed"
        )

        request_data = {
            "preset": "accumulation_basic",
            "universe": "KOSPI"
        }

        # Act
        response = client.post("/api/screening/run", json=request_data)

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestSingleStockCheck:
    """Tests for GET /api/screening/stock/{ticker} endpoint."""

    def test_check_single_stock_returns_result(self, client, mock_screening_service):
        """Test GET /api/screening/stock/{ticker} returns result."""
        # Arrange
        mock_screening_service.check_single_stock.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "current_price": 175.50,
            "matched": True,
            "conditions": [
                {"condition_name": "price_near_ma240", "matched": True, "details": {}}
            ]
        }

        # Act
        response = client.get("/api/screening/stock/AAPL")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["matched"] is True

    def test_check_single_stock_with_preset_param(
        self, client, mock_screening_service
    ):
        """Test GET /api/screening/stock/{ticker} with preset parameter."""
        # Arrange
        mock_screening_service.check_single_stock.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "current_price": 175.50,
            "matched": False,
            "conditions": []
        }

        # Act
        response = client.get("/api/screening/stock/AAPL?preset=value_basic")

        # Assert
        assert response.status_code == 200
        mock_screening_service.check_single_stock.assert_called_once()

    def test_check_single_stock_invalid_ticker_returns_400(
        self, client, mock_screening_service
    ):
        """Test GET /api/screening/stock/{ticker} with invalid ticker."""
        # Arrange
        mock_screening_service.check_single_stock.side_effect = ValueError(
            "Failed to check stock: Invalid ticker"
        )

        # Act
        response = client.get("/api/screening/stock/INVALID123")

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
