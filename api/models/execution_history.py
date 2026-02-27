"""
SQLAlchemy model for the execution_history table.

Tracks every screening or strategy execution for auditing,
duplicate detection (via fingerprint), and result retrieval.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from api.database import Base


class ExecutionHistory(Base):
    __tablename__ = "execution_history"

    id = Column(String(32), primary_key=True)
    execution_type = Column(String(20), nullable=False)
    preset = Column(String(100), nullable=False)
    universes = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    reference_date = Column(String(20), nullable=True)
    params = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    graph = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    total_count = Column(Integer, nullable=False)
    matched_count = Column(Integer, nullable=False)
    elapsed_ms = Column(Float, nullable=True)
    results = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    strategy_id = Column(String(32), nullable=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
