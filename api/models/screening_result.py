"""
SQLAlchemy model for the saved_screening_results table.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from api.database import Base


class SavedScreeningResult(Base):
    __tablename__ = "saved_screening_results"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    preset = Column(String(100), nullable=False)
    universes = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    reference_date = Column(String(20), nullable=True)
    total_count = Column(Integer, nullable=False)
    matched_count = Column(Integer, nullable=False)
    elapsed_ms = Column(Float, nullable=True)
    results = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
