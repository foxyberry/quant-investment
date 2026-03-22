"""
Unified notification dispatcher.

Single entry point for dispatching messages to configured channels
(Telegram, Slack). Eliminates duplicated send logic across
portfolio_alert_service and strategy_alert_service.
"""

import json
import logging
import re
import time
import urllib.error
import urllib.request
from typing import Dict, Optional

from api.database import SessionLocal

logger = logging.getLogger(__name__)

# Slack webhook URL must match this pattern (SSRF prevention)
_SLACK_WEBHOOK_PATTERN = re.compile(r"^https://hooks\.slack\.com/services/.+")

# Rate limit: minimum seconds between Slack messages
_SLACK_RATE_LIMIT_SEC = 1.0
_last_slack_send_time: float = 0.0


def dispatch(message: str, channels: Optional[list[str]] = None) -> Dict[str, bool]:
    """Dispatch a message to all enabled notification channels.

    Args:
        message: The message text to send.
        channels: Optional explicit channel list. If None, sends to all
                  enabled channels found in DB settings.

    Returns:
        Dict mapping channel name to success bool, e.g. {"telegram": True, "slack": False}
    """
    results: Dict[str, bool] = {}

    try:
        from api.services.broker_settings_service import get_broker_settings_service
        svc = get_broker_settings_service()
    except Exception:
        logger.warning("Could not load broker settings service", exc_info=True)
        return results

    # Telegram
    if channels is None or "telegram" in channels:
        results["telegram"] = _send_telegram(svc, message)

    # Slack
    if channels is None or "slack" in channels:
        results["slack"] = _send_slack(svc, message)

    return results


def _send_telegram(svc: object, message: str) -> bool:
    """Send via Telegram using saved bot settings."""
    try:
        view = svc.get_telegram_settings()
        if not (view.enabled and view.has_bot_token and view.chat_id):
            logger.debug("Telegram not configured or disabled, skipping")
            return False

        from api.models.broker_credential import BrokerCredential

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "telegram")
            if not row:
                return False
            data = json.loads(row.config_json)
            encrypted_token = data.get("bot_token_encrypted", "")
            svc.send_telegram_message(view.chat_id, encrypted_token, message)
            logger.info("Notification sent via Telegram")
            return True
        finally:
            db.close()
    except Exception:
        logger.warning("Failed to send via Telegram", exc_info=True)
        return False


def _send_slack(svc: object, message: str) -> bool:
    """Send via Slack Incoming Webhook using saved settings."""
    global _last_slack_send_time
    try:
        from api.models.broker_credential import BrokerCredential

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "slack")
            if not row:
                logger.debug("Slack not configured, skipping")
                return False

            data = json.loads(row.config_json)
            if not data.get("enabled", False):
                logger.debug("Slack disabled, skipping")
                return False

            encrypted_url = data.get("webhook_url_encrypted", "")
            if not encrypted_url:
                logger.debug("Slack webhook URL not set, skipping")
                return False

            webhook_url = svc._decrypt(encrypted_url)
        finally:
            db.close()

        # SSRF prevention
        if not _SLACK_WEBHOOK_PATTERN.match(webhook_url):
            logger.warning("Slack webhook URL rejected (SSRF check): %s...", webhook_url[:40])
            return False

        # Rate limit
        now = time.monotonic()
        elapsed = now - _last_slack_send_time
        if elapsed < _SLACK_RATE_LIMIT_SEC:
            time.sleep(_SLACK_RATE_LIMIT_SEC - elapsed)

        payload = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            _last_slack_send_time = time.monotonic()
            logger.info("Notification sent via Slack")
            return resp.status == 200

    except urllib.error.HTTPError as exc:
        if exc.code in (403, 410):
            logger.warning("Slack webhook expired or revoked (HTTP %d)", exc.code)
        else:
            logger.warning("Slack API error: HTTP %d", exc.code)
        return False
    except Exception:
        logger.warning("Failed to send via Slack", exc_info=True)
        return False
