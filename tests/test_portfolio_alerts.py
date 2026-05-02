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
import api.models.portfolio  # noqa: F401
import api.models.portfolio_alert  # noqa: F401
import api.models.portfolio_alert_config  # noqa: F401
import api.models.portfolio_trailing_state  # noqa: F401
from api.models.portfolio import Holding
from api.models.portfolio_alert import PortfolioAlertHistory
from api.models.portfolio_alert_config import PortfolioAlertConfig
from api.models.portfolio_trailing_state import PortfolioTrailingState


@pytest.fixture(autouse=True)
def _fresh_tables():
    """Create tables before each test, truncate after."""
    Base.metadata.create_all(bind=engine)
    yield
    # Truncate between tests
    db = SessionLocal()
    try:
        db.query(PortfolioAlertHistory).delete()
        db.query(PortfolioAlertConfig).delete()
        db.query(PortfolioTrailingState).delete()
        db.query(Holding).delete()
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tests — dedup logic
# ---------------------------------------------------------------------------


class TestDedupLogic:
    def test_first_alert_succeeds(self):
        from api.services.portfolio_alert_service import record_and_send

        with patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}) as mock_dispatch:
            result = record_and_send("005930.KS", "stop_loss", "Test message", 50000.0)
            assert result is True
            mock_dispatch.assert_called_once()

    def test_duplicate_alert_blocked(self):
        from api.services.portfolio_alert_service import record_and_send

        with patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}):
            record_and_send("005930.KS", "stop_loss", "First", 50000.0)
            result = record_and_send("005930.KS", "stop_loss", "Duplicate", 49000.0)
            assert result is False

    def test_different_signal_type_allowed(self):
        from api.services.portfolio_alert_service import record_and_send

        with patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}):
            r1 = record_and_send("005930.KS", "stop_loss", "SL", 50000.0)
            r2 = record_and_send("005930.KS", "take_profit", "TP", 80000.0)
            assert r1 is True
            assert r2 is True

    def test_different_ticker_allowed(self):
        from api.services.portfolio_alert_service import record_and_send

        with patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}):
            r1 = record_and_send("005930.KS", "stop_loss", "A", 50000.0)
            r2 = record_and_send("035420.KS", "stop_loss", "B", 180000.0)
            assert r1 is True
            assert r2 is True

    def test_is_already_sent_today(self):
        from api.services.portfolio_alert_service import is_already_sent_today, record_and_send

        with patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}):
            assert is_already_sent_today("AAPL", "stop_loss") is False
            record_and_send("AAPL", "stop_loss", "msg", 150.0)
            assert is_already_sent_today("AAPL", "stop_loss") is True
            assert is_already_sent_today("AAPL", "take_profit") is False

    def test_get_history(self):
        from api.services.portfolio_alert_service import get_history, record_and_send

        with patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}):
            record_and_send("AAPL", "stop_loss", "msg1", 150.0)
            record_and_send("MSFT", "take_profit", "msg2", 400.0)

        history = get_history(limit=10)
        assert history.total_count == 2
        assert len(history.alerts) == 2


# ---------------------------------------------------------------------------
# Tests — DB holdings loading
# ---------------------------------------------------------------------------


class TestDBHoldings:
    def test_load_holdings_from_db(self):
        from api.services.portfolio_alert_scanner import _load_holdings_from_db

        # Insert a holding into DB
        db = SessionLocal()
        db.add(Holding(ticker="005930.KS", name="삼성전자", quantity=10, avg_price=70000, currency="KRW"))
        db.commit()
        db.close()

        holdings = _load_holdings_from_db()
        assert len(holdings) == 1
        assert holdings[0].ticker == "005930.KS"
        assert holdings[0].name == "삼성전자"
        assert holdings[0].buy_price == 70000
        assert holdings[0].quantity == 10

    def test_zero_quantity_excluded(self):
        from api.services.portfolio_alert_scanner import _load_holdings_from_db

        db = SessionLocal()
        db.add(Holding(ticker="AAPL", name="Apple", quantity=10, avg_price=150, currency="USD"))
        db.add(Holding(ticker="SOLD", name="Sold Stock", quantity=0, avg_price=100, currency="USD"))
        db.commit()
        db.close()

        holdings = _load_holdings_from_db()
        assert len(holdings) == 1
        assert holdings[0].ticker == "AAPL"

    def test_load_config_uses_db(self):
        from api.services.portfolio_alert_scanner import load_config

        db = SessionLocal()
        db.add(Holding(ticker="MSFT", name="Microsoft", quantity=5, avg_price=400, currency="USD"))
        db.commit()
        db.close()

        holdings, settings = load_config()
        assert len(holdings) == 1
        assert holdings[0].ticker == "MSFT"


