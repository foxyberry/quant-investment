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
    channels: Optional[list[str]] = None,
) -> bool:
    """Record alert and send to configured channels. Returns False if already sent today."""
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

    # Dispatch to specified channels (or all enabled if not specified)
    from api.services.notification_dispatcher import dispatch
    dispatch(message, channels=channels)
    return True


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
