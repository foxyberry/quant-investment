"""
Tests for search API endpoint.

Tests the search router endpoint for searching tickers.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestSearchEndpoint:
    """Tests for GET /api/search endpoint."""

    def test_search_tickers_returns_results(self, client):
        """Test GET /api/search returns matching tickers."""
        with patch("api.routers.search.yf") as mock_yf:
            # Mock direct ticker lookup
            mock_ticker = MagicMock()
            mock_yf.Ticker.return_value = mock_ticker
            mock_ticker.info = {
                "regularMarketPrice": 175.50,
                "shortName": "Apple Inc.",
            }

            # Mock search
            mock_yf.search.return_value = {
                "quotes": [
                    {"symbol": "AAPL", "shortname": "Apple Inc."},
                    {"symbol": "AAPD", "shortname": "Direxion Daily AAPL Bear"},
                ]
            }

            # Act
            response = client.get("/api/search?q=AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 1
            # First result should be the direct ticker match
            assert data[0]["ticker"] == "AAPL"
            assert data[0]["name"] == "Apple Inc."

    def test_search_tickers_by_name(self, client):
        """Test GET /api/search with company name query."""
        with patch("api.routers.search.yf") as mock_yf:
            # Direct ticker lookup fails
            mock_ticker = MagicMock()
            mock_yf.Ticker.return_value = mock_ticker
            mock_ticker.info = {"regularMarketPrice": None}

            # Search returns results
            mock_yf.search.return_value = {
                "quotes": [
                    {"symbol": "MSFT", "shortname": "Microsoft Corporation"},
                    {"symbol": "MSFUT", "shortname": "Microsoft Futures"},
                ]
            }

            # Act
            response = client.get("/api/search?q=microsoft")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
            assert any(r["ticker"] == "MSFT" for r in data)

    def test_search_tickers_empty_query_returns_422(self, client):
        """Test GET /api/search with empty query returns validation error."""
        # Act
        response = client.get("/api/search?q=")

        # Assert
        assert response.status_code == 422

    def test_search_tickers_no_query_returns_422(self, client):
        """Test GET /api/search without query parameter returns validation error."""
        # Act
        response = client.get("/api/search")

        # Assert
        assert response.status_code == 422

    def test_search_no_results(self, client):
        """Test GET /api/search with no matching tickers."""
        with patch("api.routers.search.yf") as mock_yf:
            # Direct lookup fails
            mock_ticker = MagicMock()
            mock_yf.Ticker.return_value = mock_ticker
            mock_ticker.info = {}

            # Search returns empty
            mock_yf.search.return_value = {"quotes": []}

            # Act
            response = client.get("/api/search?q=XYZNOTEXIST")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data == []

    def test_search_handles_yfinance_error(self, client):
        """Test GET /api/search handles yfinance errors gracefully."""
        with patch("api.routers.search.yf") as mock_yf:
            # Direct lookup fails
            mock_yf.Ticker.side_effect = Exception("API error")
            mock_yf.search.side_effect = Exception("Search API error")

            # Act
            response = client.get("/api/search?q=AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_search_limits_results_to_20(self, client):
        """Test GET /api/search returns at most 20 results."""
        with patch("api.routers.search.yf") as mock_yf:
            # Direct lookup
            mock_ticker = MagicMock()
            mock_yf.Ticker.return_value = mock_ticker
            mock_ticker.info = {"regularMarketPrice": None}

            # Return many results
            mock_yf.search.return_value = {
                "quotes": [
                    {"symbol": f"SYM{i}", "shortname": f"Stock {i}"}
                    for i in range(30)
                ]
            }

            # Act
            response = client.get("/api/search?q=SYM")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) <= 20

    def test_search_deduplicates_results(self, client):
        """Test GET /api/search deduplicates ticker results."""
        with patch("api.routers.search.yf") as mock_yf:
            # Direct lookup returns AAPL
            mock_ticker = MagicMock()
            mock_yf.Ticker.return_value = mock_ticker
            mock_ticker.info = {
                "regularMarketPrice": 175.50,
                "shortName": "Apple Inc.",
            }

            # Search also returns AAPL
            mock_yf.search.return_value = {
                "quotes": [
                    {"symbol": "AAPL", "shortname": "Apple Inc."},
                    {"symbol": "AAPL.L", "shortname": "Apple Inc. (London)"},
                ]
            }

            # Act
            response = client.get("/api/search?q=AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            tickers = [r["ticker"] for r in data]
            # AAPL should appear only once
            assert tickers.count("AAPL") == 1