class TestPortfolioResetBehavior:
    def test_replace_import_clears_alert_history_and_trailing_state(self):
        from api.services.portfolio.portfolio_core_service import PortfolioCoreService
        from api.services.portfolio_alert_service import record_and_send
        from api.services.portfolio.portfolio_trailing_service import update_and_check_trailing

        class _NoopThread:
            def __init__(self, *args, **kwargs):
                pass

            def start(self):
                return None

        with patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}):
            record_and_send("005930.KS", "stop_loss", "old alert", 50000.0)

        db = SessionLocal()
        try:
            update_and_check_trailing(db, "005930.KS", 100.0, 0.10)
            db.commit()
        finally:
            db.close()

        service = PortfolioCoreService()
        csv_content = "ticker,quantity,avg_price,name\nAAPL,3,150,Apple\n"
        with patch("api.services.portfolio.portfolio_csv_service.threading.Thread", _NoopThread):
            result = service.import_from_csv(csv_content, mode="replace")

        assert result["imported"] == 1

        db = SessionLocal()
        try:
            assert db.query(PortfolioAlertHistory).count() == 0
            assert db.query(PortfolioTrailingState).count() == 0
            assert db.query(Holding).count() == 1
        finally:
            db.close()

    def test_delete_all_holdings_clears_alert_history_and_trailing_state(self):
        from api.services.portfolio.portfolio_core_service import PortfolioCoreService
        from api.services.portfolio_alert_service import record_and_send
        from api.services.portfolio.portfolio_trailing_service import update_and_check_trailing

        db = SessionLocal()
        try:
            db.add(Holding(ticker="AAPL", name="Apple", quantity=10, avg_price=150, currency="USD"))
            update_and_check_trailing(db, "AAPL", 200.0, 0.10)
            db.commit()
        finally:
            db.close()

        with patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}):
            record_and_send("AAPL", "take_profit", "old alert", 200.0)

        service = PortfolioCoreService()
        service.delete_all_holdings()

        db = SessionLocal()
        try:
            assert db.query(PortfolioAlertHistory).count() == 0
            assert db.query(PortfolioTrailingState).count() == 0
            assert db.query(Holding).count() == 0
        finally:
            db.close()

    def test_remove_holding_clears_single_ticker_trailing_state(self):
        from api.services.portfolio.portfolio_core_service import PortfolioCoreService
        from api.services.portfolio.portfolio_trailing_service import update_and_check_trailing

        db = SessionLocal()
        try:
            db.add(Holding(ticker="AAPL", name="Apple", quantity=10, avg_price=150, currency="USD"))
            db.add(Holding(ticker="MSFT", name="Microsoft", quantity=5, avg_price=400, currency="USD"))
            update_and_check_trailing(db, "AAPL", 200.0, 0.10)
            update_and_check_trailing(db, "MSFT", 500.0, 0.10)
            db.commit()
        finally:
            db.close()

        service = PortfolioCoreService()
        assert service.remove_holding("AAPL") is True

        db = SessionLocal()
        try:
            assert db.get(PortfolioTrailingState, "AAPL") is None
            assert db.get(PortfolioTrailingState, "MSFT") is not None
        finally:
            db.close()


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
            patch("api.services.portfolio.portfolio_alert_service._fetch_prices", return_value={"005930.KS": 60000.0}),
            patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}),
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
            patch("api.services.portfolio.portfolio_alert_service._fetch_prices", return_value={"AAPL": 135.0}),
            patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}),
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
            patch("api.services.portfolio.portfolio_alert_service._fetch_prices", return_value={"AAPL": 105.0}),
            patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}),
        ):
            alerts = scanner._scan(holdings, settings)
            assert alerts == 0

    def test_scan_uses_per_holding_sell_conditions_for_trailing_threshold(self):
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
            trailing_stop_pct=0.10,
            market_hours_only=False,
        )

        class _Conditions:
            stop_loss_pct = 0.20
            take_profit_pct = 0.30
            trailing_stop_pct = 0.20

        manager = MagicMock()
        manager.get_sell_conditions_for.return_value = _Conditions()

        with (
            patch("api.services.portfolio.portfolio_alert_service._fetch_prices", side_effect=[{"AAPL": 120.0}, {"AAPL": 100.0}]),
            patch("api.services.portfolio.portfolio_alert_service._load_sell_conditions_for_tickers", return_value={"AAPL": _Conditions()}),
            patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}),
        ):
            assert scanner._scan(holdings, settings) == 0
            assert scanner._scan(holdings, settings) == 0


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
