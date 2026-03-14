"""Tests for strategy webhook service."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

from api.schemas.strategy_webhook import WebhookCreateRequest, WebhookUpdateRequest


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from api.database import Base
    import api.models.strategy  # noqa: F401
    import api.models.strategy_webhook  # noqa: F401

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def patch_session(db_session):
    """Patch SessionLocal in the webhook service module."""
    with patch(
        "api.services.strategy_webhook_service.SessionLocal",
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


class TestWebhookCRUD:
    """Tests for webhook CRUD operations."""

    def test_create_webhook(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import create_webhook

        req = WebhookCreateRequest(
            url="https://example.com/webhook",
            events=["status_changed"],
            secret="mysecret",
        )
        result = create_webhook("test-strat-1", req)
        assert result.strategy_id == "test-strat-1"
        assert result.url == "https://example.com/webhook"
        assert result.events == ["status_changed"]
        assert result.has_secret is True
        assert result.active is True

    def test_list_webhooks(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import create_webhook, list_webhooks

        create_webhook(
            "test-strat-1",
            WebhookCreateRequest(url="https://a.com/hook", events=["status_changed"]),
        )
        create_webhook(
            "test-strat-1",
            WebhookCreateRequest(url="https://b.com/hook", events=["backtest_completed"]),
        )
        result = list_webhooks("test-strat-1")
        assert result.total_count == 2
        assert len(result.webhooks) == 2

    def test_list_empty(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import list_webhooks

        result = list_webhooks("test-strat-1")
        assert result.total_count == 0

    def test_get_webhook(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import create_webhook, get_webhook

        created = create_webhook(
            "test-strat-1",
            WebhookCreateRequest(url="https://a.com/hook", events=["status_changed"]),
        )
        result = get_webhook("test-strat-1", created.id)
        assert result is not None
        assert result.url == "https://a.com/hook"

    def test_get_webhook_not_found(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import get_webhook

        result = get_webhook("test-strat-1", 999)
        assert result is None

    def test_update_webhook(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import create_webhook, update_webhook

        created = create_webhook(
            "test-strat-1",
            WebhookCreateRequest(url="https://a.com/hook", events=["status_changed"]),
        )
        updated = update_webhook(
            "test-strat-1",
            created.id,
            WebhookUpdateRequest(url="https://new.com/hook", active=False),
        )
        assert updated is not None
        assert updated.url == "https://new.com/hook"
        assert updated.active is False

    def test_update_webhook_not_found(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import update_webhook

        result = update_webhook(
            "test-strat-1", 999, WebhookUpdateRequest(active=False)
        )
        assert result is None

    def test_delete_webhook(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import (
            create_webhook,
            delete_webhook,
            list_webhooks,
        )

        created = create_webhook(
            "test-strat-1",
            WebhookCreateRequest(url="https://a.com/hook", events=["status_changed"]),
        )
        assert delete_webhook("test-strat-1", created.id) is True
        assert list_webhooks("test-strat-1").total_count == 0

    def test_delete_webhook_not_found(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import delete_webhook

        assert delete_webhook("test-strat-1", 999) is False

    def test_webhook_without_secret(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import create_webhook

        req = WebhookCreateRequest(
            url="https://a.com/hook",
            events=["backtest_completed"],
        )
        result = create_webhook("test-strat-1", req)
        assert result.has_secret is False


class TestWebhookValidation:
    """Tests for webhook schema validation."""

    def test_invalid_url(self):
        with pytest.raises(Exception):
            WebhookCreateRequest(url="not-a-url", events=["status_changed"])

    def test_invalid_event(self):
        with pytest.raises(Exception):
            WebhookCreateRequest(
                url="https://a.com/hook", events=["nonexistent_event"]
            )

    def test_empty_events(self):
        with pytest.raises(Exception):
            WebhookCreateRequest(url="https://a.com/hook", events=[])


    def test_ssrf_localhost(self):
        with pytest.raises(Exception, match="internal"):
            WebhookCreateRequest(
                url="http://localhost:8080/hook", events=["status_changed"]
            )

    def test_ssrf_private_ip(self):
        with pytest.raises(Exception, match="internal"):
            WebhookCreateRequest(
                url="http://192.168.1.1/hook", events=["status_changed"]
            )

    def test_ssrf_metadata_ip(self):
        with pytest.raises(Exception, match="internal"):
            WebhookCreateRequest(
                url="http://169.254.169.254/latest/meta-data",
                events=["status_changed"],
            )

    def test_ssrf_loopback_ip(self):
        with pytest.raises(Exception, match="internal"):
            WebhookCreateRequest(
                url="http://127.0.0.1/hook", events=["status_changed"]
            )

    def test_create_webhook_nonexistent_strategy(self, patch_session):
        from api.services.strategy_webhook_service import create_webhook

        req = WebhookCreateRequest(
            url="https://example.com/hook", events=["status_changed"]
        )
        result = create_webhook("nonexistent-id", req)
        assert result is None

    def test_update_webhook_remove_secret(self, patch_session, strategy_row):
        from api.services.strategy_webhook_service import create_webhook, update_webhook

        created = create_webhook(
            "test-strat-1",
            WebhookCreateRequest(
                url="https://a.com/hook",
                events=["status_changed"],
                secret="mysecret",
            ),
        )
        assert created.has_secret is True
        updated = update_webhook(
            "test-strat-1",
            created.id,
            WebhookUpdateRequest(secret=None),
        )
        assert updated is not None
        assert updated.has_secret is False


class TestWebhookDispatcher:
    """Tests for webhook event dispatching."""

    def test_compute_signature(self):
        from api.services.strategy_webhook_service import _compute_signature

        payload = b'{"event":"test"}'
        secret = "mysecret"
        sig = _compute_signature(payload, secret)
        expected = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        assert sig == expected

    @patch("api.services.strategy_webhook_service._send_webhook")
    def test_dispatch_event_calls_matching_webhooks(
        self, mock_send, patch_session, strategy_row
    ):
        from api.services.strategy_webhook_service import (
            create_webhook,
            dispatch_event,
        )

        create_webhook(
            "test-strat-1",
            WebhookCreateRequest(
                url="https://a.com/hook",
                events=["status_changed"],
                secret="sec1",
            ),
        )
        create_webhook(
            "test-strat-1",
            WebhookCreateRequest(
                url="https://b.com/hook",
                events=["backtest_completed"],
            ),
        )

        dispatch_event(
            strategy_id="test-strat-1",
            strategy_name="Test Strategy",
            event="status_changed",
            data={"old_status": "draft", "new_status": "backtested"},
        )

        # Wait for background thread
        import time
        time.sleep(0.5)

        # Only the first webhook matches status_changed
        assert mock_send.call_count == 1
        call_args = mock_send.call_args
        assert call_args[0][0] == "https://a.com/hook"
        payload = call_args[0][1]
        assert payload["event"] == "status_changed"
        assert payload["strategy_id"] == "test-strat-1"
        assert call_args[0][2] == "sec1"

    @patch("api.services.strategy_webhook_service._send_webhook")
    def test_dispatch_skips_inactive_webhooks(
        self, mock_send, patch_session, strategy_row
    ):
        from api.services.strategy_webhook_service import (
            create_webhook,
            dispatch_event,
            update_webhook,
        )

        created = create_webhook(
            "test-strat-1",
            WebhookCreateRequest(
                url="https://a.com/hook",
                events=["status_changed"],
            ),
        )
        update_webhook(
            "test-strat-1",
            created.id,
            WebhookUpdateRequest(active=False),
        )

        dispatch_event(
            strategy_id="test-strat-1",
            strategy_name="Test Strategy",
            event="status_changed",
        )

        import time
        time.sleep(0.5)
        mock_send.assert_not_called()

    @patch("api.services.strategy_webhook_service._send_webhook")
    def test_dispatch_no_matching_event(
        self, mock_send, patch_session, strategy_row
    ):
        from api.services.strategy_webhook_service import (
            create_webhook,
            dispatch_event,
        )

        create_webhook(
            "test-strat-1",
            WebhookCreateRequest(
                url="https://a.com/hook",
                events=["backtest_completed"],
            ),
        )

        dispatch_event(
            strategy_id="test-strat-1",
            strategy_name="Test Strategy",
            event="status_changed",
        )

        import time
        time.sleep(0.5)
        mock_send.assert_not_called()
