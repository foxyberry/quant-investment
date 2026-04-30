"""View dataclasses returned by BrokerSettingsService."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TigerSettingsView:
    tiger_id: str | None
    account: str | None
    license: str | None
    sandbox: bool
    has_private_key: bool
    updated_at: str | None


@dataclass
class IBKRSettingsView:
    gateway_url: str | None
    account_id: str | None
    updated_at: str | None


@dataclass
class TelegramSettingsView:
    has_bot_token: bool
    chat_id: str | None
    enabled: bool
    updated_at: str | None


@dataclass
class SlackSettingsView:
    has_webhook_url: bool
    channel_name: str | None
    enabled: bool
    updated_at: str | None
