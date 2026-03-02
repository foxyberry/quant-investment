"""
SQLAlchemy models for the portfolio tables (holdings + trades + sell rules).
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from api.database import Base


class Holding(Base):
    __tablename__ = "holdings"

    ticker = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False, default="KRW")
    note = Column(Text, nullable=True)
    bought_at = Column(Date, nullable=True)
    sector = Column(String(128), nullable=True)
    industry = Column(String(128), nullable=True)
    country = Column(String(64), nullable=True)
    exchange = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sell_rules = relationship("SellRule", back_populates="holding", cascade="all, delete-orphan")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(32), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    trade_type = Column(String(8), nullable=False)  # BUY or SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, nullable=True, default=0)
    tax = Column(Float, nullable=True, default=0)
    realized_pnl = Column(Float, nullable=True)  # calculated for SELL trades
    avg_price_at_trade = Column(Float, nullable=True)  # avg_price snapshot at sell
    currency = Column(String(8), nullable=False, default="KRW")
    note = Column(Text, nullable=True)
    traded_at = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SellRule(Base):
    """Per-holding sell rule persisted in DB.

    rule_type:
        stop_loss      — sell when pnl_pct <= -params.pct
        take_profit    — sell when pnl_pct >= params.pct
        trailing_stop  — sell when price drops params.pct from high watermark
        holding_period — sell when holding_days >= params.max_days
    """

    __tablename__ = "sell_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(
        String(32),
        ForeignKey("holdings.ticker", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_type = Column(String(32), nullable=False)
    params = Column(Text, nullable=False, default="{}")      # JSON: rule configuration
    state_json = Column(Text, nullable=True)                  # JSON: runtime state (e.g. high_watermark)
    is_active = Column(Boolean, nullable=False, default=True)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    holding = relationship("Holding", back_populates="sell_rules")
