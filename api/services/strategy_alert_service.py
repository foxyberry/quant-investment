"""
Strategy Alert Service.

Manages alert configurations and alert history for live signal monitoring.
"""

import logging
from typing import Optional

from api.database import SessionLocal
from api.models.strategy import Strategy
from api.models.strategy_alert import StrategyAlertConfig, StrategyAlertHistory
from api.schemas.strategy_alert import (
    AlertConfigResponse,
    AlertConfigUpsertRequest,
    AlertHistoryEntry,
    AlertHistoryResponse,
)

logger = logging.getLogger(__name__)


def _config_to_response(cfg: StrategyAlertConfig) -> AlertConfigResponse:
    return AlertConfigResponse(
        id=cfg.id,
        strategy_id=cfg.strategy_id,
        enabled=cfg.enabled,
        interval_minutes=cfg.interval_minutes,
        channels=cfg.channels or [],
        tickers=cfg.tickers or [],
        created_at=cfg.created_at.isoformat() if cfg.created_at else None,
        updated_at=cfg.updated_at.isoformat() if cfg.updated_at else None,
    )


def _history_to_entry(h: StrategyAlertHistory) -> AlertHistoryEntry:
    return AlertHistoryEntry(
        id=h.id,
        strategy_id=h.strategy_id,
        ticker=h.ticker,
        matched_conditions=h.matched_conditions or [],
        price_at_signal=h.price_at_signal,
        fired_at=h.fired_at.isoformat() if h.fired_at else None,
    )


def get_alert_config(strategy_id: str) -> Optional[AlertConfigResponse]:
    """Get alert configuration for a strategy."""
    db = SessionLocal()
    try:
        cfg = (
            db.query(StrategyAlertConfig)
            .filter(StrategyAlertConfig.strategy_id == strategy_id)
            .first()
        )
        return _config_to_response(cfg) if cfg else None
    finally:
        db.close()


def upsert_alert_config(
    strategy_id: str, data: AlertConfigUpsertRequest
) -> Optional[AlertConfigResponse]:
    """Create or update alert configuration. Returns None if strategy not found."""
    db = SessionLocal()
    try:
        if not db.query(Strategy).filter(Strategy.id == strategy_id).first():
            return None
        cfg = (
            db.query(StrategyAlertConfig)
            .filter(StrategyAlertConfig.strategy_id == strategy_id)
            .first()
        )
        if cfg:
            cfg.enabled = data.enabled
            cfg.interval_minutes = data.interval_minutes
            cfg.channels = data.channels
            cfg.tickers = data.tickers
        else:
            cfg = StrategyAlertConfig(
                strategy_id=strategy_id,
                enabled=data.enabled,
                interval_minutes=data.interval_minutes,
                channels=data.channels,
                tickers=data.tickers,
            )
            db.add(cfg)
        db.commit()
        db.refresh(cfg)
        return _config_to_response(cfg)
    finally:
        db.close()


def delete_alert_config(strategy_id: str) -> bool:
    """Delete alert configuration. Returns True if deleted."""
    db = SessionLocal()
    try:
        cfg = (
            db.query(StrategyAlertConfig)
            .filter(StrategyAlertConfig.strategy_id == strategy_id)
            .first()
        )
        if not cfg:
            return False
        db.delete(cfg)
        db.commit()
        return True
    finally:
        db.close()


def get_alert_history(
    strategy_id: str, limit: int = 50, max_limit: int = 200
) -> AlertHistoryResponse:
    limit = max(1, min(limit, max_limit))
    """Get alert history for a strategy."""
    db = SessionLocal()
    try:
        total = (
            db.query(StrategyAlertHistory)
            .filter(StrategyAlertHistory.strategy_id == strategy_id)
            .count()
        )
        alerts = (
            db.query(StrategyAlertHistory)
            .filter(StrategyAlertHistory.strategy_id == strategy_id)
            .order_by(StrategyAlertHistory.fired_at.desc())
            .limit(limit)
            .all()
        )
        return AlertHistoryResponse(
            strategy_id=strategy_id,
            alerts=[_history_to_entry(a) for a in alerts],
            total_count=total,
        )
    finally:
        db.close()


def record_alert(
    strategy_id: str,
    ticker: str,
    matched_conditions: list,
    price_at_signal: Optional[float] = None,
) -> AlertHistoryEntry:
    """Record a fired alert in history."""
    db = SessionLocal()
    try:
        entry = StrategyAlertHistory(
            strategy_id=strategy_id,
            ticker=ticker,
            matched_conditions=matched_conditions,
            price_at_signal=price_at_signal,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _history_to_entry(entry)
    finally:
        db.close()


def fire_alert(
    strategy_id: str,
    ticker: str,
    matched_conditions: list,
    price_at_signal: Optional[float] = None,
    channels: Optional[list[str]] = None,
) -> AlertHistoryEntry:
    """Record alert and dispatch to configured channels."""
    entry = record_alert(strategy_id, ticker, matched_conditions, price_at_signal)
    channels = channels or []

    if channels:
        try:
            from api.services.notification_dispatcher import dispatch

            conditions_str = ", ".join(str(c) for c in matched_conditions)
            price_str = f"{price_at_signal}" if price_at_signal is not None else "N/A"
            msg = (
                f"Signal: {ticker}\n"
                f"Conditions: {conditions_str}\n"
                f"Price: {price_str}"
            )
            dispatch(msg, channels=channels)
        except Exception:
            logger.warning(
                "Failed to dispatch alert for %s/%s",
                strategy_id,
                ticker,
                exc_info=True,
            )

    return entry
