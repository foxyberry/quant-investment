"""
Strategy Webhook Service.

CRUD operations for webhook configurations and async event dispatching
with HMAC signatures and exponential backoff retry.
"""

import hashlib
import hmac
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api.database import SessionLocal
from api.models.strategy import Strategy
from api.models.strategy_webhook import StrategyWebhook
from api.schemas.strategy_webhook import (
    WebhookCreateRequest,
    WebhookEventPayload,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdateRequest,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1  # seconds


def _to_response(wh: StrategyWebhook) -> WebhookResponse:
    return WebhookResponse(
        id=wh.id,
        strategy_id=wh.strategy_id,
        url=wh.url,
        events=wh.events or [],
        has_secret=bool(wh.secret),
        active=wh.active,
        created_at=wh.created_at.isoformat() if wh.created_at else None,
        updated_at=wh.updated_at.isoformat() if wh.updated_at else None,
    )


def list_webhooks(strategy_id: str) -> WebhookListResponse:
    """List all webhooks for a strategy."""
    db = SessionLocal()
    try:
        webhooks = (
            db.query(StrategyWebhook)
            .filter(StrategyWebhook.strategy_id == strategy_id)
            .order_by(StrategyWebhook.created_at)
            .all()
        )
        return WebhookListResponse(
            strategy_id=strategy_id,
            webhooks=[_to_response(w) for w in webhooks],
            total_count=len(webhooks),
        )
    finally:
        db.close()


def create_webhook(strategy_id: str, data: WebhookCreateRequest) -> Optional[WebhookResponse]:
    """Create a new webhook for a strategy. Returns None if strategy not found."""
    db = SessionLocal()
    try:
        if not db.query(Strategy).filter(Strategy.id == strategy_id).first():
            return None
        wh = StrategyWebhook(
            strategy_id=strategy_id,
            url=data.url,
            events=data.events,
            secret=data.secret,
            active=data.active,
        )
        db.add(wh)
        db.commit()
        db.refresh(wh)
        return _to_response(wh)
    finally:
        db.close()


def get_webhook(strategy_id: str, webhook_id: int) -> Optional[WebhookResponse]:
    """Get a specific webhook."""
    db = SessionLocal()
    try:
        wh = (
            db.query(StrategyWebhook)
            .filter(
                StrategyWebhook.id == webhook_id,
                StrategyWebhook.strategy_id == strategy_id,
            )
            .first()
        )
        return _to_response(wh) if wh else None
    finally:
        db.close()


def update_webhook(
    strategy_id: str, webhook_id: int, data: WebhookUpdateRequest
) -> Optional[WebhookResponse]:
    """Update a webhook configuration."""
    db = SessionLocal()
    try:
        wh = (
            db.query(StrategyWebhook)
            .filter(
                StrategyWebhook.id == webhook_id,
                StrategyWebhook.strategy_id == strategy_id,
            )
            .first()
        )
        if not wh:
            return None
        if data.url is not None:
            wh.url = data.url
        if data.events is not None:
            wh.events = data.events
        if "secret" in data.model_fields_set:
            wh.secret = data.secret
        if data.active is not None:
            wh.active = data.active
        db.commit()
        db.refresh(wh)
        return _to_response(wh)
    finally:
        db.close()


def delete_webhook(strategy_id: str, webhook_id: int) -> bool:
    """Delete a webhook. Returns True if deleted."""
    db = SessionLocal()
    try:
        wh = (
            db.query(StrategyWebhook)
            .filter(
                StrategyWebhook.id == webhook_id,
                StrategyWebhook.strategy_id == strategy_id,
            )
            .first()
        )
        if not wh:
            return False
        db.delete(wh)
        db.commit()
        return True
    finally:
        db.close()


def _compute_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def _send_webhook(url: str, payload: dict, secret: Optional[str]) -> bool:
    """Send webhook with retry logic. Returns True if successful."""
    import urllib.request
    import urllib.error

    payload_bytes = json.dumps(payload, default=str).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        sig = _compute_signature(payload_bytes, secret)
        headers["X-Webhook-Signature"] = f"sha256={sig}"

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                url, data=payload_bytes, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status < 300:
                    return True
                logger.warning(
                    "Webhook %s returned status %d (attempt %d/%d)",
                    url, resp.status, attempt + 1, MAX_RETRIES,
                )
        except Exception as e:
            logger.warning(
                "Webhook %s failed (attempt %d/%d): %s",
                url, attempt + 1, MAX_RETRIES, e,
            )
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_BASE_DELAY * (2 ** attempt))

    logger.error("Webhook %s failed after %d attempts", url, MAX_RETRIES)
    return False


def dispatch_event(
    strategy_id: str,
    strategy_name: str,
    event: str,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """Dispatch a webhook event to all matching active webhooks (async).

    This fires off delivery in a background thread so the caller
    is not blocked.
    """
    db = SessionLocal()
    try:
        webhooks = (
            db.query(StrategyWebhook)
            .filter(
                StrategyWebhook.strategy_id == strategy_id,
                StrategyWebhook.active.is_(True),
            )
            .all()
        )

        targets = []
        for wh in webhooks:
            if event in (wh.events or []):
                targets.append((wh.url, wh.secret))

        if not targets:
            return

        payload = WebhookEventPayload(
            event=event,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data or {},
        ).model_dump()

    finally:
        db.close()

    def _deliver():
        for url, secret in targets:
            _send_webhook(url, payload, secret)

    thread = threading.Thread(target=_deliver, daemon=True)
    thread.start()
