"""Tests for Telegram notification settings.

Verifies the service layer and schema validation for Telegram configuration,
following the same patterns as Tiger/IBKR broker settings.
Tests the service directly to avoid the complex app lifespan dependencies.
"""

from __future__ import annotations

import base64
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base
from api.models.broker_credential import BrokerCredential  # noqa: F401 — register model


def _generate_fernet_key() -> str:
    """Return a fresh URL-safe base64 Fernet key (32 random bytes)."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    """Provide a valid Fernet key for every test in this module."""
    key = _generate_fernet_key()
    monkeypatch.setenv("BROKER_CONFIG_ENCRYPTION_KEY", key)


@pytest.fixture()
def db_session():
    """Provide a fresh in-memory SQLite DB with tables created."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestingSession
    engine.dispose()


@pytest.fixture()
def service(db_session):
    """Return a BrokerSettingsService that uses the test DB."""
    import api.services.broker_settings_service as mod

    orig = mod.SessionLocal
    mod.SessionLocal = db_session
    from api.services.broker_settings_service import BrokerSettingsService

    svc = BrokerSettingsService()
    yield svc
    mod.SessionLocal = orig


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestTelegramSchemas:
    """Pydantic model validation."""

    def test_request_defaults(self):
        from api.schemas.telegram import TelegramSettingsRequest

        req = TelegramSettingsRequest(chat_id="12345")
        assert req.enabled is True
        assert req.bot_token is None

    def test_response_defaults(self):
        from api.schemas.telegram import TelegramSettingsResponse

        resp = TelegramSettingsResponse()
        assert resp.has_bot_token is False
        assert resp.chat_id is None
        assert resp.enabled is False
        assert resp.updated_at is None

    def test_test_response(self):
        from api.schemas.telegram import TelegramTestResponse

        resp = TelegramTestResponse(success=True, message="OK")
        assert resp.success is True
        assert resp.message == "OK"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestGetTelegramSettings:
    """BrokerSettingsService.get_telegram_settings()"""

    def test_empty_settings(self, service):
        view = service.get_telegram_settings()
        assert view.has_bot_token is False
        assert view.chat_id is None
        assert view.enabled is False
        assert view.updated_at is None


class TestSaveTelegramSettings:
    """BrokerSettingsService.save_telegram_settings()"""

    def test_save_and_get(self, service):
        view = service.save_telegram_settings(
            {"bot_token": "123:ABC", "chat_id": "99999", "enabled": True}
        )
        assert view.has_bot_token is True
        assert view.chat_id == "99999"
        assert view.enabled is True
        assert view.updated_at is not None

        # Verify via get
        view2 = service.get_telegram_settings()
        assert view2.has_bot_token is True
        assert view2.chat_id == "99999"

    def test_save_without_chat_id_fails(self, service):
        with pytest.raises(ValueError, match="chat_id is required"):
            service.save_telegram_settings(
                {"bot_token": "123:ABC", "chat_id": "", "enabled": True}
            )

    def test_update_preserves_token(self, service):
        """When bot_token is empty on update, the existing encrypted token is kept."""
        service.save_telegram_settings(
            {"bot_token": "123:ABC", "chat_id": "99999", "enabled": True}
        )

        # Update without token (empty string)
        view = service.save_telegram_settings(
            {"bot_token": "", "chat_id": "88888", "enabled": False}
        )
        assert view.has_bot_token is True  # token preserved
        assert view.chat_id == "88888"
        assert view.enabled is False

    def test_save_without_token_first_time_fails(self, service):
        """First save must include bot_token."""
        with pytest.raises(ValueError, match="bot_token is required"):
            service.save_telegram_settings(
                {"chat_id": "99999", "enabled": True}
            )

    def test_update_replaces_token(self, service):
        """Providing a new bot_token replaces the existing one."""
        service.save_telegram_settings(
            {"bot_token": "old:TOKEN", "chat_id": "99999", "enabled": True}
        )
        service.save_telegram_settings(
            {"bot_token": "new:TOKEN", "chat_id": "99999", "enabled": True}
        )
        view = service.get_telegram_settings()
        assert view.has_bot_token is True
        assert view.chat_id == "99999"


class TestSendTelegramMessage:
    """BrokerSettingsService.send_telegram_message()"""

    @patch("api.services.broker_settings_service.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen, service):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok":true}'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        # Save settings to get an encrypted token
        service.save_telegram_settings(
            {"bot_token": "123:ABC", "chat_id": "99999", "enabled": True}
        )

        # Get encrypted token from DB
        from api.services.broker_settings_service import SessionLocal

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "telegram")
            data = json.loads(row.config_json)
            encrypted_token = data["bot_token_encrypted"]
        finally:
            db.close()

        result = service.send_telegram_message("99999", encrypted_token)
        assert result is True
        mock_urlopen.assert_called_once()

    @patch("api.services.broker_settings_service.urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen, service):
        mock_urlopen.side_effect = Exception("Connection refused")

        service.save_telegram_settings(
            {"bot_token": "123:ABC", "chat_id": "99999", "enabled": True}
        )

        from api.services.broker_settings_service import SessionLocal

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "telegram")
            data = json.loads(row.config_json)
            encrypted_token = data["bot_token_encrypted"]
        finally:
            db.close()

        result = service.send_telegram_message("99999", encrypted_token)
        assert result is False

    @patch("api.services.broker_settings_service.urllib.request.urlopen")
    def test_custom_message(self, mock_urlopen, service):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok":true}'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        service.save_telegram_settings(
            {"bot_token": "123:ABC", "chat_id": "99999", "enabled": True}
        )

        from api.services.broker_settings_service import SessionLocal

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "telegram")
            data = json.loads(row.config_json)
            encrypted_token = data["bot_token_encrypted"]
        finally:
            db.close()

        result = service.send_telegram_message(
            "99999", encrypted_token, "Custom alert message"
        )
        assert result is True

        # Verify the custom message was sent in the request body
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert body["text"] == "Custom alert message"


class TestValidChannels:
    """VALID_CHANNELS includes telegram."""

    def test_telegram_in_valid_channels(self):
        from api.schemas.strategy_alert import VALID_CHANNELS

        assert "telegram" in VALID_CHANNELS


class TestFireAlert:
    """fire_alert() dispatches to Telegram when configured."""

    @patch("api.services.broker_settings_service.urllib.request.urlopen")
    def test_fire_alert_with_telegram_channel(self, mock_urlopen, service, db_session):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok":true}'
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        # Save Telegram settings
        service.save_telegram_settings(
            {"bot_token": "123:ABC", "chat_id": "99999", "enabled": True}
        )

        # Patch the service singleton and SessionLocal for fire_alert
        import api.services.broker_settings_service as bss

        with (
            patch.object(bss, "_broker_settings_service", service),
            patch("api.services.strategy_alert_service.SessionLocal", db_session),
        ):
            # Need to create the strategy_alert_history table
            from api.models.strategy_alert import (
                StrategyAlertHistory,
            )

            Base.metadata.create_all(bind=db_session.kw["bind"])

            from api.services.strategy_alert_service import fire_alert

            entry = fire_alert(
                strategy_id="test-strat",
                ticker="AAPL",
                matched_conditions=["RSI < 30", "MACD cross"],
                price_at_signal=150.5,
                channels=["telegram"],
            )
            assert entry.ticker == "AAPL"
            assert entry.strategy_id == "test-strat"
            # Telegram message should have been sent
            mock_urlopen.assert_called_once()
