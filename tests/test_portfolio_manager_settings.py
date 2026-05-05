"""Tests for PortfolioManager provider injection and DB-backed provider behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base
from api.models.portfolio import Holding, SellRule
from api.services.portfolio_manager_provider import DBPortfolioDataProvider
from screener.portfolio_manager import PortfolioManager


@dataclass
class StubConfigResponse:
    technical_signals: bool


class StubConfigService:
    def __init__(
        self,
        *,
        default_sell_conditions: dict[str, float] | None = None,
        technical_signals_config: dict | None = None,
        technical_signals_enabled: bool = True,
    ) -> None:
        self._default_sell_conditions = default_sell_conditions or {
            "stop_loss_pct": 0.04,
            "take_profit_pct": 0.21,
            "trailing_stop_pct": 0.07,
        }
        self._technical_signals_config = technical_signals_config or {
            "ma_breakdown": True,
            "death_cross": False,
        }
        self._technical_signals_enabled = technical_signals_enabled

    def get_default_sell_conditions(self) -> dict[str, float]:
        return self._default_sell_conditions

    def get_technical_signals_config(self) -> dict:
        return self._technical_signals_config

    def get_config(self) -> StubConfigResponse:
        return StubConfigResponse(technical_signals=self._technical_signals_enabled)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield testing_session
    engine.dispose()


@pytest.fixture()
def provider(db_session):
    db = db_session()
    try:
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

    return DBPortfolioDataProvider(
        session_factory=db_session,
        config_service=StubConfigService(),
    )


@pytest.fixture()
def manager(provider):
    return PortfolioManager(config_path="/nonexistent/portfolio.yaml", provider=provider)


def test_portfolio_manager_reads_provider_backed_default_sell_conditions(manager):
    conditions = manager.get_default_sell_conditions()

    assert conditions.stop_loss_pct == 0.04
    assert conditions.take_profit_pct == 0.21
    assert conditions.trailing_stop_pct == 0.07


def test_portfolio_manager_reads_provider_backed_technical_signals(manager):
    assert manager.get_technical_signals_config() == {
        "ma_breakdown": True,
        "death_cross": False,
    }


def test_portfolio_manager_reads_technical_signals_enabled_flag_from_provider(manager):
    assert manager.is_technical_signals_enabled() is True


def test_portfolio_manager_reads_holdings_from_provider(manager):
    holdings = manager.get_holdings()

    assert len(holdings) == 1
    assert holdings[0].symbol == "AAPL"
    assert holdings[0].buy_price == 150.0


def test_portfolio_manager_uses_db_sell_rules_as_per_holding_overrides(db_session):
    db = db_session()
    try:
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

    provider = DBPortfolioDataProvider(
        session_factory=db_session,
        config_service=StubConfigService(
            default_sell_conditions={
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.15,
                "trailing_stop_pct": 0.08,
            }
        ),
    )

    mgr = PortfolioManager(config_path="/nonexistent/portfolio.yaml", provider=provider)
    conditions = mgr.get_sell_conditions_for("AAPL")

    assert conditions.stop_loss_pct == 0.03
    assert conditions.take_profit_pct == 0.25
    assert conditions.trailing_stop_pct == 0.12


def test_portfolio_manager_still_supports_legacy_yaml_override_fallback(db_session, tmp_path):
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

    provider = DBPortfolioDataProvider(
        session_factory=db_session,
        config_service=StubConfigService(
            default_sell_conditions={
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.15,
                "trailing_stop_pct": 0.08,
            }
        ),
    )

    mgr = PortfolioManager(config_path=str(config_path), provider=provider)
    conditions = mgr.get_sell_conditions_for("TSLA")

    assert conditions.stop_loss_pct == 0.02
    assert conditions.take_profit_pct == 0.30
    assert conditions.trailing_stop_pct == 0.08
