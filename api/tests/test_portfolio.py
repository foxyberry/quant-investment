"""
Tests for portfolio API endpoints.

Tests the portfolio router endpoints including holdings CRUD,
portfolio summary, and sell signals.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestGetHoldings:
    """Tests for GET /api/portfolio/holdings endpoint."""

    def test_get_holdings_returns_list(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/holdings returns list of holdings."""
        # Arrange
        mock_portfolio_service.get_all_holdings.return_value = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "quantity": 10,
                "avg_price": 150.0,
                "current_price": 175.0,
                "market_value": 1750.0,
                "cost_basis": 1500.0,
                "pnl": 250.0,
                "pnl_pct": 16.67,
                "currency": "USD",
                "bought_at": None,
                "note": None
            }
        ]

        # Act
        response = client.get("/api/portfolio/holdings")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["quantity"] == 10

    def test_get_holdings_empty_portfolio(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/holdings with empty portfolio."""
        # Arrange
        mock_portfolio_service.get_all_holdings.return_value = []

        # Act
        response = client.get("/api/portfolio/holdings")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_holdings_without_prices(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/holdings with with_prices=false."""
        # Arrange
        mock_portfolio_service.get_all_holdings.return_value = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "quantity": 10,
                "avg_price": 150.0,
                "current_price": None,
                "market_value": None,
                "cost_basis": 1500.0,
                "pnl": None,
                "pnl_pct": None,
                "currency": "USD",
                "bought_at": None,
                "note": None
            }
        ]

        # Act
        response = client.get("/api/portfolio/holdings?with_prices=false")

        # Assert
        assert response.status_code == 200
        mock_portfolio_service.get_all_holdings.assert_called_once_with(
            with_prices=False
        )


class TestAddHolding:
    """Tests for POST /api/portfolio/holdings endpoint."""

    def test_add_holding_success(self, client, mock_portfolio_service, sample_holding):
        """Test POST /api/portfolio/holdings creates new holding."""
        # Arrange
        mock_portfolio_service.add_holding.return_value = {
            "ticker": sample_holding["ticker"],
            "name": sample_holding["name"],
            "quantity": sample_holding["quantity"],
            "avg_price": sample_holding["avg_price"],
            "current_price": 72000.0,
            "market_value": 7200000.0,
            "cost_basis": 7000000.0,
            "pnl": 200000.0,
            "pnl_pct": 2.86,
            "currency": "KRW",
            "bought_at": None,
            "note": sample_holding.get("note")
        }

        # Act
        response = client.post("/api/portfolio/holdings", json=sample_holding)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == sample_holding["ticker"]
        assert data["quantity"] == sample_holding["quantity"]

    def test_add_holding_invalid_quantity_returns_422(self, client):
        """Test POST /api/portfolio/holdings with invalid quantity returns 422."""
        # Arrange
        invalid_holding = {
            "ticker": "AAPL",
            "quantity": -10,  # Invalid: must be > 0
            "avg_price": 150.0
        }

        # Act
        response = client.post("/api/portfolio/holdings", json=invalid_holding)

        # Assert
        assert response.status_code == 422

    def test_add_holding_invalid_price_returns_422(self, client):
        """Test POST /api/portfolio/holdings with invalid price returns 422."""
        # Arrange
        invalid_holding = {
            "ticker": "AAPL",
            "quantity": 10,
            "avg_price": 0  # Invalid: must be > 0
        }

        # Act
        response = client.post("/api/portfolio/holdings", json=invalid_holding)

        # Assert
        assert response.status_code == 422

    def test_add_holding_missing_required_fields_returns_422(self, client):
        """Test POST /api/portfolio/holdings with missing fields returns 422."""
        # Arrange
        incomplete_holding = {
            "ticker": "AAPL"
            # Missing quantity and avg_price
        }

        # Act
        response = client.post("/api/portfolio/holdings", json=incomplete_holding)

        # Assert
        assert response.status_code == 422


