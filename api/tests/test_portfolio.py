"""
Tests for portfolio API endpoints.

Tests the portfolio router endpoints including holdings CRUD,
portfolio summary, sell signals, and CSV import/export.
"""

import io
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from api.services.portfolio_service import PortfolioService


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

    def test_get_summary_with_base_currency(self, client, mock_portfolio_service):
        """Test GET /api/portfolio/summary passes base_currency to service."""
        mock_portfolio_service.get_summary.return_value = {
            "total_investment": 7407.41,
            "total_market_value": 8888.89,
            "total_pnl": 1481.48,
            "total_pnl_pct": 20.0,
            "holdings_count": 2,
            "currency": "USD",
            "last_updated": datetime.now().isoformat(),
        }

        response = client.get("/api/portfolio/summary?base_currency=usd")

        assert response.status_code == 200
        mock_portfolio_service.get_summary.assert_called_once_with(base_currency="usd")
        assert response.json()["currency"] == "USD"

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
                "pnl_pct": 20.0,
                "currency": "USD",
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corp.",
                "signal_type": "stop_loss",
                "reason": "Dropped below -10% threshold",
                "current_price": 270.0,
                "trigger_price": 270.0,
                "avg_price": 300.0,
                "pnl_pct": -10.0,
                "currency": "USD",
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
        assert data["signals"][0]["currency"] == "USD"

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


def _csv_upload(client, content: str, mode: str = "merge"):
    """Helper to POST CSV content as file upload."""
    return client.post(
        "/api/portfolio/holdings/import",
        files={"file": ("test.csv", io.BytesIO(content.encode("utf-8")), "text/csv")},
        data={"mode": mode},
    )


