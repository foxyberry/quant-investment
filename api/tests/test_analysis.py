"""
Tests for analysis API endpoints.

Tests the analysis router endpoints including
stock enrichment and AI analysis.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestEnrichStock:
    """Tests for POST /api/analysis/enrich endpoint."""

    def test_enrich_stock_success(self, client, mock_analysis_service):
        """Test POST /api/analysis/enrich with valid ticker."""
        # Arrange
        mock_analysis_service.enrich_stock.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "current_price": 175.50,
            "ma_240": 165.00,
            "distance_pct": 6.36,
            "technical": {
                "rsi": 55.0,
                "macd": 2.5,
                "bb_position": "middle"
            },
            "fundamental": {
                "pe_ratio": 28.5,
                "pb_ratio": 45.2,
                "roe": 147.0,
                "market_cap": 2800000000000
            },
            "news": {
                "articles": [],
                "sentiment": "neutral"
            }
        }

        request_data = {"ticker": "AAPL"}

        # Act
        response = client.post("/api/analysis/enrich", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["current_price"] == 175.50
        assert "technical" in data
        assert "fundamental" in data
        assert data["technical"]["rsi"] == 55.0

    def test_enrich_stock_korean_ticker(self, client, mock_analysis_service):
        """Test POST /api/analysis/enrich with Korean ticker."""
        # Arrange
        mock_analysis_service.enrich_stock.return_value = {
            "ticker": "005930.KS",
            "name": "Samsung Electronics",
            "current_price": 70000.0,
            "ma_240": 68000.0,
            "distance_pct": 2.94,
            "technical": {
                "rsi": 48.0,
                "macd": -500.0
            },
            "fundamental": {
                "pe_ratio": 12.5,
                "pb_ratio": 1.2
            },
            "news": None
        }

        request_data = {"ticker": "005930.KS"}

        # Act
        response = client.post("/api/analysis/enrich", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "005930.KS"

    def test_enrich_stock_invalid_ticker_returns_400(
        self, client, mock_analysis_service
    ):
        """Test POST /api/analysis/enrich with invalid ticker returns 400."""
        # Arrange
        mock_analysis_service.enrich_stock.side_effect = ValueError(
            "Invalid ticker: INVALIDTICKER123"
        )

        request_data = {"ticker": "INVALIDTICKER123"}

        # Act
        response = client.post("/api/analysis/enrich", json=request_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_enrich_stock_service_error_returns_500(
        self, client, mock_analysis_service
    ):
        """Test POST /api/analysis/enrich handles service errors."""
        # Arrange
        mock_analysis_service.enrich_stock.side_effect = Exception(
            "External API error"
        )

        request_data = {"ticker": "AAPL"}

        # Act
        response = client.post("/api/analysis/enrich", json=request_data)

        # Assert
        assert response.status_code == 500


class TestAnalyzeStock:
    """Tests for POST /api/analysis/analyze endpoint."""

    def test_analyze_stock_success(self, client, mock_analysis_service):
        """Test POST /api/analysis/analyze with valid ticker."""
        # Arrange
        mock_analysis_service.is_claude_available.return_value = True
        mock_analysis_service.analyze_stock.return_value = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "current_price": 175.50,
            "valuation_score": 7.0,
            "risk_score": 4.0,
            "entry_recommendation": "BUY",
            "reasoning": "Strong fundamentals with reasonable valuation...",
            "key_risks": ["Market concentration", "China exposure"],
            "catalysts": ["AI products", "Services growth"]
        }

        request_data = {"ticker": "AAPL", "include_news": True}

        # Act
        response = client.post("/api/analysis/analyze", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["valuation_score"] == 7.0
        assert data["entry_recommendation"] == "BUY"
        assert len(data["key_risks"]) == 2

    def test_analyze_stock_no_api_key_returns_503(
        self, client, mock_analysis_service
    ):
        """Test POST /api/analysis/analyze without API key returns 503."""
        # Arrange
        mock_analysis_service.is_claude_available.return_value = False

        request_data = {"ticker": "AAPL"}

        # Act
        response = client.post("/api/analysis/analyze", json=request_data)

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "ANTHROPIC_API_KEY" in data["detail"]

    def test_analyze_stock_service_unavailable_returns_503(
        self, client, mock_analysis_service
    ):
        """Test POST /api/analysis/analyze handles service unavailable."""
        # Arrange
        mock_analysis_service.is_claude_available.return_value = True
        mock_analysis_service.analyze_stock.return_value = None

        request_data = {"ticker": "AAPL"}

        # Act
        response = client.post("/api/analysis/analyze", json=request_data)

        # Assert
        assert response.status_code == 503


class TestAnalysisStatus:
    """Tests for GET /api/analysis/status endpoint."""

    def test_get_status(self, client, mock_analysis_service):
        """Test GET /api/analysis/status returns service status."""
        # Arrange
        mock_analysis_service.is_claude_available.return_value = True
        mock_analysis_service.cache = MagicMock()
        mock_analysis_service.cache.cache_dir = "/path/to/cache"

        # Act
        response = client.get("/api/analysis/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "claude_available" in data
        assert "cache_available" in data
        assert "enrichers" in data

    def test_get_status_no_claude(self, client, mock_analysis_service):
        """Test GET /api/analysis/status when Claude is not available."""
        # Arrange
        mock_analysis_service.is_claude_available.return_value = False
        mock_analysis_service.cache = None

        # Act
        response = client.get("/api/analysis/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["claude_available"] is False


class TestTickerAnalysis:
    """Tests for GET /api/analysis/ticker/{ticker} endpoint."""

    def test_get_ticker_analysis_success(self, client):
        """Test GET /api/analysis/ticker/{ticker} returns combined analysis."""
        with patch("api.routers.analysis.MarketService") as MockMarketService:
            mock_service = MagicMock()
            MockMarketService.return_value = mock_service

            # Mock OHLCV
            mock_service.get_ohlcv.return_value = {
                "ticker": "AAPL",
                "data": [
                    {
                        "date": "2026-02-11",
                        "open": 174.0,
                        "high": 176.0,
                        "low": 173.5,
                        "close": 175.5,
                        "volume": 50000000,
                    }
                ],
                "period_days": 1,
            }

            # Mock quote
            mock_service.get_quote.return_value = {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "current_price": 175.50,
                "change": 2.30,
                "change_pct": 1.33,
                "volume": 50000000,
                "timestamp": "2026-02-12T10:00:00",
            }

            # Mock technical indicators
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
                "ma_240": 165.0,
            }

            # Mock ticker info lookup for fundamental data
            mock_service.get_ticker_info.return_value = {
                "marketCap": 2800000000000,
                "trailingPE": 28.5,
                "dividendYield": 0.005,
                "sector": "Technology",
            }

            # Act
            response = client.get("/api/analysis/ticker/AAPL?period=6mo")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "AAPL"
            assert data["name"] == "Apple Inc."
            assert data["current_price"] == 175.50
            assert data["change_pct"] == 1.33
            assert len(data["ohlcv"]) == 1
            assert data["ohlcv"][0]["time"] == "2026-02-11"
            assert data["technical"]["rsi"]["value"] == 55.5
            assert data["technical"]["rsi"]["signal"] == "neutral"
            assert data["technical"]["macd"]["trend"] == "bullish"
            assert data["fundamental"]["sector"] == "Technology"

    def test_get_ticker_analysis_not_found(self, client):
        """Test GET /api/analysis/ticker/{ticker} with invalid ticker returns 404."""
        with patch("api.routers.analysis.MarketService") as MockMarketService:
            mock_service = MagicMock()
            MockMarketService.return_value = mock_service
            mock_service.get_ohlcv.return_value = None

            # Act
            response = client.get("/api/analysis/ticker/INVALIDTICKER")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    def test_get_ticker_analysis_partial_data(self, client):
        """Test GET /api/analysis/ticker/{ticker} with partial data available."""
        with patch("api.routers.analysis.MarketService") as MockMarketService:
            mock_service = MagicMock()
            MockMarketService.return_value = mock_service

            # OHLCV available
            mock_service.get_ohlcv.return_value = {
                "ticker": "NEWSTOCK",
                "data": [
                    {
                        "date": "2026-02-11",
                        "open": 10.0,
                        "high": 11.0,
                        "low": 9.5,
                        "close": 10.5,
                        "volume": 100000,
                    }
                ],
                "period_days": 1,
            }

            # Quote available
            mock_service.get_quote.return_value = {
                "ticker": "NEWSTOCK",
                "name": None,
                "current_price": 10.5,
                "change": 0.5,
                "change_pct": 5.0,
                "volume": 100000,
                "timestamp": "2026-02-12T10:00:00",
            }

            # No technical data
            mock_service.get_technical_indicators.return_value = None

            # No fundamental data
            mock_service.get_ticker_info.return_value = {}

            # Act
            response = client.get("/api/analysis/ticker/NEWSTOCK")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "NEWSTOCK"
            assert data["name"] == "NEWSTOCK"  # Falls back to ticker
            assert data["technical"]["rsi"] is None
            assert data["fundamental"] is None
