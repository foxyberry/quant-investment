"""
SQLAlchemy model for portfolio alert history with daily dedup.
"""

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text, UniqueConstraint

from api.database import Base


class PortfolioAlertHistory(Base):
    """Record of a fired portfolio alert with daily dedup."""

    __tablename__ = "portfolio_alert_history"
    __table_args__ = (
        UniqueConstraint("ticker", "signal_type", "dedup_date", name="uq_portfolio_alert_dedup"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(32), nullable=False, index=True)
    signal_type = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    price_at_signal = Column(Float, nullable=True)
    fired_at = Column(DateTime, default=datetime.utcnow, index=True)
    dedup_date = Column(Date, default=date.today, nullable=False, index=True)
