"""
SQLAlchemy models for strategy alerts.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from api.database import Base


class StrategyAlertConfig(Base):
    """Configuration for live signal alerts on a strategy."""

    __tablename__ = "strategy_alert_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(32), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    interval_minutes = Column(Integer, nullable=False, default=60)
    channels = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    tickers = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StrategyAlertHistory(Base):
    """Record of a fired strategy alert."""

    __tablename__ = "strategy_alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(32), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(16), nullable=False)
    matched_conditions = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    price_at_signal = Column(Float, nullable=True)
    fired_at = Column(DateTime, default=datetime.utcnow, index=True)
