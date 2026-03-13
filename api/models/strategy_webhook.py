"""
SQLAlchemy model for the strategy_webhooks table.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from api.database import Base


class StrategyWebhook(Base):
    __tablename__ = "strategy_webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(32), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    events = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    secret = Column(String(128), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
