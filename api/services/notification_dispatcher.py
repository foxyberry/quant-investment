"""
Unified notification dispatcher.

Single entry point for dispatching messages to configured channels
(Telegram, Slack). Eliminates duplicated send logic across
portfolio_alert_service and strategy_alert_service.

Block Kit support:
  dispatch_blocks(blocks, fallback_text, channels) — send Slack Block Kit JSON
  md_to_slack_blocks(markdown) — convert report markdown to Block Kit blocks
"""

import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from api.database import SessionLocal
from api.services.notifications.slack_format import md_to_report_payload, md_to_slack_blocks

logger = logging.getLogger(__name__)

# Slack webhook URL must match this pattern (SSRF prevention)
# Requires alphanumeric path segments after /services/ — blocks path traversal (../) and other tricks
_SLACK_WEBHOOK_PATTERN = re.compile(r"^https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+$")

# Rate limit: minimum seconds between Slack messages
_SLACK_RATE_LIMIT_SEC = 1.0
_last_slack_send_time: float = 0.0
# Lock guards _last_slack_send_time to prevent concurrent calls racing past the rate limiter
_slack_lock = threading.Lock()


def dispatch_report(
    content: str,
    fallback_text: str,
    channels: Optional[list[str]] = None,
) -> Dict[str, bool]:
    """
    Dispatch a report with colored Block Kit attachments per stock section.
    Use this instead of dispatch_blocks for portfolio daily reports.
    """
    results: Dict[str, bool] = {}

    try:
        from api.services.broker_settings_service import get_broker_settings_service
        svc = get_broker_settings_service()
    except Exception:
        logger.warning("Could not load broker settings service", exc_info=True)
        return results

    if channels is None or "telegram" in channels:
        results["telegram"] = _send_telegram(svc, fallback_text)

    if channels is None or "slack" in channels:
        payload = md_to_report_payload(content)
        results["slack"] = _send_slack_payload(svc, payload, fallback_text)

    return results


def dispatch_blocks(
    blocks: List[dict],
    fallback_text: str,
    channels: Optional[list[str]] = None,
) -> Dict[str, bool]:
    """
    Dispatch Slack Block Kit blocks to configured channels.
    Blocks are chunked at 50 per message to respect Slack limits.
    Non-Slack channels fall back to fallback_text.
    """
    results: Dict[str, bool] = {}

    try:
        from api.services.broker_settings_service import get_broker_settings_service
        svc = get_broker_settings_service()
    except Exception:
        logger.warning("Could not load broker settings service", exc_info=True)
        return results

    if channels is None or "telegram" in channels:
        results["telegram"] = _send_telegram(svc, fallback_text)

    if channels is None or "slack" in channels:
        results["slack"] = _send_slack_blocks(svc, blocks, fallback_text)

    return results


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


def _get_slack_webhook(svc: object) -> str | None:
    """Retrieve and validate the Slack webhook URL. Returns None if unavailable."""
    try:
        from api.models.broker_credential import BrokerCredential

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "slack")
            if not row:
                logger.debug("Slack not configured, skipping")
                return None
            data = json.loads(row.config_json)
            if not data.get("enabled", False):
                logger.debug("Slack disabled, skipping")
                return None
            encrypted_url = data.get("webhook_url_encrypted", "")
            if not encrypted_url:
                logger.debug("Slack webhook URL not set, skipping")
                return None
            webhook_url: str = svc._decrypt(encrypted_url)
        finally:
            db.close()
    except Exception:
        logger.warning("Failed to retrieve Slack webhook URL", exc_info=True)
        return None

    if not _SLACK_WEBHOOK_PATTERN.match(webhook_url):
        logger.warning("Slack webhook URL rejected (SSRF check): %s...", webhook_url[:40])
        return None
    return webhook_url


def _post_slack(webhook_url: str, payload: dict) -> bool:
    """POST a single JSON payload to the Slack webhook. Returns True on 200.

    Thread-safe: _slack_lock serialises concurrent callers and protects the
    global _last_slack_send_time rate-limiter against race conditions.
    """
    global _last_slack_send_time
    with _slack_lock:
        now = time.monotonic()
        elapsed = now - _last_slack_send_time
        if elapsed < _SLACK_RATE_LIMIT_SEC:
            time.sleep(_SLACK_RATE_LIMIT_SEC - elapsed)
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                _last_slack_send_time = time.monotonic()
                return resp.status == 200
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 410):
                logger.warning("Slack webhook expired or revoked (HTTP %d)", exc.code)
            else:
                logger.warning("Slack API error: HTTP %d", exc.code)
            return False
        except Exception:
            logger.warning("Failed to send to Slack", exc_info=True)
            return False


def _send_slack(svc: object, message: str) -> bool:
    """Send plain-text message via Slack Incoming Webhook."""
    webhook_url = _get_slack_webhook(svc)
    if not webhook_url:
        return False
    ok = _post_slack(webhook_url, {"text": message})
    if ok:
        logger.info("Notification sent via Slack")
    return ok


def _send_slack_blocks(svc: object, blocks: List[dict], fallback_text: str) -> bool:
    """Send Block Kit blocks via Slack webhook, chunking at 50 blocks per request."""
    webhook_url = _get_slack_webhook(svc)
    if not webhook_url:
        return False

    if not blocks:
        logger.debug("_send_slack_blocks: empty blocks list, skipping")
        return True

    _CHUNK = 50
    chunks = [blocks[i : i + _CHUNK] for i in range(0, len(blocks), _CHUNK)]
    for idx, chunk in enumerate(chunks):
        payload: dict = {"text": fallback_text if idx == 0 else "...", "blocks": chunk}
        ok = _post_slack(webhook_url, payload)
        if not ok:
            logger.warning("Slack block chunk %d/%d failed", idx + 1, len(chunks))
            return False
        if idx < len(chunks) - 1:
            time.sleep(1.0)

    logger.info("Slack Block Kit sent (%d blocks, %d chunk(s))", len(blocks), len(chunks))
    return True


def _send_slack_payload(svc: object, payload: dict, fallback_text: str) -> bool:
    """
    Send a full Slack payload (blocks + attachments) via webhook.
    Sends main blocks first, then attachments in batches (Slack limits: 50 blocks,
    100 attachments per message — we send attachments one per stock for clarity).
    """
    webhook_url = _get_slack_webhook(svc)
    if not webhook_url:
        return False

    main_blocks = payload.get("blocks", [])
    attachments = payload.get("attachments", [])

    # First message: main blocks (header + macro)
    first: dict = {"text": fallback_text}
    if main_blocks:
        first["blocks"] = main_blocks[:50]
    ok = _post_slack(webhook_url, first)
    if not ok:
        return False

    # Subsequent messages: attachments (one batch per Slack call, max 20 attachments each)
    # Note: no explicit time.sleep here — _post_slack's lock-protected rate limiter
    # already enforces _SLACK_RATE_LIMIT_SEC (1 s) between consecutive calls.
    _ATT_CHUNK = 20
    for i in range(0, len(attachments), _ATT_CHUNK):
        chunk = attachments[i : i + _ATT_CHUNK]
        ok = _post_slack(webhook_url, {"text": "...", "attachments": chunk})
        if not ok:
            logger.warning("Slack attachment chunk %d failed", i // _ATT_CHUNK + 1)
            return False

    total_att = len(attachments)
    logger.info(
        "Report sent via Slack Block Kit (%d main blocks, %d colored attachment(s))",
        len(main_blocks), total_att,
    )
    return True
