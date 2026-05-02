"""Tests for portfolio-wide trailing stop state and evaluation."""

import os
import sys
from unittest.mock import patch

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "sqlite:///test_portfolio_trailing.db"

from api.database import Base, SessionLocal, engine
import api.models.portfolio  # noqa: F401
import api.models.portfolio_alert  # noqa: F401
import api.models.portfolio_trailing_state  # noqa: F401
from api.models.portfolio_trailing_state import PortfolioTrailingState


def setup_function():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(PortfolioTrailingState).delete()
        db.commit()
    finally:
        db.close()


def teardown_function():
    db = SessionLocal()
    try:
        db.query(PortfolioTrailingState).delete()
        db.commit()
    finally:
        db.close()


def test_first_observation_seeds_watermark():
    from api.services.portfolio.portfolio_trailing_service import update_and_check_trailing

    db = SessionLocal()
    try:
        high_watermark, reason = update_and_check_trailing(db, "AAPL", 100.0, 0.10)
        db.commit()
        row = db.get(PortfolioTrailingState, "AAPL")
        assert high_watermark == 100.0
        assert reason is None
        assert row is not None
        assert row.high_watermark == 100.0
    finally:
        db.close()


def test_watermark_advances_on_higher_price():
    from api.services.portfolio.portfolio_trailing_service import update_and_check_trailing

    db = SessionLocal()
    try:
        update_and_check_trailing(db, "AAPL", 100.0, 0.10)
        db.commit()
        high_watermark, reason = update_and_check_trailing(db, "AAPL", 120.0, 0.10)
        db.commit()
        row = db.get(PortfolioTrailingState, "AAPL")
        assert high_watermark == 120.0
        assert reason is None
        assert row.high_watermark == 120.0
    finally:
        db.close()


def test_trigger_fires_on_drop_below_threshold():
    from api.services.portfolio.portfolio_trailing_service import update_and_check_trailing

    db = SessionLocal()
    try:
        update_and_check_trailing(db, "AAPL", 200.0, 0.10)
        db.commit()
        high_watermark, reason = update_and_check_trailing(db, "AAPL", 179.99, 0.10)
        db.commit()
        assert high_watermark == 200.0
        assert reason is not None
        assert "Trailing stop triggered" in reason
    finally:
        db.close()


def test_trigger_idempotent_per_day():
    from api.services.portfolio_alert_scanner import AlertSettings, HoldingInfo, PortfolioAlertScanner

    scanner = PortfolioAlertScanner()
    holdings = [HoldingInfo(ticker="AAPL", name="Apple", buy_price=100.0, quantity=10)]
    settings = AlertSettings(
        enabled=True,
        stop_loss_pct=0.50,
        take_profit_pct=2.00,
        trailing_stop_pct=0.10,
        market_hours_only=False,
    )

    with (
        patch(
            "api.services.portfolio.portfolio_alert_service._fetch_prices",
            side_effect=[{"AAPL": 200.0}, {"AAPL": 179.99}, {"AAPL": 179.99}],
        ),
        patch("api.services.notification_dispatcher.dispatch", return_value={"telegram": True}),
    ):
        assert scanner._scan(holdings, settings) == 0
        assert scanner._scan(holdings, settings) == 1
        assert scanner._scan(holdings, settings) == 0
