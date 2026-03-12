"""
SQLAlchemy model for the macro_history table.

Stores periodic macro monitor snapshots (FX, futures, investor flow, signal)
so that timeline data persists across server restarts.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from api.database import Base


class MacroHistory(Base):
    __tablename__ = "macro_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    fx_value = Column(Float, nullable=True)
    futures_value = Column(Float, nullable=True)
    foreign_net = Column(Float, nullable=True)
    macro_score = Column(Float, nullable=True)
    regime = Column(String(32), nullable=True, default="unknown")
    vix = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
