"""Tests for strategy alert service."""

from unittest.mock import patch

import pytest

from api.schemas.strategy_alert import AlertConfigUpsertRequest


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from api.database import Base
    import api.models.strategy  # noqa: F401
    import api.models.strategy_alert  # noqa: F401

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def patch_session(db_session):
    """Patch SessionLocal in the alert service module."""
    with patch(
        "api.services.strategy_alert_service.SessionLocal",
        return_value=db_session,
    ):
        yield db_session


@pytest.fixture
def strategy_row(db_session):
    """Insert a test strategy into the DB."""
    from api.models.strategy import Strategy

    s = Strategy(id="test-strat-1", name="Test Strategy", graph={"nodes": [], "edges": []})
    db_session.add(s)
    db_session.commit()
    return s


class TestAlertConfigCRUD:
    """Tests for alert configuration CRUD."""

    def test_upsert_creates_config(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import upsert_alert_config

        req = AlertConfigUpsertRequest(
            enabled=True,
            interval_minutes=30,
            channels=["webhook"],
            tickers=["AAPL", "MSFT"],
        )
        result = upsert_alert_config("test-strat-1", req)
        assert result.strategy_id == "test-strat-1"
        assert result.enabled is True
        assert result.interval_minutes == 30
        assert result.channels == ["webhook"]
        assert result.tickers == ["AAPL", "MSFT"]

    def test_upsert_updates_existing(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import upsert_alert_config

        upsert_alert_config(
            "test-strat-1",
            AlertConfigUpsertRequest(tickers=["AAPL"]),
        )
        updated = upsert_alert_config(
            "test-strat-1",
            AlertConfigUpsertRequest(
                enabled=False,
                interval_minutes=120,
                tickers=["TSLA", "GOOG"],
            ),
        )
        assert updated.enabled is False
        assert updated.interval_minutes == 120
        assert updated.tickers == ["TSLA", "GOOG"]

    def test_get_config(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import (
            get_alert_config,
            upsert_alert_config,
        )

        upsert_alert_config(
            "test-strat-1",
            AlertConfigUpsertRequest(tickers=["AAPL"]),
        )
        result = get_alert_config("test-strat-1")
        assert result is not None
        assert result.tickers == ["AAPL"]

    def test_get_config_not_found(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import get_alert_config

        result = get_alert_config("test-strat-1")
        assert result is None

    def test_delete_config(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import (
            delete_alert_config,
            get_alert_config,
            upsert_alert_config,
        )

        upsert_alert_config(
            "test-strat-1",
            AlertConfigUpsertRequest(tickers=["AAPL"]),
        )
        assert delete_alert_config("test-strat-1") is True
        assert get_alert_config("test-strat-1") is None

    def test_delete_config_not_found(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import delete_alert_config

        assert delete_alert_config("test-strat-1") is False


class TestAlertHistory:
    """Tests for alert history recording and retrieval."""

    def test_record_and_retrieve_alert(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import (
            get_alert_history,
            record_alert,
        )

        record_alert(
            strategy_id="test-strat-1",
            ticker="AAPL",
            matched_conditions=["rsi_oversold", "ma_cross_up"],
            price_at_signal=150.25,
        )
        history = get_alert_history("test-strat-1")
        assert history.total_count == 1
        assert len(history.alerts) == 1
        alert = history.alerts[0]
        assert alert.ticker == "AAPL"
        assert alert.matched_conditions == ["rsi_oversold", "ma_cross_up"]
        assert alert.price_at_signal == 150.25

    def test_history_ordered_by_fired_at_desc(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import (
            get_alert_history,
            record_alert,
        )

        record_alert("test-strat-1", "AAPL", ["rsi_oversold"])
        record_alert("test-strat-1", "MSFT", ["ma_cross_up"])
        record_alert("test-strat-1", "GOOG", ["macd_cross_up"])

        history = get_alert_history("test-strat-1")
        assert history.total_count == 3
        # Most recent first
        assert history.alerts[0].ticker == "GOOG"

    def test_history_limit(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import (
            get_alert_history,
            record_alert,
        )

        for i in range(5):
            record_alert("test-strat-1", f"TICK{i}", ["cond"])

        history = get_alert_history("test-strat-1", limit=3)
        assert len(history.alerts) == 3
        assert history.total_count == 5

    def test_empty_history(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import get_alert_history

        history = get_alert_history("test-strat-1")
        assert history.total_count == 0
        assert history.alerts == []


class TestAlertValidation:
    """Tests for alert schema validation."""

    def test_invalid_channel(self):
        with pytest.raises(Exception):
            AlertConfigUpsertRequest(
                channels=["invalid_channel"],
                tickers=["AAPL"],
            )

    def test_empty_tickers(self):
        with pytest.raises(Exception):
            AlertConfigUpsertRequest(
                tickers=[],
            )

    def test_interval_too_low(self):
        with pytest.raises(Exception):
            AlertConfigUpsertRequest(
                interval_minutes=1,
                tickers=["AAPL"],
            )

    def test_ticker_normalization(self):
        req = AlertConfigUpsertRequest(tickers=["  aapl  ", "msft"])
        assert req.tickers == ["AAPL", "MSFT"]

    def test_blank_tickers_rejected(self):
        with pytest.raises(Exception, match="non-blank"):
            AlertConfigUpsertRequest(tickers=["  ", ""])

    def test_upsert_nonexistent_strategy(self, patch_session):
        from api.services.strategy_alert_service import upsert_alert_config

        req = AlertConfigUpsertRequest(tickers=["AAPL"])
        result = upsert_alert_config("nonexistent-id", req)
        assert result is None

    def test_history_limit_clamped(self, patch_session, strategy_row):
        from api.services.strategy_alert_service import (
            get_alert_history,
            record_alert,
        )

        for i in range(5):
            record_alert("test-strat-1", f"T{i}", ["cond"])

        # Negative limit clamped to 1
        history = get_alert_history("test-strat-1", limit=-10)
        assert len(history.alerts) == 1

        # Excessive limit clamped to max_limit
        history = get_alert_history("test-strat-1", limit=9999)
        assert len(history.alerts) == 5  # all 5 returned (within 200 cap)
