"""Tests for per-holding sell rules: schemas, service CRUD, evaluation engine, API endpoints.

Covers:
- Schema validation (SellRuleCreate params per rule_type)
- Service CRUD (create, read, update, delete)
- Evaluation engine (each rule_type, dry_run, edge cases)
- trailing_stop state_json persistence
- Duplicate trigger prevention
- CASCADE deletion (holding delete → rules deleted)
- API endpoint integration (HTTP level)
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Generator
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base
from api.models.portfolio import Holding, SellRule
from api.schemas.portfolio import (
    SELL_RULE_TYPES,
    SellRuleCreate,
    SellRuleUpdate,
    SellSignal,
    _is_finite_number,
    _validate_sell_rule_params,
)
from api.services.portfolio_service import PortfolioService


# ── Test fixtures ─────────────────────────────────────────────────


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite database and return a session.

    Uses ``expire_on_commit=False`` so ORM objects remain readable after
    the service layer commits, and wraps the session so that the
    service's ``db.close()`` calls are no-ops (preventing the shared
    test session from being destroyed mid-test).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key enforcement (SQLite disables CASCADE by default)
    @event.listens_for(engine, "connect")
    def _set_fk_pragma(dbapi_conn, _connection_record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    # Prevent service methods from closing the shared test session
    _real_close = session.close
    session.close = lambda: None
    yield session
    _real_close()


@pytest.fixture()
def service(db_session) -> Generator[PortfolioService, None, None]:
    """Create a PortfolioService that uses the test DB session."""
    with patch("api.services.portfolio_service.SessionLocal", return_value=db_session), \
         patch.object(PortfolioService, "_backfill_null_sectors"):
        svc = PortfolioService()
        yield svc


@pytest.fixture()
def holding(db_session) -> Holding:
    """Insert a test holding into the DB."""
    h = Holding(
        ticker="005930.KS",
        name="삼성전자",
        quantity=100,
        avg_price=70000,
        currency="KRW",
        bought_at=date(2025, 1, 15),
    )
    db_session.add(h)
    db_session.commit()
    return h


@pytest.fixture()
def holding_us(db_session) -> Holding:
    """Insert a US test holding into the DB."""
    h = Holding(
        ticker="AAPL",
        name="Apple Inc.",
        quantity=50,
        avg_price=150.0,
        currency="USD",
        bought_at=date(2025, 6, 1),
    )
    db_session.add(h)
    db_session.commit()
    return h


# =========================================================================
# 1. Helper function tests
# =========================================================================


class TestIsFiniteNumber:
    def test_finite_int(self):
        assert _is_finite_number(10) is True
        assert _is_finite_number(-5) is True
        assert _is_finite_number(0) is True

    def test_finite_float(self):
        assert _is_finite_number(3.14) is True
        assert _is_finite_number(-0.5) is True

    def test_nan(self):
        assert _is_finite_number(float("nan")) is False

    def test_inf(self):
        assert _is_finite_number(float("inf")) is False
        assert _is_finite_number(float("-inf")) is False

    def test_bool_rejected(self):
        assert _is_finite_number(True) is False
        assert _is_finite_number(False) is False

    def test_string_rejected(self):
        assert _is_finite_number("10") is False

    def test_none_rejected(self):
        assert _is_finite_number(None) is False


# =========================================================================
# 2. Schema validation tests
# =========================================================================


class TestSellRuleCreateValidation:
    """Test SellRuleCreate Pydantic schema validation."""

    def test_valid_stop_loss(self):
        rule = SellRuleCreate(rule_type="stop_loss", params={"pct": -10})
        assert rule.rule_type == "stop_loss"
        assert rule.params["pct"] == -10

    def test_valid_take_profit(self):
        rule = SellRuleCreate(rule_type="take_profit", params={"pct": 20})
        assert rule.rule_type == "take_profit"

    def test_valid_trailing_stop(self):
        rule = SellRuleCreate(rule_type="trailing_stop", params={"pct": 8})
        assert rule.rule_type == "trailing_stop"

    def test_valid_holding_period(self):
        rule = SellRuleCreate(rule_type="holding_period", params={"max_days": 90})
        assert rule.rule_type == "holding_period"

    def test_invalid_rule_type(self):
        with pytest.raises(ValidationError, match="Invalid rule_type"):
            SellRuleCreate(rule_type="unknown", params={"pct": -10})

    def test_stop_loss_positive_pct_rejected(self):
        with pytest.raises(ValidationError, match="must be negative"):
            SellRuleCreate(rule_type="stop_loss", params={"pct": 10})

    def test_stop_loss_zero_pct_rejected(self):
        with pytest.raises(ValidationError, match="must be negative"):
            SellRuleCreate(rule_type="stop_loss", params={"pct": 0})

    def test_take_profit_negative_pct_rejected(self):
        with pytest.raises(ValidationError, match="must be positive"):
            SellRuleCreate(rule_type="take_profit", params={"pct": -5})

    def test_take_profit_zero_pct_rejected(self):
        with pytest.raises(ValidationError, match="must be positive"):
            SellRuleCreate(rule_type="take_profit", params={"pct": 0})

    def test_trailing_stop_negative_pct_rejected(self):
        with pytest.raises(ValidationError, match="must be positive"):
            SellRuleCreate(rule_type="trailing_stop", params={"pct": -3})

    def test_holding_period_non_integer_rejected(self):
        with pytest.raises(ValidationError, match="integer"):
            SellRuleCreate(rule_type="holding_period", params={"max_days": 30.5})

    def test_holding_period_negative_rejected(self):
        with pytest.raises(ValidationError, match="must be positive"):
            SellRuleCreate(rule_type="holding_period", params={"max_days": -1})

    def test_holding_period_zero_rejected(self):
        with pytest.raises(ValidationError, match="must be positive"):
            SellRuleCreate(rule_type="holding_period", params={"max_days": 0})

    def test_holding_period_bool_rejected(self):
        with pytest.raises(ValidationError, match="integer"):
            SellRuleCreate(rule_type="holding_period", params={"max_days": True})

    def test_stop_loss_missing_pct(self):
        with pytest.raises(ValidationError, match="finite numeric"):
            SellRuleCreate(rule_type="stop_loss", params={})

    def test_stop_loss_nan_pct(self):
        with pytest.raises(ValidationError, match="finite numeric"):
            SellRuleCreate(rule_type="stop_loss", params={"pct": float("nan")})

    def test_stop_loss_inf_pct(self):
        with pytest.raises(ValidationError, match="finite numeric"):
            SellRuleCreate(rule_type="stop_loss", params={"pct": float("inf")})

    def test_default_is_active_true(self):
        rule = SellRuleCreate(rule_type="stop_loss", params={"pct": -10})
        assert rule.is_active is True

    def test_explicit_is_active_false(self):
        rule = SellRuleCreate(rule_type="stop_loss", params={"pct": -10}, is_active=False)
        assert rule.is_active is False


class TestValidateSellRuleParams:
    """Test the standalone _validate_sell_rule_params function."""

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown rule_type"):
            _validate_sell_rule_params("nonexistent", {"pct": 10})

    def test_deterministic_error_message(self):
        """Error message should contain sorted rule types for deterministic output."""
        with pytest.raises(ValueError) as exc_info:
            _validate_sell_rule_params("bad_type", {})
        msg = str(exc_info.value)
        assert "holding_period" in msg
        assert "stop_loss" in msg


class TestSellSignalSchema:
    """Test SellSignal schema with NaN sanitization."""

    def test_nan_sanitization(self):
        signal = SellSignal(
            ticker="AAPL", name="Apple", signal_type="stop_loss",
            reason="test", current_price=float("nan"),
            avg_price=float("inf"), pnl_pct=float("-inf"),
            trigger_price=float("nan"), currency="USD",
        )
        assert signal.current_price == 0.0
        assert signal.avg_price == 0.0
        assert signal.pnl_pct == 0.0
        assert signal.trigger_price is None

    def test_rule_id_optional(self):
        signal = SellSignal(
            ticker="T", name="T", signal_type="stop_loss",
            reason="r", current_price=10, avg_price=12, pnl_pct=-16.7,
            currency="USD",
        )
        assert signal.rule_id is None

    def test_rule_id_present(self):
        signal = SellSignal(
            ticker="T", name="T", signal_type="stop_loss",
            reason="r", current_price=10, avg_price=12, pnl_pct=-16.7,
            currency="USD", rule_id=42,
        )
        assert signal.rule_id == 42


# =========================================================================
# 3. Service CRUD tests
# =========================================================================


class TestSellRuleCRUD:
    """Test sell rule CRUD operations via PortfolioService."""

    def test_create_and_list(self, service, holding, db_session):
        data = SellRuleCreate(rule_type="stop_loss", params={"pct": -10})
        result = service.create_sell_rule(holding.ticker, data)
        assert result.ticker == holding.ticker
        assert result.rule_type == "stop_loss"
        assert result.params == {"pct": -10}
        assert result.is_active is True
        assert result.triggered_at is None

        rules = service.get_sell_rules(holding.ticker)
        assert len(rules) == 1
        assert rules[0].id == result.id

    def test_create_for_nonexistent_holding(self, service, db_session):
        data = SellRuleCreate(rule_type="stop_loss", params={"pct": -10})
        with pytest.raises(ValueError, match="Holding not found"):
            service.create_sell_rule("NONEXISTENT", data)

    def test_create_with_market_suffix_alias(self, service, db_session):
        """Legacy holdings without suffix should accept .KS/.KQ ticker input."""
        h = Holding(
            ticker="021240",
            name="코웨이",
            quantity=10,
            avg_price=50000,
            currency="KRW",
            bought_at=date(2025, 1, 15),
        )
        db_session.add(h)
        db_session.commit()

        created = service.create_sell_rule(
            "021240.KS",
            SellRuleCreate(rule_type="stop_loss", params={"pct": -10}),
        )
        assert created.ticker == "021240"

        by_alias = service.get_sell_rules("021240.KS")
        by_raw = service.get_sell_rules("021240")
        assert len(by_alias) == 1
        assert len(by_raw) == 1
        assert by_alias[0].id == by_raw[0].id

    def test_create_multiple_rules(self, service, holding, db_session):
        service.create_sell_rule(holding.ticker, SellRuleCreate(
            rule_type="stop_loss", params={"pct": -10},
        ))
        service.create_sell_rule(holding.ticker, SellRuleCreate(
            rule_type="take_profit", params={"pct": 20},
        ))
        rules = service.get_sell_rules(holding.ticker)
        assert len(rules) == 2
        types = {r.rule_type for r in rules}
        assert types == {"stop_loss", "take_profit"}

    def test_update_params(self, service, holding, db_session):
        created = service.create_sell_rule(holding.ticker, SellRuleCreate(
            rule_type="stop_loss", params={"pct": -10},
        ))
        updated = service.update_sell_rule(created.id, SellRuleUpdate(
            params={"pct": -15},
        ))
        assert updated.params == {"pct": -15}

    def test_update_is_active(self, service, holding, db_session):
        created = service.create_sell_rule(holding.ticker, SellRuleCreate(
            rule_type="stop_loss", params={"pct": -10},
        ))
        updated = service.update_sell_rule(created.id, SellRuleUpdate(is_active=False))
        assert updated.is_active is False

    def test_update_nonexistent_raises(self, service, db_session):
        with pytest.raises(ValueError, match="Sell rule not found"):
            service.update_sell_rule(9999, SellRuleUpdate(is_active=False))

    def test_update_with_invalid_params_raises(self, service, holding, db_session):
        created = service.create_sell_rule(holding.ticker, SellRuleCreate(
            rule_type="stop_loss", params={"pct": -10},
        ))
        with pytest.raises(ValueError, match="must be negative"):
            service.update_sell_rule(created.id, SellRuleUpdate(params={"pct": 10}))

    def test_delete_rule(self, service, holding, db_session):
        created = service.create_sell_rule(holding.ticker, SellRuleCreate(
            rule_type="stop_loss", params={"pct": -10},
        ))
        assert service.delete_sell_rule(created.id) is True
        assert service.get_sell_rules(holding.ticker) == []

    def test_delete_nonexistent_returns_false(self, service, db_session):
        assert service.delete_sell_rule(9999) is False

    def test_list_empty_rules(self, service, holding, db_session):
        rules = service.get_sell_rules(holding.ticker)
        assert rules == []

    def test_cascade_delete_on_holding_removal(self, service, holding, db_session):
        service.create_sell_rule(holding.ticker, SellRuleCreate(
            rule_type="stop_loss", params={"pct": -10},
        ))
        service.create_sell_rule(holding.ticker, SellRuleCreate(
            rule_type="take_profit", params={"pct": 20},
        ))
        assert len(service.get_sell_rules(holding.ticker)) == 2

        # Delete the holding directly
        db_session.delete(holding)
        db_session.commit()

        # Rules should be cascade-deleted
        count = db_session.query(SellRule).filter(SellRule.ticker == holding.ticker).count()
        assert count == 0


# =========================================================================
# 4. Evaluation engine tests
# =========================================================================


class TestEvaluateSellRules:
    """Test sell rule evaluation engine."""

    def _add_rule(self, db_session, ticker: str, rule_type: str, params: dict, **kwargs) -> SellRule:
        rule = SellRule(ticker=ticker, rule_type=rule_type, params=params, is_active=True, **kwargs)
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)
        return rule

    def test_stop_loss_triggered(self, service, holding, db_session):
        self._add_rule(db_session, holding.ticker, "stop_loss", {"pct": -10})
        # avg_price=70000, -10% threshold = 63000, current=60000 → triggered
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 60000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert len(result.results) == 1
        assert result.results[0].triggered is True
        assert result.results[0].trigger_value == pytest.approx(63000)

    def test_stop_loss_not_triggered(self, service, holding, db_session):
        self._add_rule(db_session, holding.ticker, "stop_loss", {"pct": -10})
        # avg=70000, threshold=63000, current=65000 → not triggered
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 65000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is False

    def test_take_profit_triggered(self, service, holding, db_session):
        self._add_rule(db_session, holding.ticker, "take_profit", {"pct": 20})
        # avg=70000, +20% threshold=84000, current=90000 → triggered
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 90000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is True
        assert result.results[0].trigger_value == pytest.approx(84000)

    def test_take_profit_not_triggered(self, service, holding, db_session):
        self._add_rule(db_session, holding.ticker, "take_profit", {"pct": 20})
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 80000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is False

    def test_trailing_stop_triggered(self, service, holding, db_session):
        # trailing_stop with 10% pullback, high_watermark=100000
        self._add_rule(
            db_session, holding.ticker, "trailing_stop", {"pct": 10},
            state_json={"high_watermark": 100000},
        )
        # 10% below 100000 = 90000, current=85000 → triggered
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 85000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is True
        assert result.results[0].trigger_value == pytest.approx(90000)

    def test_trailing_stop_updates_high_watermark(self, service, holding, db_session):
        rule = self._add_rule(
            db_session, holding.ticker, "trailing_stop", {"pct": 10},
            state_json={"high_watermark": 80000},
        )
        # current=95000 > old hwm=80000 → should update hwm, not trigger
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 95000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is False
        # Check state_json was updated
        db_session.refresh(rule)
        assert rule.state_json["high_watermark"] == 95000

    def test_trailing_stop_no_hwm_initially(self, service, holding, db_session):
        rule = self._add_rule(
            db_session, holding.ticker, "trailing_stop", {"pct": 10},
        )
        # No state_json → hwm should be set to current price
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 75000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is False
        db_session.refresh(rule)
        assert rule.state_json["high_watermark"] == 75000

    def test_holding_period_triggered(self, service, holding, db_session):
        # Holding bought 100 days ago, max_days=90
        holding.bought_at = date.today() - timedelta(days=100)
        db_session.commit()
        self._add_rule(db_session, holding.ticker, "holding_period", {"max_days": 90})
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 75000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is True

    def test_holding_period_not_triggered(self, service, holding, db_session):
        holding.bought_at = date.today() - timedelta(days=30)
        db_session.commit()
        self._add_rule(db_session, holding.ticker, "holding_period", {"max_days": 90})
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 75000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is False

    def test_inactive_rules_skipped(self, service, holding, db_session):
        self._add_rule(db_session, holding.ticker, "stop_loss", {"pct": -10})
        inactive = SellRule(
            ticker=holding.ticker, rule_type="take_profit",
            params={"pct": 5}, is_active=False,
        )
        db_session.add(inactive)
        db_session.commit()
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 60000}):
            result = service.evaluate_sell_rules(holding.ticker)
        # Only active rule evaluated
        assert len(result.results) == 1
        assert result.results[0].rule_type == "stop_loss"

    def test_already_triggered_rules_skipped(self, service, holding, db_session):
        self._add_rule(
            db_session, holding.ticker, "stop_loss", {"pct": -10},
        )
        triggered = SellRule(
            ticker=holding.ticker, rule_type="take_profit",
            params={"pct": 5}, is_active=True,
            triggered_at=datetime.now(tz=None),
        )
        db_session.add(triggered)
        db_session.commit()
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 60000}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert len(result.results) == 1
        assert result.results[0].rule_type == "stop_loss"

    def test_no_rules_returns_empty(self, service, holding, db_session):
        with patch.object(service, "_get_current_prices", return_value={}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results == []

    def test_missing_price_returns_not_triggered(self, service, holding, db_session):
        self._add_rule(db_session, holding.ticker, "stop_loss", {"pct": -10})
        # Price not available
        with patch.object(service, "_get_current_prices", return_value={}):
            result = service.evaluate_sell_rules(holding.ticker)
        assert result.results[0].triggered is False
        assert "unavailable" in result.results[0].reason

    def test_dry_run_does_not_persist_triggered_at(self, service, holding, db_session):
        rule = self._add_rule(db_session, holding.ticker, "stop_loss", {"pct": -10})
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 60000}):
            result = service.evaluate_sell_rules(holding.ticker, dry_run=True)
        assert result.results[0].triggered is True
        # But triggered_at should NOT be persisted
        db_session.refresh(rule)
        assert rule.triggered_at is None

    def test_dry_run_does_not_persist_hwm(self, service, holding, db_session):
        rule = self._add_rule(
            db_session, holding.ticker, "trailing_stop", {"pct": 10},
            state_json={"high_watermark": 70000},
        )
        # current=80000 > hwm=70000, dry_run should not persist new hwm
        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 80000}):
            service.evaluate_sell_rules(holding.ticker, dry_run=True)
        db_session.refresh(rule)
        assert rule.state_json["high_watermark"] == 70000

    def test_evaluation_error_isolated(self, service, holding, db_session):
        """Bad params in one rule should not crash the whole batch."""
        # Good rule
        self._add_rule(db_session, holding.ticker, "stop_loss", {"pct": -10})
        # Bad rule (will fail in factory due to missing 'pct')
        bad_rule = SellRule(
            ticker=holding.ticker, rule_type="take_profit",
            params={}, is_active=True,
        )
        db_session.add(bad_rule)
        db_session.commit()

        with patch.object(service, "_get_current_prices", return_value={holding.ticker: 60000}):
            result = service.evaluate_sell_rules(holding.ticker)
        # Both rules evaluated, one with error
        assert len(result.results) == 2
        errors = [r for r in result.results if r.reason and "Evaluation error" in r.reason]
        successes = [r for r in result.results if r.reason is None or "Evaluation error" not in r.reason]
        assert len(errors) == 1
        assert len(successes) == 1

    def test_evaluate_all_tickers(self, service, holding, holding_us, db_session):
        """Evaluate rules across multiple holdings when no ticker filter."""
        self._add_rule(db_session, holding.ticker, "stop_loss", {"pct": -10})
        self._add_rule(db_session, holding_us.ticker, "take_profit", {"pct": 20})

        prices = {holding.ticker: 60000, holding_us.ticker: 200.0}
        with patch.object(service, "_get_current_prices", return_value=prices):
            result = service.evaluate_sell_rules()  # no ticker filter
        assert len(result.results) == 2
        tickers = {r.ticker for r in result.results}
        assert tickers == {holding.ticker, holding_us.ticker}


# =========================================================================
# 5. _compute_trigger_value tests
# =========================================================================


class TestComputeTriggerValue:
    def _make_holding(self, avg_price: float) -> Holding:
        return Holding(ticker="TEST", quantity=10, avg_price=avg_price, currency="KRW")

    def _make_rule(self, rule_type: str, params: dict) -> SellRule:
        return SellRule(ticker="TEST", rule_type=rule_type, params=params, is_active=True)

    def test_stop_loss_trigger(self):
        h = self._make_holding(100)
        r = self._make_rule("stop_loss", {"pct": -10})
        val = PortfolioService._compute_trigger_value(r, h, None)
        assert val == pytest.approx(90.0)

    def test_take_profit_trigger(self):
        h = self._make_holding(100)
        r = self._make_rule("take_profit", {"pct": 20})
        val = PortfolioService._compute_trigger_value(r, h, None)
        assert val == pytest.approx(120.0)

    def test_trailing_stop_trigger(self):
        h = self._make_holding(100)
        r = self._make_rule("trailing_stop", {"pct": 10})
        val = PortfolioService._compute_trigger_value(r, h, 150.0)
        assert val == pytest.approx(135.0)

    def test_trailing_stop_no_hwm(self):
        h = self._make_holding(100)
        r = self._make_rule("trailing_stop", {"pct": 10})
        val = PortfolioService._compute_trigger_value(r, h, None)
        assert val is None

    def test_holding_period_returns_none(self):
        h = self._make_holding(100)
        r = self._make_rule("holding_period", {"max_days": 90})
        val = PortfolioService._compute_trigger_value(r, h, None)
        assert val is None


# =========================================================================
# 6. API endpoint integration tests (FastAPI TestClient)
# =========================================================================


class TestSellRuleAPIEndpoints:
    """Integration tests for sell rule HTTP endpoints."""

    @pytest.fixture(autouse=True)
    def setup_client(self, db_session):
        """Create FastAPI test client with test DB."""
        from fastapi.testclient import TestClient
        from api.routers.portfolio import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        # Create a service that uses the test DB session
        with patch("api.services.portfolio_service.SessionLocal", return_value=db_session), \
             patch.object(PortfolioService, "_backfill_null_sectors"):
            svc = PortfolioService()

        # Patch get_portfolio_service to return the pre-configured service,
        # AND keep SessionLocal patched for the service's methods
        with patch("api.services.portfolio_service.SessionLocal", return_value=db_session), \
             patch("api.routers.portfolio.get_portfolio_service", return_value=svc), \
             TestClient(app) as client:
            self.client = client
            self.db = db_session
            yield

    def _create_holding(self):
        h = Holding(
            ticker="AAPL", name="Apple", quantity=100,
            avg_price=150.0, currency="USD",
        )
        self.db.add(h)
        self.db.commit()
        return h

    def test_list_rules_empty(self):
        self._create_holding()
        resp = self.client.get("/api/portfolio/holdings/AAPL/sell-rules")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_rule(self):
        self._create_holding()
        resp = self.client.post(
            "/api/portfolio/holdings/AAPL/sell-rules",
            json={"rule_type": "stop_loss", "params": {"pct": -10}},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["rule_type"] == "stop_loss"
        assert data["is_active"] is True

    def test_create_rule_invalid_params(self):
        self._create_holding()
        resp = self.client.post(
            "/api/portfolio/holdings/AAPL/sell-rules",
            json={"rule_type": "stop_loss", "params": {"pct": 10}},
        )
        assert resp.status_code == 422  # Pydantic validation error

    def test_create_rule_nonexistent_holding(self):
        resp = self.client.post(
            "/api/portfolio/holdings/NONE/sell-rules",
            json={"rule_type": "stop_loss", "params": {"pct": -10}},
        )
        assert resp.status_code == 404

    def test_update_rule(self):
        self._create_holding()
        create_resp = self.client.post(
            "/api/portfolio/holdings/AAPL/sell-rules",
            json={"rule_type": "stop_loss", "params": {"pct": -10}},
        )
        rule_id = create_resp.json()["id"]
        resp = self.client.put(
            f"/api/portfolio/sell-rules/{rule_id}",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_update_rule_not_found(self):
        resp = self.client.put(
            "/api/portfolio/sell-rules/9999",
            json={"is_active": False},
        )
        assert resp.status_code == 404

    def test_delete_rule(self):
        self._create_holding()
        create_resp = self.client.post(
            "/api/portfolio/holdings/AAPL/sell-rules",
            json={"rule_type": "take_profit", "params": {"pct": 20}},
        )
        rule_id = create_resp.json()["id"]
        resp = self.client.delete(f"/api/portfolio/sell-rules/{rule_id}")
        assert resp.status_code == 204

    def test_delete_rule_not_found(self):
        resp = self.client.delete("/api/portfolio/sell-rules/9999")
        assert resp.status_code == 404

    def test_evaluate_endpoint(self):
        self._create_holding()
        self.client.post(
            "/api/portfolio/holdings/AAPL/sell-rules",
            json={"rule_type": "stop_loss", "params": {"pct": -10}},
        )
        with patch.object(
            PortfolioService, "_get_current_prices",
            return_value={"AAPL": 120.0},
        ):
            resp = self.client.post("/api/portfolio/sell-rules/evaluate")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "checked_at" in data
