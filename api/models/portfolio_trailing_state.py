"""
SQLAlchemy model for portfolio-wide trailing stop high-water marks.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String

from api.database import Base


class PortfolioTrailingState(Base):
    """Persisted high-water mark for config-driven trailing stop evaluation."""

    __tablename__ = "portfolio_trailing_state"

    ticker = Column(String(32), primary_key=True)
    high_watermark = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
