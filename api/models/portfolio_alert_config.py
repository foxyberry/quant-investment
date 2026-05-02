"""Persistent portfolio alert and sell settings.

Runtime readers use this table as the primary source of truth for:
- portfolio alert settings
- global sell-condition defaults
- technical sell-signal config

At present, only alert settings are mutated through the public API path.
Global sell defaults and technical signal config are bootstrap-compatible and
DB-backed for runtime reads, but still need a dedicated write path if we want
them to become fully user-editable outside legacy YAML migration flows.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class PortfolioAlertConfig(Base):
    """Store portfolio alert runtime settings in the database."""

    __tablename__ = "portfolio_alert_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scan_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    stop_loss_pct: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)
    take_profit_pct: Mapped[float] = mapped_column(Float, default=0.30, nullable=False)
    trailing_stop_pct: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)
    technical_signals: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    market_hours_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    channels_json: Mapped[str] = mapped_column(Text, default='["telegram"]', nullable=False)
    default_stop_loss_pct: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    default_take_profit_pct: Mapped[float] = mapped_column(Float, default=0.15, nullable=False)
    default_trailing_stop_pct: Mapped[float] = mapped_column(Float, default=0.08, nullable=False)
    technical_signals_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    migrated_from_yaml: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
