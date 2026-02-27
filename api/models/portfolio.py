"""
SQLAlchemy models for the portfolio tables (holdings + trades).
"""

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
