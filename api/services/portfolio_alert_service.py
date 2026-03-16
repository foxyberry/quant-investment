"""
Portfolio alert service — dedup-aware alert recording and Telegram dispatch.
"""

import json
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError

from api.database import SessionLocal
from api.models.portfolio_alert import PortfolioAlertHistory
from api.schemas.portfolio_alert import PortfolioAlertHistoryEntry, PortfolioAlertHistoryResponse

logger = logging.getLogger(__name__)


def _entry_from_row(row: PortfolioAlertHistory) -> PortfolioAlertHistoryEntry:
    return PortfolioAlertHistoryEntry(
        id=row.id,
        ticker=row.ticker,
        signal_type=row.signal_type,
        message=row.message,
        price_at_signal=row.price_at_signal,
        fired_at=row.fired_at.isoformat() if row.fired_at else None,
    )


def is_already_sent_today(ticker: str, signal_type: str) -> bool:
    """Check if the same (ticker, signal_type) alert was already sent today."""
    today = date.today()
    db = SessionLocal()
    try:
        exists = (
            db.query(PortfolioAlertHistory)
            .filter(
                PortfolioAlertHistory.ticker == ticker,
                PortfolioAlertHistory.signal_type == signal_type,
                PortfolioAlertHistory.dedup_date == today,
            )
            .first()
        )
        return exists is not None
    finally:
        db.close()


def record_and_send(
    ticker: str,
    signal_type: str,
    message: str,
    price: Optional[float] = None,
) -> bool:
    """Record alert and send via Telegram. Returns False if already sent today."""
    today = date.today()
    now = datetime.utcnow()  # noqa: DTZ003

    db = SessionLocal()
    try:
        row = PortfolioAlertHistory(
            ticker=ticker,
            signal_type=signal_type,
            message=message,
            price_at_signal=price,
            fired_at=now,
            dedup_date=today,
        )
        db.add(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.debug("Alert already sent today: %s/%s", ticker, signal_type)
        return False
    finally:
        db.close()

    # Dispatch to Telegram
    _send_telegram(message)
    return True


def _send_telegram(message: str) -> None:
    """Send message via Telegram using saved bot settings."""
    try:
        from api.models.broker_credential import BrokerCredential
        from api.services.broker_settings_service import get_broker_settings_service

        svc = get_broker_settings_service()
        view = svc.get_telegram_settings()
        if not (view.enabled and view.has_bot_token and view.chat_id):
            logger.debug("Telegram not configured or disabled, skipping")
            return

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "telegram")
            if row:
                data = json.loads(row.config_json)
                encrypted_token = data.get("bot_token_encrypted", "")
                svc.send_telegram_message(view.chat_id, encrypted_token, message)
                logger.info("Portfolio alert sent via Telegram")
        finally:
            db.close()
    except Exception:
        logger.warning("Failed to send portfolio alert via Telegram", exc_info=True)


def get_history(limit: int = 50) -> PortfolioAlertHistoryResponse:
    """Get recent alert history."""
    limit = max(1, min(limit, 200))
    db = SessionLocal()
    try:
        total = db.query(PortfolioAlertHistory).count()
        rows = (
            db.query(PortfolioAlertHistory)
            .order_by(PortfolioAlertHistory.fired_at.desc())
            .limit(limit)
            .all()
        )
        return PortfolioAlertHistoryResponse(
            alerts=[_entry_from_row(r) for r in rows],
            total_count=total,
        )
    finally:
        db.close()
