"""
Strategy Webhook Schemas.

Pydantic models for webhook configuration and event payloads.
"""

import ipaddress
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

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
        _check_ssrf(v)
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
        if v is not None:
            if not v.startswith(("http://", "https://")):
                raise ValueError("URL must start with http:// or https://")
            _check_ssrf(v)
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            invalid = set(v) - VALID_WEBHOOK_EVENTS
            if invalid:
                raise ValueError(f"Invalid events: {invalid}. Valid: {VALID_WEBHOOK_EVENTS}")
        return v


def _is_blocked_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if the IP should be blocked for webhook delivery."""
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _check_ssrf(url: str) -> None:
    """Block internal/metadata network addresses to prevent SSRF."""
    import socket

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname or hostname == "localhost":
        raise ValueError("Webhook URL must not target internal addresses")
    # Check literal IP first
    try:
        addr = ipaddress.ip_address(hostname)
        if _is_blocked_ip(addr):
            raise ValueError("Webhook URL must not target internal/private addresses")
        return
    except ValueError:
        pass  # hostname is a domain name
    # DNS resolution check
    try:
        for info in socket.getaddrinfo(hostname, None):
            resolved_ip = info[4][0]
            try:
                addr = ipaddress.ip_address(resolved_ip)
                if _is_blocked_ip(addr):
                    raise ValueError(
                        "Webhook URL must not target internal/private addresses"
                    )
            except ValueError as e:
                if "internal" in str(e) or "private" in str(e):
                    raise
    except socket.gaierror:
        pass  # DNS resolution failed; allow (will fail at dispatch time)


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
