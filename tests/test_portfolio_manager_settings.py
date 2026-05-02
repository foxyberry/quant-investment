"""Tests for PortfolioManager reading DB-backed sell/technical settings."""

from __future__ import annotations

import json
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base
from api.models.portfolio import Holding, SellRule
from api.models.portfolio_alert_config import PortfolioAlertConfig


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield testing_session
    engine.dispose()


@pytest.fixture()
def manager(db_session):
    import api.services.portfolio_alert_config_service as config_mod
    import api.database as database_mod

    orig_session = config_mod.SessionLocal
    orig_db_session = database_mod.SessionLocal
    config_mod.SessionLocal = db_session
    database_mod.SessionLocal = db_session

    db = db_session()
    try:
        db.add(
            PortfolioAlertConfig(
                id=1,
                enabled=True,
                scan_interval_seconds=60,
                stop_loss_pct=0.20,
                take_profit_pct=0.30,
                trailing_stop_pct=0.10,
                technical_signals=True,
                market_hours_only=True,
                channels_json='["telegram"]',
                default_stop_loss_pct=0.04,
                default_take_profit_pct=0.21,
                default_trailing_stop_pct=0.07,
                technical_signals_json=json.dumps({"ma_breakdown": True, "death_cross": False}),
                migrated_from_yaml=False,
            )
        )
        db.add(
            Holding(
                ticker="AAPL",
                name="Apple",
                quantity=10,
                avg_price=150.0,
                currency="USD",
                bought_at=date(2026, 1, 1),
            )
        )
        db.commit()
    finally:
        db.close()

    from screener.portfolio_manager import PortfolioManager

    mgr = PortfolioManager(config_path="/nonexistent/portfolio.yaml")
    yield mgr
    config_mod.SessionLocal = orig_session
    database_mod.SessionLocal = orig_db_session


def test_portfolio_manager_reads_db_backed_default_sell_conditions(manager):
    conditions = manager.get_default_sell_conditions()

    assert conditions.stop_loss_pct == 0.04
    assert conditions.take_profit_pct == 0.21
    assert conditions.trailing_stop_pct == 0.07


def test_portfolio_manager_reads_db_backed_technical_signals(manager):
    assert manager.get_technical_signals_config() == {
        "ma_breakdown": True,
        "death_cross": False,
    }


def test_portfolio_manager_uses_db_sell_rules_as_per_holding_overrides(db_session):
    import api.services.portfolio_alert_config_service as config_mod
    import api.database as database_mod

    orig_session = config_mod.SessionLocal
    orig_db_session = database_mod.SessionLocal
    config_mod.SessionLocal = db_session
    database_mod.SessionLocal = db_session

    db = db_session()
    try:
        db.add(
            PortfolioAlertConfig(
                id=1,
                enabled=True,
                scan_interval_seconds=60,
                stop_loss_pct=0.20,
                take_profit_pct=0.30,
                trailing_stop_pct=0.10,
                technical_signals=True,
                market_hours_only=True,
                channels_json='["telegram"]',
                default_stop_loss_pct=0.05,
                default_take_profit_pct=0.15,
                default_trailing_stop_pct=0.08,
                technical_signals_json="{}",
                migrated_from_yaml=False,
            )
        )
        db.add(
            Holding(
                ticker="AAPL",
                name="Apple",
                quantity=10,
                avg_price=150.0,
                currency="USD",
                bought_at=date(2026, 1, 1),
            )
        )
        db.add(SellRule(ticker="AAPL", rule_type="stop_loss", params={"pct": -3}, is_active=True))
        db.add(SellRule(ticker="AAPL", rule_type="take_profit", params={"pct": 25}, is_active=True))
        db.add(SellRule(ticker="AAPL", rule_type="trailing_stop", params={"pct": 12}, is_active=True))
        db.commit()
    finally:
        db.close()

    from screener.portfolio_manager import PortfolioManager

    mgr = PortfolioManager(config_path="/nonexistent/portfolio.yaml")
    conditions = mgr.get_sell_conditions_for("AAPL")

    assert conditions.stop_loss_pct == 0.03
    assert conditions.take_profit_pct == 0.25
    assert conditions.trailing_stop_pct == 0.12

    config_mod.SessionLocal = orig_session
    database_mod.SessionLocal = orig_db_session


def test_portfolio_manager_still_supports_legacy_yaml_override_fallback(db_session, tmp_path):
    import api.services.portfolio_alert_config_service as config_mod
    import api.database as database_mod

    orig_session = config_mod.SessionLocal
    orig_db_session = database_mod.SessionLocal
    config_mod.SessionLocal = db_session
    database_mod.SessionLocal = db_session

    db = db_session()
    try:
        db.add(
            PortfolioAlertConfig(
                id=1,
                enabled=True,
                scan_interval_seconds=60,
                stop_loss_pct=0.20,
                take_profit_pct=0.30,
                trailing_stop_pct=0.10,
                technical_signals=True,
                market_hours_only=True,
                channels_json='["telegram"]',
                default_stop_loss_pct=0.05,
                default_take_profit_pct=0.15,
                default_trailing_stop_pct=0.08,
                technical_signals_json="{}",
                migrated_from_yaml=False,
            )
        )
        db.commit()
    finally:
        db.close()

    config_path = tmp_path / "portfolio.yaml"
    config_path.write_text(
        """
holdings:
  TSLA:
    custom_conditions:
      stop_loss_pct: 0.02
      take_profit_pct: 0.30
""".strip(),
        encoding="utf-8",
    )

    from screener.portfolio_manager import PortfolioManager

    mgr = PortfolioManager(config_path=str(config_path))
    conditions = mgr.get_sell_conditions_for("TSLA")

    assert conditions.stop_loss_pct == 0.02
    assert conditions.take_profit_pct == 0.30
    assert conditions.trailing_stop_pct == 0.08

    config_mod.SessionLocal = orig_session
    database_mod.SessionLocal = orig_db_session
