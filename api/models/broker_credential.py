"""Persistent broker credential model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class BrokerCredential(Base):
    """Store broker credential/config blobs with encrypted secret fields."""

    __tablename__ = "broker_credentials"

    broker: Mapped[str] = mapped_column(String(32), primary_key=True)
    account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
