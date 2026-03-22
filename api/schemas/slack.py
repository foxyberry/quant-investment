"""Slack notification settings schemas."""

from typing import Optional

from pydantic import BaseModel


class SlackSettingsRequest(BaseModel):
    webhook_url: Optional[str] = None
    channel_name: Optional[str] = None
    enabled: bool = False


class SlackSettingsResponse(BaseModel):
    has_webhook_url: bool = False
    channel_name: Optional[str] = None
    enabled: bool = False
    updated_at: Optional[str] = None


class SlackTestResponse(BaseModel):
    success: bool
    message: str = ""
