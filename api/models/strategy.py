"""
SQLAlchemy model for the strategies table.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from api.database import Base


VALID_STATUSES = {"draft", "backtested", "validated", "production", "retired"}


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    graph = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    status = Column(String(16), nullable=False, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
