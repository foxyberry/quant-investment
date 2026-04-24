"""
SQLAlchemy models for the portfolio tables (holdings, trades, sell_rules).
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
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


class SellRulePreset(Base):
    __tablename__ = "sell_rule_presets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    rules = Column(_JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    linked_sell_rules = relationship("SellRule", back_populates="preset", passive_deletes=True)


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

    sell_rules = relationship(
        "SellRule", back_populates="holding", cascade="all, delete-orphan",
        passive_deletes=True,
    )


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
    __tablename__ = "sell_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(
        String(32),
        ForeignKey("holdings.ticker", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_type = Column(
        String(32), nullable=False,
    )  # stop_loss | take_profit | trailing_stop | holding_period
    params = Column(_JSON, nullable=False)  # {"pct": -10} etc.
    state_json = Column(_JSON, nullable=True)  # runtime state (e.g. trailing_stop high_watermark)
    preset_id = Column(
        Integer,
        ForeignKey("sell_rule_presets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "rule_type IN ('stop_loss', 'take_profit', 'trailing_stop', 'holding_period')",
            name="ck_sell_rule_type",
        ),
    )
    is_active = Column(Boolean, nullable=False, default=True)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    holding = relationship("Holding", back_populates="sell_rules")
    preset = relationship("SellRulePreset", back_populates="linked_sell_rules")


class PortfolioArchive(Base):
    __tablename__ = "portfolio_archives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)
    total_holdings = Column(Integer, nullable=False, default=0)

    items = relationship(
        "PortfolioArchiveItem",
        back_populates="archive",
        cascade="all, delete-orphan",
    )


class PortfolioArchiveItem(Base):
    __tablename__ = "portfolio_archive_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    archive_id = Column(
        Integer,
        ForeignKey("portfolio_archives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticker = Column(String(32), nullable=False)
    name = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False, default="KRW")
    bought_at = Column(Date, nullable=True)
    sector = Column(String(128), nullable=True)
    industry = Column(String(128), nullable=True)
    country = Column(String(64), nullable=True)
    exchange = Column(String(32), nullable=True)

    archive = relationship("PortfolioArchive", back_populates="items")
