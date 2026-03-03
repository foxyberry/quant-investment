"""
SQLAlchemy models for the watchlist tables (watchlist_items + buy_rules).
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from api.database import Base

_JSON = JSON().with_variant(JSONB, "postgresql")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    target_price = Column(Float, nullable=True)
    note = Column(Text, nullable=True)
    tags = Column(_JSON, nullable=True)  # JSON array of string tags
    added_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    buy_rules = relationship(
        "BuyRule",
        back_populates="watchlist_item",
        cascade="all, delete-orphan",
    )


class BuyRule(Base):
    __tablename__ = "buy_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    watchlist_item_id = Column(
        Integer,
        ForeignKey("watchlist_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_type = Column(String(32), nullable=False)  # target_price, rsi_oversold
    params = Column(_JSON, nullable=False)  # e.g. {"price": 50000} or {"rsi": 30}
    state_json = Column(_JSON, nullable=True)  # evaluation state
    is_active = Column(Boolean, default=True, nullable=False)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    watchlist_item = relationship("WatchlistItem", back_populates="buy_rules")
