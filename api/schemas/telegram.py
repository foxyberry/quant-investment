"""
Telegram notification settings schemas.

Pydantic models for Telegram bot configuration and test responses.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TelegramSettingsRequest(BaseModel):
    """Telegram bot credential payload for settings save."""

    bot_token: Optional[str] = Field(
        None, description="Telegram Bot API token (kept if empty on update)"
    )
    chat_id: str = Field(..., description="Telegram chat ID to send notifications to")
    enabled: bool = Field(default=True, description="Whether Telegram notifications are enabled")


class TelegramSettingsResponse(BaseModel):
    """Telegram notification settings payload safe for UI."""

    has_bot_token: bool = False
    chat_id: Optional[str] = None
    enabled: bool = False
    updated_at: Optional[str] = None


class TelegramTestResponse(BaseModel):
    """Result of a Telegram test notification."""

    success: bool = Field(..., description="Whether the test message was sent successfully")
    message: str = Field(..., description="Human-readable result message")
