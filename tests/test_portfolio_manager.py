"""Tests for PortfolioManager sell-condition resolution."""

from __future__ import annotations

from pathlib import Path
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base
from api.models.portfolio_alert_config import PortfolioAlertConfig
from screener.portfolio_manager import PortfolioManager


def _write_config(tmp_path: Path, body: str) -> Path:
    config_path = tmp_path / "portfolio.yaml"
    config_path.write_text(body, encoding="utf-8")
    return config_path


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield testing_session
    engine.dispose()


@pytest.fixture()
def patch_db_sessions(db_session):
    import api.database as database_mod
    import api.services.portfolio_alert_config_service as config_mod

    orig_db_session = database_mod.SessionLocal
    orig_config_session = config_mod.SessionLocal
    database_mod.SessionLocal = db_session
    config_mod.SessionLocal = db_session
    try:
        yield db_session
    finally:
        database_mod.SessionLocal = orig_db_session
        config_mod.SessionLocal = orig_config_session


def _seed_default_config(db_session) -> None:
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
                technical_signals_json=json.dumps({}),
                migrated_from_yaml=False,
            )
        )
        db.commit()
    finally:
        db.close()


def test_get_sell_conditions_for_returns_defaults_without_holding_override(tmp_path, patch_db_sessions):
    _seed_default_config(patch_db_sessions)
    config_path = _write_config(
        tmp_path,
        """
""".strip(),
    )

    manager = PortfolioManager(config_path=str(config_path))
    conditions = manager.get_sell_conditions_for("AAPL")

    assert conditions.stop_loss_pct == 0.05
    assert conditions.take_profit_pct == 0.15
    assert conditions.trailing_stop_pct == 0.08


def test_get_sell_conditions_for_merges_sell_conditions_override(tmp_path, patch_db_sessions):
    _seed_default_config(patch_db_sessions)
    config_path = _write_config(
        tmp_path,
        """
holdings:
  AAPL:
    sell_conditions:
      take_profit_pct: 0.25
      trailing_stop_pct: 0.12
""".strip(),
    )

    manager = PortfolioManager(config_path=str(config_path))
    conditions = manager.get_sell_conditions_for("AAPL")

    assert conditions.stop_loss_pct == 0.05
    assert conditions.take_profit_pct == 0.25
    assert conditions.trailing_stop_pct == 0.12


def test_get_sell_conditions_for_supports_legacy_custom_conditions_key(tmp_path, patch_db_sessions):
    _seed_default_config(patch_db_sessions)
    config_path = _write_config(
        tmp_path,
        """
holdings:
  TSLA:
    custom_conditions:
      stop_loss_pct: 0.03
""".strip(),
    )

    manager = PortfolioManager(config_path=str(config_path))
    conditions = manager.get_sell_conditions_for("tsla")

    assert conditions.stop_loss_pct == 0.03
    assert conditions.take_profit_pct == 0.15
    assert conditions.trailing_stop_pct == 0.08