class TestImportCsv:
    """Tests for POST /api/portfolio/holdings/import endpoint."""

    def test_import_csv_merge_success(self, client, mock_portfolio_service):
        """Valid CSV merge import returns correct counts."""
        mock_portfolio_service.import_from_csv.return_value = {
            "imported": 2, "updated": 1, "skipped": 0, "errors": []
        }
        csv = "ticker,quantity,avg_price\nAAPL,10,185\nMSFT,5,420\nGOOG,3,140\n"
        resp = _csv_upload(client, csv, "merge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 2
        assert data["updated"] == 1
        assert data["skipped"] == 0

    def test_import_csv_replace_success(self, client, mock_portfolio_service):
        """Replace mode clears existing holdings first."""
        mock_portfolio_service.import_from_csv.return_value = {
            "imported": 2, "updated": 0, "skipped": 0, "errors": []
        }
        csv = "ticker,quantity,avg_price\nAAPL,10,185\nMSFT,5,420\n"
        resp = _csv_upload(client, csv, "replace")
        assert resp.status_code == 200
        mock_portfolio_service.import_from_csv.assert_called_once()
        call_args = mock_portfolio_service.import_from_csv.call_args
        assert call_args[1].get("mode") == "replace" or call_args[0][1] == "replace"

    def test_import_csv_validation_errors(self, client, mock_portfolio_service):
        """Bad rows result in partial success with errors."""
        mock_portfolio_service.import_from_csv.return_value = {
            "imported": 1, "updated": 0, "skipped": 1,
            "errors": [{"row": 3, "ticker": "BAD", "reason": "Invalid quantity: abc"}]
        }
        csv = "ticker,quantity,avg_price\nAAPL,10,185\nBAD,abc,100\n"
        resp = _csv_upload(client, csv)
        assert resp.status_code == 200
        data = resp.json()
        assert data["skipped"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["row"] == 3

    def test_import_csv_empty_file(self, client, mock_portfolio_service):
        """Empty file returns 400."""
        resp = client.post(
            "/api/portfolio/holdings/import",
            files={"file": ("test.csv", io.BytesIO(b""), "text/csv")},
            data={"mode": "merge"},
        )
        assert resp.status_code == 400

    def test_import_csv_missing_columns(self, client, mock_portfolio_service):
        """Missing required columns returns 400."""
        mock_portfolio_service.import_from_csv.side_effect = ValueError(
            "Missing required columns: avg_price"
        )
        csv = "ticker,quantity\nAAPL,10\n"
        resp = _csv_upload(client, csv)
        assert resp.status_code == 400
        assert "Missing required columns" in resp.json()["detail"]

    def test_import_csv_invalid_mode(self, client, mock_portfolio_service):
        """Invalid mode returns 422."""
        csv = "ticker,quantity,avg_price\nAAPL,10,185\n"
        resp = _csv_upload(client, csv, "invalid")
        assert resp.status_code == 422

    def test_import_csv_minimal_columns(self, client, mock_portfolio_service):
        """Only required columns still works with defaults."""
        mock_portfolio_service.import_from_csv.return_value = {
            "imported": 1, "updated": 0, "skipped": 0, "errors": []
        }
        csv = "ticker,quantity,avg_price\nAAPL,10,185.50\n"
        resp = _csv_upload(client, csv)
        assert resp.status_code == 200
        assert resp.json()["imported"] == 1

    def test_import_csv_unicode(self, client, mock_portfolio_service):
        """Korean name/note in CSV works correctly."""
        mock_portfolio_service.import_from_csv.return_value = {
            "imported": 1, "updated": 0, "skipped": 0, "errors": []
        }
        csv = "ticker,quantity,avg_price,name,note\n005930.KS,50,72000,삼성전자,핵심 보유\n"
        resp = _csv_upload(client, csv)
        assert resp.status_code == 200


class TestExportCsv:
    """Tests for GET /api/portfolio/holdings/export endpoint."""

    def test_export_csv_content(self, client, mock_portfolio_service):
        """Exported CSV matches holdings data."""
        mock_portfolio_service.export_to_csv.return_value = (
            "ticker,quantity,avg_price,name,currency,note\r\n"
            "AAPL,10,185.5,Apple Inc.,USD,\r\n"
        )
        resp = client.get("/api/portfolio/holdings/export")
        assert resp.status_code == 200
        body = resp.text
        assert "AAPL" in body
        assert "185.5" in body

    def test_export_csv_empty(self, client, mock_portfolio_service):
        """Empty portfolio exports header-only CSV."""
        mock_portfolio_service.export_to_csv.return_value = (
            "ticker,quantity,avg_price,name,currency,note\r\n"
        )
        resp = client.get("/api/portfolio/holdings/export")
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        # BOM + header only
        assert len(lines) == 1

    def test_export_csv_headers(self, client, mock_portfolio_service):
        """Response has correct content-type and content-disposition."""
        mock_portfolio_service.export_to_csv.return_value = "ticker,quantity,avg_price,name,currency,note\r\n"
        resp = client.get("/api/portfolio/holdings/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "portfolio_holdings.csv" in resp.headers["content-disposition"]


class TestTemplate:
    """Tests for GET /api/portfolio/holdings/template endpoint."""

    def test_template_full(self, client, mock_portfolio_service):
        """Full template returns CSV with all columns."""
        resp = client.get("/api/portfolio/holdings/template")
        assert resp.status_code == 200
        body = resp.text
        assert "ticker" in body
        assert "name" in body
        assert "currency" in body
        assert "bought_at" in body

    def test_template_minimal(self, client, mock_portfolio_service):
        """Minimal template returns only required columns."""
        resp = client.get("/api/portfolio/holdings/template?minimal=true")
        assert resp.status_code == 200
        body = resp.text
        assert "ticker" in body
        assert "quantity" in body
        # Minimal should not have name column in header
        header_line = body.strip().split("\n")[0]
        assert "name" not in header_line

    def test_template_content_disposition(self, client, mock_portfolio_service):
        """Template response has download headers."""
        resp = client.get("/api/portfolio/holdings/template")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]


def _setup_test_db(holdings):
    """Create an in-memory SQLite DB and seed it with holdings dicts.

    Returns a patched SessionLocal bound to the in-memory engine.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from api.database import Base
    from api.models.portfolio import Holding

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    db = TestSession()
    for h in holdings:
        db.add(Holding(
            ticker=h["ticker"],
            name=h.get("name"),
            quantity=h["quantity"],
            avg_price=h["avg_price"],
            currency=h.get("currency", "KRW"),
        ))
    db.commit()
    db.close()

    return TestSession


class TestPriceCache:
    """Tests for PortfolioService price cache and parallel fetch behavior."""

    def test_price_cache_reuse(self):
        """Cached prices are reused on the second call within TTL."""
        # Arrange
        test_session = _setup_test_db([
            {"ticker": "AAPL", "name": "Apple", "quantity": 10, "avg_price": 150.0, "currency": "USD"},
            {"ticker": "MSFT", "name": "Microsoft", "quantity": 5, "avg_price": 300.0, "currency": "USD"},
        ])

        with patch("api.services.portfolio_service.SessionLocal", test_session):
            service = PortfolioService()
            price_map = {"AAPL": 175.0, "MSFT": 320.0}

            with patch.object(service._cache, "get_latest_prices", return_value={}):
                with patch.object(service, "_get_current_price", side_effect=lambda t: price_map[t]) as mock_price:
                    # Act
                    service.get_all_holdings(with_prices=True)
                    service.get_all_holdings(with_prices=True)

                    # Assert - second call should reuse cache, so only 2 calls total
                    assert mock_price.call_count == 2

    def test_price_cache_expiry(self):
        """Expired cache triggers a fresh fetch path on the next call."""
        # Arrange
        test_session = _setup_test_db([
            {"ticker": "AAPL", "name": "Apple", "quantity": 10, "avg_price": 150.0, "currency": "USD"},
            {"ticker": "MSFT", "name": "Microsoft", "quantity": 5, "avg_price": 300.0, "currency": "USD"},
        ])

        with patch("api.services.portfolio_service.SessionLocal", test_session):
            service = PortfolioService()
            batch_prices = {"AAPL": 175.0, "MSFT": 320.0}

            with patch.object(service._cache, "get_latest_prices", return_value=batch_prices) as mock_batch:
                # Act - first call fetches prices
                service.get_all_holdings(with_prices=True)

                # Expire the cache by backdating the timestamp
                service._price_cache_time = time.monotonic() - (service.PRICE_CACHE_TTL + 30)

                # Second call should re-fetch because cache is expired
                service.get_all_holdings(with_prices=True)

                # Assert - batch fetch path is invoked again after expiry
                assert mock_batch.call_count == 2

    def test_parallel_price_fetch(self):
        """_get_current_prices returns correct prices for all tickers."""
        # Arrange
        test_session = _setup_test_db([
            {"ticker": "AAPL", "name": "Apple", "quantity": 10, "avg_price": 150.0, "currency": "USD"},
            {"ticker": "MSFT", "name": "Microsoft", "quantity": 5, "avg_price": 300.0, "currency": "USD"},
            {"ticker": "GOOG", "name": "Alphabet", "quantity": 3, "avg_price": 140.0, "currency": "USD"},
        ])

        with patch("api.services.portfolio_service.SessionLocal", test_session):
            service = PortfolioService()
            price_map = {"AAPL": 175.0, "MSFT": 320.0, "GOOG": 155.0}

            with patch.object(service._cache, "get_latest_prices", return_value={}):
                with patch.object(service, "_get_current_price", side_effect=lambda t: price_map[t]):
                    # Act
                    result = service._get_current_prices(["AAPL", "MSFT", "GOOG"])

                    # Assert
                    assert result["AAPL"] == 175.0
                    assert result["MSFT"] == 320.0
                    assert result["GOOG"] == 155.0

    def test_batch_price_fetch_path(self):
        """When batch cache path returns prices, per-ticker fallback is skipped."""
        test_session = _setup_test_db([
            {"ticker": "AAPL", "name": "Apple", "quantity": 10, "avg_price": 150.0, "currency": "USD"},
            {"ticker": "MSFT", "name": "Microsoft", "quantity": 5, "avg_price": 300.0, "currency": "USD"},
        ])

        with patch("api.services.portfolio_service.SessionLocal", test_session):
            service = PortfolioService()
            with patch.object(service._cache, "get_latest_prices", return_value={"AAPL": 175.0, "MSFT": 320.0}):
                with patch.object(service, "_get_current_price") as mock_price:
                    result = service._get_current_prices(["AAPL", "MSFT"])
                    assert result["AAPL"] == 175.0
                    assert result["MSFT"] == 320.0
                    mock_price.assert_not_called()

    def test_summary_reuses_cached_prices(self):
        """get_summary reuses prices cached by a prior get_all_holdings call."""
        # Arrange
        test_session = _setup_test_db([
            {"ticker": "AAPL", "name": "Apple", "quantity": 10, "avg_price": 150.0, "currency": "USD"},
            {"ticker": "MSFT", "name": "Microsoft", "quantity": 5, "avg_price": 300.0, "currency": "USD"},
        ])

        with patch("api.services.portfolio_service.SessionLocal", test_session):
            service = PortfolioService()
            price_map = {"AAPL": 175.0, "MSFT": 320.0}

            with patch.object(service._cache, "get_latest_prices", return_value={}):
                with patch.object(service, "_get_current_price", side_effect=lambda t: price_map[t]) as mock_price:
                    # Act - first call populates the cache
                    service.get_all_holdings(with_prices=True)
                    # get_summary internally calls get_all_holdings(with_prices=True)
                    service.get_summary()

                    # Assert - prices fetched only once (2 tickers), not twice (4 calls)
                    assert mock_price.call_count == 2


class TestSummaryCurrencyConversion:
    """Tests for PortfolioService summary currency conversion."""

    def test_get_summary_converts_to_requested_base_currency(self):
        test_session = _setup_test_db([
            {"ticker": "005930.KS", "name": "Samsung", "quantity": 10, "avg_price": 10000.0, "currency": "KRW"},
            {"ticker": "AAPL", "name": "Apple", "quantity": 2, "avg_price": 100.0, "currency": "USD"},
        ])

        with patch("api.services.portfolio_service.SessionLocal", test_session):
            service = PortfolioService()
            # Keep market values equal to cost basis for deterministic totals.
            with patch.object(service, "_get_current_price", return_value=None):
                with patch.object(service._fx, "get_rates") as mock_rates:
                    # Base USD: 1 USD = 1350 KRW
                    mock_rates.return_value = {
                        "base": "USD",
                        "rates": {"KRW": 1350.0, "JPY": 150.0},
                        "updated_at": datetime.now(),
                    }

                    summary = service.get_summary(base_currency="USD")

                    # 100,000 KRW -> 74.074... USD, plus 200 USD = 274.074...
                    assert summary.currency == "USD"
                    assert summary.total_investment == pytest.approx(274.074074, rel=1e-6)
                    assert summary.total_market_value == pytest.approx(274.074074, rel=1e-6)
                    assert summary.total_pnl == pytest.approx(0.0, abs=1e-9)
