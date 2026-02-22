"""
SQLAlchemy model for the holdings table.
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
