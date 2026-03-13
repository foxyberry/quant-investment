"""
Strategy Webhook Schemas.

Pydantic models for webhook configuration and event payloads.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

VALID_WEBHOOK_EVENTS = {
    "status_changed",
    "backtest_completed",
    "validation_passed",
    "validation_failed",
}


class WebhookCreateRequest(BaseModel):
    """Request to create a new webhook."""

    url: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(
        ...,
        min_length=1,
        description="Events to subscribe to",
    )
    secret: Optional[str] = Field(
        None,
        max_length=128,
        description="Shared secret for HMAC signature verification",
    )
    active: bool = Field(default=True)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: List[str]) -> List[str]:
        invalid = set(v) - VALID_WEBHOOK_EVENTS
        if invalid:
            raise ValueError(f"Invalid events: {invalid}. Valid: {VALID_WEBHOOK_EVENTS}")
        return v


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook."""

    url: Optional[str] = None
    events: Optional[List[str]] = None
    secret: Optional[str] = Field(None, max_length=128)
    active: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            invalid = set(v) - VALID_WEBHOOK_EVENTS
            if invalid:
                raise ValueError(f"Invalid events: {invalid}. Valid: {VALID_WEBHOOK_EVENTS}")
        return v


class WebhookResponse(BaseModel):
    """Response for a single webhook."""

    id: int
    strategy_id: str
    url: str
    events: List[str]
    has_secret: bool = Field(description="Whether a secret is configured (secret itself is not exposed)")
    active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WebhookListResponse(BaseModel):
    """Response listing all webhooks for a strategy."""

    strategy_id: str
    webhooks: List[WebhookResponse]
    total_count: int


class WebhookEventPayload(BaseModel):
    """Payload sent to webhook endpoints."""

    event: str
    strategy_id: str
    strategy_name: str
    timestamp: str
    data: Dict[str, Any] = Field(default_factory=dict)