class TestUpdateHolding:
    """Tests for PUT /api/portfolio/holdings/{ticker} endpoint."""

    def test_update_holding_success(self, client, mock_portfolio_service):
        """Test PUT /api/portfolio/holdings/{ticker} updates holding."""
        # Arrange
        mock_portfolio_service.update_holding.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "quantity": 20,  # Updated
            "avg_price": 155.0,  # Updated
            "current_price": 175.0,
            "market_value": 3500.0,
            "cost_basis": 3100.0,
            "pnl": 400.0,
            "pnl_pct": 12.9,
            "currency": "USD",
            "bought_at": None,
            "note": None
        }

        update_data = {
            "quantity": 20,
            "avg_price": 155.0
        }

        # Act
        response = client.put("/api/portfolio/holdings/AAPL", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 20
        assert data["avg_price"] == 155.0

    def test_update_holding_partial_update(self, client, mock_portfolio_service):
        """Test PUT /api/portfolio/holdings/{ticker} with partial update."""
        # Arrange
        mock_portfolio_service.update_holding.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "quantity": 15,  # Only quantity updated
            "avg_price": 150.0,
            "current_price": 175.0,
            "market_value": 2625.0,
            "cost_basis": 2250.0,
            "pnl": 375.0,
            "pnl_pct": 16.67,
            "currency": "USD",
            "bought_at": None,
            "note": None
        }

        update_data = {
            "quantity": 15
        }

        # Act
        response = client.put("/api/portfolio/holdings/AAPL", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 15

    def test_update_holding_not_found_returns_404(self, client, mock_portfolio_service):
        """Test PUT /api/portfolio/holdings/{ticker} with non-existent holding."""
        # Arrange
        mock_portfolio_service.update_holding.return_value = None

        update_data = {"quantity": 10}

        # Act
        response = client.put(
            "/api/portfolio/holdings/NONEXISTENT", json=update_data
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestDeleteHolding:
    """Tests for DELETE /api/portfolio/holdings/{ticker} endpoint."""

    def test_delete_holding_success(self, client, mock_portfolio_service):
        """Test DELETE /api/portfolio/holdings/{ticker} removes holding."""
        # Arrange
        mock_portfolio_service.remove_holding.return_value = True

        # Act
        response = client.delete("/api/portfolio/holdings/AAPL")

        # Assert
        assert response.status_code == 204

    def test_delete_holding_not_found_returns_404(self, client, mock_portfolio_service):
        """Test DELETE /api/portfolio/holdings/{ticker} with non-existent holding."""
        # Arrange
        mock_portfolio_service.remove_holding.return_value = False

        # Act
        response = client.delete("/api/portfolio/holdings/NONEXISTENT")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestGetSingleHolding:
    """Tests for GET /api/portfolio/holdings/{ticker} endpoint."""

    def test_get_single_holding(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/holdings/{ticker} returns single holding."""
        # Arrange
        mock_portfolio_service.get_holding.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "quantity": 10,
            "avg_price": 150.0,
            "current_price": 175.0,
            "market_value": 1750.0,
            "cost_basis": 1500.0,
            "pnl": 250.0,
            "pnl_pct": 16.67,
            "currency": "USD",
            "bought_at": None,
            "note": None
        }

        # Act
        response = client.get("/api/portfolio/holdings/AAPL")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"

    def test_get_single_holding_not_found_returns_404(
        self, client, mock_portfolio_service
    ):
        """Test GET /api/portfolio/holdings/{ticker} with non-existent holding."""
        # Arrange
        mock_portfolio_service.get_holding.return_value = None

        # Act
        response = client.get("/api/portfolio/holdings/NONEXISTENT")

        # Assert
        assert response.status_code == 404


class TestGetPortfolioSummary:
    """Tests for GET /api/portfolio/summary endpoint."""

    def test_get_summary_returns_aggregated_data(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/summary returns P&L data."""
        # Arrange
        mock_portfolio_service.get_summary.return_value = {
            "total_investment": 10000.0,
            "total_market_value": 12000.0,
            "total_pnl": 2000.0,
            "total_pnl_pct": 20.0,
            "holdings_count": 5,
            "currency": "USD",
            "last_updated": datetime.now().isoformat()
        }

        # Act
        response = client.get("/api/portfolio/summary")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_investment"] == 10000.0
        assert data["total_market_value"] == 12000.0
        assert data["total_pnl"] == 2000.0
        assert data["total_pnl_pct"] == 20.0
        assert data["holdings_count"] == 5

    def test_get_summary_empty_portfolio(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/summary with empty portfolio."""
        # Arrange
        mock_portfolio_service.get_summary.return_value = {
            "total_investment": 0.0,
            "total_market_value": 0.0,
            "total_pnl": 0.0,
            "total_pnl_pct": 0.0,
            "holdings_count": 0,
            "currency": "USD",
            "last_updated": datetime.now().isoformat()
        }

        # Act
        response = client.get("/api/portfolio/summary")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["holdings_count"] == 0
        assert data["total_pnl"] == 0.0


class TestGetSellSignals:
    """Tests for GET /api/portfolio/sell-signals endpoint."""

    def test_get_sell_signals_returns_list(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/sell-signals returns signals list."""
        # Arrange
        mock_portfolio_service.get_sell_signals.return_value = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "signal_type": "take_profit",
                "reason": "Reached 20% profit target",
                "current_price": 180.0,
                "trigger_price": 180.0,
                "avg_price": 150.0,
                "pnl_pct": 20.0
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corp.",
                "signal_type": "stop_loss",
                "reason": "Dropped below -10% threshold",
                "current_price": 270.0,
                "trigger_price": 270.0,
                "avg_price": 300.0,
                "pnl_pct": -10.0
            }
        ]

        # Act
        response = client.get("/api/portfolio/sell-signals")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "checked_at" in data
        assert len(data["signals"]) == 2
        assert data["signals"][0]["signal_type"] == "take_profit"
        assert data["signals"][1]["signal_type"] == "stop_loss"

    def test_get_sell_signals_empty(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/sell-signals with no signals."""
        # Arrange
        mock_portfolio_service.get_sell_signals.return_value = []

        # Act
        response = client.get("/api/portfolio/sell-signals")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["signals"] == []

    def test_get_sell_signals_with_custom_thresholds(
        self, client, mock_portfolio_service
    ):
        """Test GET /api/portfolio/sell-signals with custom thresholds."""
        # Arrange
        mock_portfolio_service.get_sell_signals.return_value = []

        # Act
        response = client.get(
            "/api/portfolio/sell-signals?stop_loss_pct=-15&take_profit_pct=30"
        )

        # Assert
        assert response.status_code == 200
        mock_portfolio_service.get_sell_signals.assert_called_once_with(
            stop_loss_pct=-15.0,
            take_profit_pct=30.0
        )


class TestGetFullPortfolio:
    """Tests for GET /api/portfolio endpoint."""

    def test_get_portfolio_returns_holdings_and_summary(
        self, client, mock_portfolio_service
    ):
        """Test GET /api/portfolio returns holdings and summary."""
        # Arrange
        mock_portfolio_service.get_all_holdings.return_value = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "quantity": 10,
                "avg_price": 150.0,
                "current_price": 175.0,
                "market_value": 1750.0,
                "cost_basis": 1500.0,
                "pnl": 250.0,
                "pnl_pct": 16.67,
                "currency": "USD",
                "bought_at": None,
                "note": None
            }
        ]
        mock_portfolio_service.get_summary.return_value = {
            "total_investment": 1500.0,
            "total_market_value": 1750.0,
            "total_pnl": 250.0,
            "total_pnl_pct": 16.67,
            "holdings_count": 1,
            "currency": "USD",
            "last_updated": datetime.now().isoformat()
        }

        # Act
        response = client.get("/api/portfolio")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "holdings" in data
        assert "summary" in data
        assert len(data["holdings"]) == 1
        assert data["summary"]["holdings_count"] == 1
