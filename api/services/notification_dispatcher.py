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
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from api.database import SessionLocal

logger = logging.getLogger(__name__)

# Slack webhook URL must match this pattern (SSRF prevention)
_SLACK_WEBHOOK_PATTERN = re.compile(r"^https://hooks\.slack\.com/services/.+")

# Rate limit: minimum seconds between Slack messages
_SLACK_RATE_LIMIT_SEC = 1.0
_last_slack_send_time: float = 0.0


# ── Block Kit helpers ──────────────────────────────────────────────────────────


def _to_slack_mrkdwn(text: str) -> str:
    """Convert markdown inline formatting to Slack mrkdwn syntax."""
    # **bold** → *bold*
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)
    # *italic* (not already bold) → _italic_
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"_\1_", text)
    return text


def _split_text(text: str, max_len: int = 2900) -> list[str]:
    """Split text into chunks ≤ max_len, preferring newline boundaries."""
    chunks: list[str] = []
    while len(text) > max_len:
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def md_to_slack_blocks(content: str) -> List[dict]:
    """
    Convert report markdown to Slack Block Kit blocks.

    Mapping:
      ## heading  → header block
      ### heading → section *bold*
      #### heading → context mrkdwn
      | table |   → section fields (2-column grid, max 10 fields per section)
      ---         → divider
      > quote     → context block
      text        → section mrkdwn (≤2900 chars, split if needed)
    """
    blocks: list[dict] = []
    lines = content.split("\n")
    text_buffer: list[str] = []
    table_header: list[str] | None = None
    table_rows: list[list[str]] = []

    def flush_text() -> None:
        nonlocal text_buffer
        if not text_buffer:
            return
        joined = "\n".join(text_buffer).strip()
        text_buffer = []
        if not joined:
            return
        for chunk in _split_text(_to_slack_mrkdwn(joined)):
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk}})

    def flush_table() -> None:
        nonlocal table_header, table_rows
        if not table_header:
            return
        # Build fields list: header row (bolded) + data rows, 2 cols each
        fields: list[dict] = []
        for h in table_header:
            fields.append({"type": "mrkdwn", "text": f"*{h.strip()}*"})
        for row in table_rows:
            for cell in row:
                fields.append({"type": "mrkdwn", "text": _to_slack_mrkdwn(cell.strip()) or "-"})
        # Slack allows max 10 fields per section block
        for i in range(0, len(fields), 10):
            blocks.append({"type": "section", "fields": fields[i : i + 10]})
        table_header = None
        table_rows.clear()

    for line in lines:
        stripped = line.strip()

        if line.startswith("## "):
            flush_text(); flush_table()
            blocks.append({
                "type": "header",
                "text": {"type": "plain_text", "text": line[3:].strip(), "emoji": True},
            })
            continue

        if line.startswith("### "):
            flush_text(); flush_table()
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{_to_slack_mrkdwn(line[4:].strip())}*"},
            })
            continue

        if line.startswith("#### "):
            flush_text(); flush_table()
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": _to_slack_mrkdwn(line[5:].strip())}],
            })
            continue

        if re.match(r"^-{3,}$", stripped):
            flush_text(); flush_table()
            blocks.append({"type": "divider"})
            continue

        if line.startswith("> "):
            flush_text(); flush_table()
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": _to_slack_mrkdwn(line[2:])}],
            })
            continue

        if line.startswith("|") and line.endswith("|"):
            flush_text()
            if re.match(r"^[\s|:-]+$", line):  # separator row
                continue
            cells = line[1:-1].split("|")
            if table_header is None:
                table_header = cells
            else:
                table_rows.append(cells)
            continue

        # Non-table line after a table
        if table_header is not None:
            flush_table()

        if not stripped:
            flush_text()
            continue

        text_buffer.append(line)

    flush_text()
    flush_table()
    return blocks


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
    """POST a single JSON payload to the Slack webhook. Returns True on 200."""
    global _last_slack_send_time
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

    _CHUNK = 50
    chunks = [blocks[i : i + _CHUNK] for i in range(0, max(1, len(blocks)), _CHUNK)]
    for idx, chunk in enumerate(chunks):
        payload: dict = {
            "text": fallback_text if idx == 0 else "...",
            "blocks": chunk,
        }
        ok = _post_slack(webhook_url, payload)
        if not ok:
            logger.warning("Slack block chunk %d/%d failed", idx + 1, len(chunks))
            return False
        if idx < len(chunks) - 1:
            time.sleep(1.0)  # avoid burst rate-limit between chunks

    logger.info("Report sent via Slack Block Kit (%d blocks, %d chunk(s))", len(blocks), len(chunks))
    return True
