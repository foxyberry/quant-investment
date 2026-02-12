"""
Pytest fixtures for API tests.

Provides shared fixtures for test client and sample data.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_holding():
    """Sample holding data for tests."""
    return {
        "ticker": "005930.KS",
        "name": "Samsung Electronics",
        "quantity": 100,
        "avg_price": 70000,
        "currency": "KRW",
        "note": "Test holding"
    }


@pytest.fixture
def sample_holding_us():
    """Sample US stock holding data for tests."""
    return {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "quantity": 10,
        "avg_price": 150.00,
        "currency": "USD",
        "note": "Test US holding"
    }


@pytest.fixture
def sample_screening_request():
    """Sample screening request data."""
    return {
        "preset": "accumulation_basic",
        "universe": "KOSPI",
        "params": None
    }


@pytest.fixture
def sample_enrich_request():
    """Sample enrichment request data."""
    return {
        "ticker": "AAPL"
    }


@pytest.fixture
def mock_portfolio_service():
    """Mock portfolio service for isolated testing."""
    with patch("api.routers.portfolio.get_portfolio_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_screening_service():
    """Mock screening service for isolated testing."""
    with patch("api.routers.screening.get_screening_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_market_service():
    """Mock market service for isolated testing."""
    with patch("api.routers.market._service") as mock:
        yield mock


@pytest.fixture
def mock_analysis_service():
    """Mock analysis service for isolated testing."""
    with patch("api.routers.analysis.get_analysis_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service
