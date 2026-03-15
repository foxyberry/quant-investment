"""
Strategy Alert Schemas.

Pydantic models for alert configuration and alert history.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

VALID_CHANNELS = {"webhook", "in_app", "telegram"}


class AlertConfigUpsertRequest(BaseModel):
    """Request to create or update alert configuration."""

    enabled: bool = Field(default=True)
    interval_minutes: int = Field(default=60, ge=5, le=1440)
    channels: List[str] = Field(default_factory=lambda: ["in_app"])
    tickers: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Tickers to monitor (1-20)",
    )

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        invalid = set(v) - VALID_CHANNELS
        if invalid:
            raise ValueError(f"Invalid channels: {invalid}. Valid: {VALID_CHANNELS}")
        return v

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, v: List[str]) -> List[str]:
        cleaned = [t.upper().strip() for t in v if t.strip()]
        if not cleaned:
            raise ValueError("At least one non-blank ticker is required")
        return cleaned


class AlertConfigResponse(BaseModel):
    """Response for alert configuration."""

    id: int
    strategy_id: str
    enabled: bool
    interval_minutes: int
    channels: List[str]
    tickers: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AlertHistoryEntry(BaseModel):
    """A single fired alert record."""

    id: int
    strategy_id: str
    ticker: str
    matched_conditions: List[str]
    price_at_signal: Optional[float] = None
    fired_at: Optional[str] = None


class AlertHistoryResponse(BaseModel):
    """Response listing alert history."""

    strategy_id: str
    alerts: List[AlertHistoryEntry]
    total_count: int
