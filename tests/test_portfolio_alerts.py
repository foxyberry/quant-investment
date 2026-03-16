"""Tests for portfolio alert dedup logic and scanner."""

import os
import sys
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Setup: configure in-memory SQLite BEFORE importing any api modules
# ---------------------------------------------------------------------------

os.environ["DATABASE_URL"] = "sqlite:///test_portfolio_alerts.db"

from api.database import Base, SessionLocal, engine
import api.models.portfolio_alert  # noqa: F401
from api.models.portfolio_alert import PortfolioAlertHistory


@pytest.fixture(autouse=True)
def _fresh_tables():
    """Create tables before each test, truncate after."""
    Base.metadata.create_all(bind=engine)
    yield
    # Truncate alert history between tests
    db = SessionLocal()
    try:
        db.query(PortfolioAlertHistory).delete()
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tests — dedup logic
# ---------------------------------------------------------------------------


class TestDedupLogic:
    def test_first_alert_succeeds(self):
        from api.services.portfolio_alert_service import record_and_send

        with patch("api.services.portfolio_alert_service._send_telegram") as mock_tg:
            result = record_and_send("005930.KS", "stop_loss", "Test message", 50000.0)
            assert result is True
            mock_tg.assert_called_once()

    def test_duplicate_alert_blocked(self):
        from api.services.portfolio_alert_service import record_and_send

        with patch("api.services.portfolio_alert_service._send_telegram"):
            record_and_send("005930.KS", "stop_loss", "First", 50000.0)
            result = record_and_send("005930.KS", "stop_loss", "Duplicate", 49000.0)
            assert result is False

    def test_different_signal_type_allowed(self):
        from api.services.portfolio_alert_service import record_and_send

        with patch("api.services.portfolio_alert_service._send_telegram"):
            r1 = record_and_send("005930.KS", "stop_loss", "SL", 50000.0)
            r2 = record_and_send("005930.KS", "take_profit", "TP", 80000.0)
            assert r1 is True
            assert r2 is True

    def test_different_ticker_allowed(self):
        from api.services.portfolio_alert_service import record_and_send

        with patch("api.services.portfolio_alert_service._send_telegram"):
            r1 = record_and_send("005930.KS", "stop_loss", "A", 50000.0)
            r2 = record_and_send("035420.KS", "stop_loss", "B", 180000.0)
            assert r1 is True
            assert r2 is True

    def test_is_already_sent_today(self):
        from api.services.portfolio_alert_service import is_already_sent_today, record_and_send

        with patch("api.services.portfolio_alert_service._send_telegram"):
            assert is_already_sent_today("AAPL", "stop_loss") is False
            record_and_send("AAPL", "stop_loss", "msg", 150.0)
            assert is_already_sent_today("AAPL", "stop_loss") is True
            assert is_already_sent_today("AAPL", "take_profit") is False

    def test_get_history(self):
        from api.services.portfolio_alert_service import get_history, record_and_send

        with patch("api.services.portfolio_alert_service._send_telegram"):
            record_and_send("AAPL", "stop_loss", "msg1", 150.0)
            record_and_send("MSFT", "take_profit", "msg2", 400.0)

        history = get_history(limit=10)
        assert history.total_count == 2
        assert len(history.alerts) == 2


# ---------------------------------------------------------------------------
# Tests — scanner
# ---------------------------------------------------------------------------


class TestScanner:
    def test_scan_fires_stop_loss(self):
        from api.services.portfolio_alert_scanner import (
            AlertSettings,
            HoldingInfo,
            PortfolioAlertScanner,
        )

        scanner = PortfolioAlertScanner()

        holdings = [
            HoldingInfo(ticker="005930.KS", name="Samsung", buy_price=80000, quantity=10),
        ]
        settings = AlertSettings(
            enabled=True,
            stop_loss_pct=0.20,
            take_profit_pct=0.30,
            market_hours_only=False,
        )

        # Price at 60000 = -25% from buy price → triggers stop loss
        with (
            patch("api.services.portfolio_alert_scanner._fetch_prices", return_value={"005930.KS": 60000.0}),
            patch("api.services.portfolio_alert_service._send_telegram"),
        ):
            alerts = scanner._scan(holdings, settings)
            assert alerts == 1

    def test_scan_fires_take_profit(self):
        from api.services.portfolio_alert_scanner import (
            AlertSettings,
            HoldingInfo,
            PortfolioAlertScanner,
        )

        scanner = PortfolioAlertScanner()

        holdings = [
            HoldingInfo(ticker="AAPL", name="Apple", buy_price=100, quantity=10),
        ]
        settings = AlertSettings(
            enabled=True,
            stop_loss_pct=0.20,
            take_profit_pct=0.30,
            market_hours_only=False,
        )

        # Price at 135 = +35% → triggers take profit
        with (
            patch("api.services.portfolio_alert_scanner._fetch_prices", return_value={"AAPL": 135.0}),
            patch("api.services.portfolio_alert_service._send_telegram"),
        ):
            alerts = scanner._scan(holdings, settings)
            assert alerts == 1

    def test_scan_no_alert_in_safe_zone(self):
        from api.services.portfolio_alert_scanner import (
            AlertSettings,
            HoldingInfo,
            PortfolioAlertScanner,
        )

        scanner = PortfolioAlertScanner()

        holdings = [
            HoldingInfo(ticker="AAPL", name="Apple", buy_price=100, quantity=10),
        ]
        settings = AlertSettings(
            enabled=True,
            stop_loss_pct=0.20,
            take_profit_pct=0.30,
            market_hours_only=False,
        )

        # Price at 105 = +5% → no alert
        with (
            patch("api.services.portfolio_alert_scanner._fetch_prices", return_value={"AAPL": 105.0}),
            patch("api.services.portfolio_alert_service._send_telegram"),
        ):
            alerts = scanner._scan(holdings, settings)
            assert alerts == 0


# ---------------------------------------------------------------------------
# Tests — message formatting
# ---------------------------------------------------------------------------


class TestMessageFormat:
    def test_kr_format(self):
        from api.services.portfolio_alert_scanner import HoldingInfo, _format_sell_message

        h = HoldingInfo(ticker="005930.KS", name="삼성전자", buy_price=80000, quantity=10)
        msg = _format_sell_message(h, "stop_loss", 60000, -0.25)
        assert "삼성전자" in msg
        assert "₩60,000" in msg
        assert "₩80,000" in msg
        assert "손절" in msg

    def test_us_format(self):
        from api.services.portfolio_alert_scanner import HoldingInfo, _format_sell_message

        h = HoldingInfo(ticker="AAPL", name="Apple", buy_price=200, quantity=5)
        msg = _format_sell_message(h, "take_profit", 270, 0.35)
        assert "Apple" in msg
        assert "$270.00" in msg
        assert "익절" in msg
