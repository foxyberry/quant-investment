"""Tests for DB-backed portfolio alert config service."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base
from api.models.portfolio_alert_config import PortfolioAlertConfig  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield testing_session
    engine.dispose()


@pytest.fixture()
def service(db_session, tmp_path: Path):
    import api.services.portfolio_alert_config_service as mod

    orig_session = mod.SessionLocal
    orig_path = mod._CONFIG_PATH
    mod.SessionLocal = db_session
    mod._CONFIG_PATH = tmp_path / "portfolio.yaml"
    from api.services.portfolio_alert_config_service import PortfolioAlertConfigService

    svc = PortfolioAlertConfigService()
    yield svc, mod._CONFIG_PATH
    mod.SessionLocal = orig_session
    mod._CONFIG_PATH = orig_path


def test_get_config_bootstraps_from_yaml(service):
    svc, config_path = service
    config_path.write_text(
        """
alert_settings:
  enabled: true
  scan_interval_seconds: 90
  stop_loss_pct: 0.11
  take_profit_pct: 0.22
  trailing_stop_pct: 0.09
  technical_signals: false
  market_hours_only: false
  channels:
    - telegram
    - slack
default_sell_conditions:
  stop_loss_pct: 0.07
  take_profit_pct: 0.18
  trailing_stop_pct: 0.06
technical_sell_signals:
  ma_breakdown: true
  death_cross: false
""".strip(),
        encoding="utf-8",
    )

    config = svc.get_config()
    assert config.enabled is True
    assert config.scan_interval_seconds == 90
    assert config.stop_loss_pct == 0.11
    assert config.take_profit_pct == 0.22
    assert config.trailing_stop_pct == 0.09
    assert config.technical_signals is False
    assert config.market_hours_only is False
    assert config.channels == ["telegram", "slack"]
    assert svc.get_default_sell_conditions() == {
        "stop_loss_pct": 0.07,
        "take_profit_pct": 0.18,
        "trailing_stop_pct": 0.06,
    }
    assert svc.get_technical_signals_config() == {
        "ma_breakdown": True,
        "death_cross": False,
    }


def test_save_config_persists_to_db_and_overrides_yaml(service):
    svc, config_path = service
    config_path.write_text(
        """
alert_settings:
  enabled: false
  scan_interval_seconds: 60
  stop_loss_pct: 0.20
  take_profit_pct: 0.30
  trailing_stop_pct: 0.10
  technical_signals: true
  market_hours_only: true
  channels:
    - telegram
default_sell_conditions:
  stop_loss_pct: 0.05
  take_profit_pct: 0.15
  trailing_stop_pct: 0.08
technical_sell_signals:
  ma_breakdown: true
""".strip(),
        encoding="utf-8",
    )

    saved = svc.save_config(
        {
            "enabled": True,
            "scan_interval_seconds": 120,
            "stop_loss_pct": 0.15,
            "take_profit_pct": 0.40,
            "trailing_stop_pct": 0.12,
            "technical_signals": False,
            "market_hours_only": False,
            "channels": ["slack"],
        }
    )
    assert saved.enabled is True
    assert saved.scan_interval_seconds == 120
    assert saved.channels == ["slack"]

    config_path.write_text(
        """
alert_settings:
  enabled: false
  scan_interval_seconds: 15
""".strip(),
        encoding="utf-8",
    )

    loaded = svc.get_config()
    assert loaded.enabled is True
    assert loaded.scan_interval_seconds == 120
    assert loaded.stop_loss_pct == 0.15
    assert loaded.take_profit_pct == 0.40
    assert loaded.trailing_stop_pct == 0.12
    assert loaded.technical_signals is False
    assert loaded.market_hours_only is False
    assert loaded.channels == ["slack"]
    assert svc.get_default_sell_conditions() == {
        "stop_loss_pct": 0.05,
        "take_profit_pct": 0.15,
        "trailing_stop_pct": 0.08,
    }
    assert svc.get_technical_signals_config() == {"ma_breakdown": True}


def test_save_config_does_not_mutate_default_sell_conditions_or_technical_config(service):
    svc, config_path = service
    config_path.write_text(
        """
alert_settings:
  enabled: true
default_sell_conditions:
  stop_loss_pct: 0.09
  take_profit_pct: 0.19
  trailing_stop_pct: 0.11
technical_sell_signals:
  ma_breakdown: false
  death_cross: true
""".strip(),
        encoding="utf-8",
    )

    svc.get_config()
    svc.save_config({"enabled": False, "channels": ["telegram", "slack"]})

    assert svc.get_default_sell_conditions() == {
        "stop_loss_pct": 0.09,
        "take_profit_pct": 0.19,
        "trailing_stop_pct": 0.11,
    }
    assert svc.get_technical_signals_config() == {
        "ma_breakdown": False,
        "death_cross": True,
    }
