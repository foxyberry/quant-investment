"""Broker settings persistence and runtime apply helpers."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import urllib.request
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from brokers import refresh_broker

from api.database import SessionLocal
from api.models.broker_credential import BrokerCredential
from api.services.broker_settings_views import (
    IBKRSettingsView,
    SlackSettingsView,
    TelegramSettingsView,
    TigerSettingsView,
)

try:
    from cryptography.fernet import Fernet, InvalidToken

    _CRYPTO_AVAILABLE = True
except Exception:  # pragma: no cover - handled by runtime guard
    Fernet = None  # type: ignore[assignment]
    InvalidToken = Exception  # type: ignore[assignment]
    _CRYPTO_AVAILABLE = False


class BrokerSettingsService:
    """Manage broker config persistence and dynamic adapter refresh."""

    ENCRYPTION_KEY_ENV = "BROKER_CONFIG_ENCRYPTION_KEY"

    def _get_fernet(self) -> Fernet:
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography package is required for encrypted broker settings")
        key = os.environ.get(self.ENCRYPTION_KEY_ENV)
        if not key:
            # Try loading from .env file before generating a new one.
            key = self._load_env_key()
        if not key:
            # Auto-generate a key and persist it in .env for convenience.
            key = Fernet.generate_key().decode("utf-8")
            self._persist_env_key(key)
            logger.info("Auto-generated %s and saved to .env", self.ENCRYPTION_KEY_ENV)
        os.environ[self.ENCRYPTION_KEY_ENV] = key
        try:
            key_bytes = key.encode("utf-8")
            # Validate key format early.
            base64.urlsafe_b64decode(key_bytes)
            return Fernet(key_bytes)
        except Exception as exc:
            raise RuntimeError(f"Invalid {self.ENCRYPTION_KEY_ENV} format") from exc

    def _load_env_key(self) -> str | None:
        """Try to read the encryption key from the project .env file."""
        import pathlib

        env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"
        try:
            if not env_path.exists():
                return None
            for line in env_path.read_text().splitlines():
                if line.startswith(f"{self.ENCRYPTION_KEY_ENV}="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        logger.info("Loaded %s from %s", self.ENCRYPTION_KEY_ENV, env_path)
                        return val
        except OSError:
            pass
        return None

    def _persist_env_key(self, key: str) -> None:
        """Append the encryption key to the project .env file."""
        import pathlib

        env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"
        try:
            lines: list[str] = []
            if env_path.exists():
                lines = env_path.read_text().splitlines(keepends=True)
            # Replace existing empty key or append
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{self.ENCRYPTION_KEY_ENV}="):
                    lines[i] = f"{self.ENCRYPTION_KEY_ENV}={key}\n"
                    found = True
                    break
            if not found:
                lines.append(f"{self.ENCRYPTION_KEY_ENV}={key}\n")
            env_path.write_text("".join(lines))
        except OSError:
            logger.warning("Could not write %s to %s", self.ENCRYPTION_KEY_ENV, env_path)

    def _encrypt(self, raw: str) -> str:
        token = self._get_fernet().encrypt(raw.encode("utf-8"))
        return token.decode("utf-8")

    def _decrypt(self, token: str) -> str:
        try:
            raw = self._get_fernet().decrypt(token.encode("utf-8"))
            return raw.decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Failed to decrypt stored broker credential") from exc

    def get_tiger_settings(self) -> TigerSettingsView:
        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "tiger")
            if not row:
                return TigerSettingsView(
                    tiger_id=None,
                    account=None,
                    license=None,
                    sandbox=False,
                    has_private_key=False,
                    updated_at=None,
                )

            data = json.loads(row.config_json)
            return TigerSettingsView(
                tiger_id=data.get("tiger_id"),
                account=data.get("account"),
                license=data.get("license"),
                sandbox=bool(data.get("sandbox", False)),
                has_private_key=bool(data.get("private_key_encrypted")),
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
        finally:
            db.close()

    def save_tiger_settings(self, payload: dict[str, Any]) -> TigerSettingsView:
        tiger_id = (payload.get("tiger_id") or "").strip()
        account = (payload.get("account") or "").strip()
        license_type = (payload.get("license") or "TBNZ").strip()
        sandbox = bool(payload.get("sandbox", False))
        private_key = payload.get("private_key")

        if not tiger_id:
            raise ValueError("tiger_id is required")
        if not account:
            raise ValueError("account is required")
        if not license_type:
            raise ValueError("license is required")

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "tiger")
            existing_data: dict[str, Any] = {}
            if row:
                existing_data = json.loads(row.config_json)
            else:
                row = BrokerCredential(
                    broker="tiger",
                    account_id=account,
                    is_enabled=True,
                    config_json="{}",
                )

            encrypted_key = existing_data.get("private_key_encrypted")
            if isinstance(private_key, str) and private_key.strip():
                encrypted_key = self._encrypt(private_key.strip())

            merged = {
                "tiger_id": tiger_id,
                "account": account,
                "license": license_type,
                "sandbox": sandbox,
                "private_key_encrypted": encrypted_key,
            }

            if not merged.get("private_key_encrypted"):
                raise ValueError("private_key is required")

            row.account_id = account
            row.is_enabled = True
            row.config_json = json.dumps(merged)
            db.merge(row)
            db.commit()
        finally:
            db.close()

        self.apply_tiger_settings_to_runtime()
        return self.get_tiger_settings()

    def apply_tiger_settings_to_runtime(self) -> None:
        """Load tiger settings from DB and apply into process env."""
        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "tiger")
            if not row:
                return
            data = json.loads(row.config_json)
            encrypted_key = data.get("private_key_encrypted")
            if not encrypted_key:
                return
            os.environ["TIGER_ID"] = str(data.get("tiger_id", "")).strip()
            os.environ["TIGER_ACCOUNT"] = str(data.get("account", "")).strip()
            os.environ["TIGER_LICENSE"] = str(data.get("license", "TBNZ")).strip()
            os.environ["TIGER_SANDBOX"] = "true" if bool(data.get("sandbox", False)) else "false"
            os.environ["TIGER_PRIVATE_KEY_CONTENT"] = self._decrypt(str(encrypted_key))
            # Prefer direct key content over file path in runtime mode.
            os.environ.pop("TIGER_PRIVATE_KEY", None)
        finally:
            db.close()

        refresh_broker("tiger")

    # -- IBKR settings -------------------------------------------------------

    def get_ibkr_settings(self) -> IBKRSettingsView:
        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "ibkr")
            if not row:
                return IBKRSettingsView(
                    gateway_url=None,
                    account_id=None,
                    updated_at=None,
                )

            data = json.loads(row.config_json)
            return IBKRSettingsView(
                gateway_url=data.get("gateway_url"),
                account_id=data.get("account_id"),
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
        finally:
            db.close()

    @staticmethod
    def _validate_ibkr_gateway_url(url: str) -> None:
        """Restrict gateway_url to localhost to prevent SSRF."""
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        allowed = {"localhost", "127.0.0.1", "::1"}
        if host not in allowed and not re.match(r"^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
            raise ValueError(
                "gateway_url must point to localhost (e.g. https://localhost:5000)"
            )

    def save_ibkr_settings(self, payload: dict[str, Any]) -> IBKRSettingsView:
        gateway_url = (payload.get("gateway_url") or "").strip()
        account_id = (payload.get("account_id") or "").strip() or None

        if not gateway_url:
            raise ValueError("gateway_url is required")
        self._validate_ibkr_gateway_url(gateway_url)

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "ibkr")
            if not row:
                row = BrokerCredential(
                    broker="ibkr",
                    account_id=account_id or "",
                    is_enabled=True,
                    config_json="{}",
                )

            merged = {
                "gateway_url": gateway_url,
                "account_id": account_id,
            }

            row.account_id = account_id or ""
            row.is_enabled = True
            row.config_json = json.dumps(merged)
            db.merge(row)
            db.commit()
        finally:
            db.close()

        self.apply_ibkr_settings_to_runtime()
        return self.get_ibkr_settings()

    def apply_ibkr_settings_to_runtime(self) -> None:
        """Load IBKR settings from DB and apply into process env."""
        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "ibkr")
            if not row:
                return
            data = json.loads(row.config_json)
            gateway_url = data.get("gateway_url")
            if not gateway_url:
                return
            os.environ["IBKR_GATEWAY_URL"] = str(gateway_url).strip()
            account_id = data.get("account_id")
            if account_id:
                os.environ["IBKR_ACCOUNT_ID"] = str(account_id).strip()
            else:
                os.environ.pop("IBKR_ACCOUNT_ID", None)
        finally:
            db.close()

        refresh_broker("ibkr")

    # -- Telegram settings ---------------------------------------------------

    def get_telegram_settings(self) -> TelegramSettingsView:
        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "telegram")
            if not row:
                return TelegramSettingsView(
                    has_bot_token=False,
                    chat_id=None,
                    enabled=False,
                    updated_at=None,
                )

            data = json.loads(row.config_json)
            return TelegramSettingsView(
                has_bot_token=bool(data.get("bot_token_encrypted")),
                chat_id=data.get("chat_id"),
                enabled=bool(data.get("enabled", False)),
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
        finally:
            db.close()

    def save_telegram_settings(self, payload: dict[str, Any]) -> TelegramSettingsView:
        chat_id = (payload.get("chat_id") or "").strip()
        bot_token = payload.get("bot_token")
        enabled = bool(payload.get("enabled", True))

        if not chat_id:
            raise ValueError("chat_id is required")

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "telegram")
            existing_data: dict[str, Any] = {}
            if row:
                existing_data = json.loads(row.config_json)
            else:
                row = BrokerCredential(
                    broker="telegram",
                    account_id=chat_id,
                    is_enabled=True,
                    config_json="{}",
                )

            encrypted_token = existing_data.get("bot_token_encrypted")
            if isinstance(bot_token, str) and bot_token.strip():
                encrypted_token = self._encrypt(bot_token.strip())

            merged = {
                "chat_id": chat_id,
                "bot_token_encrypted": encrypted_token,
                "enabled": enabled,
            }

            if not merged.get("bot_token_encrypted"):
                raise ValueError("bot_token is required")

            row.account_id = chat_id
            row.is_enabled = enabled
            row.config_json = json.dumps(merged)
            db.merge(row)
            db.commit()
        finally:
            db.close()

        return self.get_telegram_settings()

    def send_telegram_message(
        self,
        chat_id: str,
        bot_token_encrypted: str,
        message: str = "Quant Investment test notification",
    ) -> bool:
        """Send a message via the Telegram Bot API.

        Parameters
        ----------
        chat_id:
            Target chat / group / channel ID.
        bot_token_encrypted:
            Fernet-encrypted bot token stored in config_json.
        message:
            Text content to send.

        Returns
        -------
        bool
            True on success, False on failure.
        """
        # Let decryption errors propagate so callers can distinguish key mismatch.
        token = self._decrypt(bot_token_encrypted)
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return bool(body.get("ok"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                body = json.loads(exc.read().decode("utf-8"))
                detail = body.get("description", "")
            except Exception:
                pass
            logger.warning("Telegram sendMessage failed: %s %s", exc.code, detail)
            raise RuntimeError(
                detail or f"Telegram API error {exc.code}"
            ) from exc
        except Exception:
            logger.warning("Telegram sendMessage failed", exc_info=True)
            return False


    # ------------------------------------------------------------------
    # Slack settings
    # ------------------------------------------------------------------

    _SLACK_WEBHOOK_PATTERN = re.compile(r"^https://hooks\.slack\.com/services/.+")

    def get_slack_settings(self) -> SlackSettingsView:
        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "slack")
            if not row:
                return SlackSettingsView(has_webhook_url=False, channel_name=None, enabled=False, updated_at=None)
            data = json.loads(row.config_json)
            return SlackSettingsView(
                has_webhook_url=bool(data.get("webhook_url_encrypted")),
                channel_name=data.get("channel_name"),
                enabled=data.get("enabled", False),
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
        finally:
            db.close()

    def save_slack_settings(self, payload: dict[str, Any]) -> SlackSettingsView:
        webhook_url = (payload.get("webhook_url") or "").strip()
        channel_name = (payload.get("channel_name") or "").strip()
        enabled = bool(payload.get("enabled", False))

        if webhook_url and not self._SLACK_WEBHOOK_PATTERN.match(webhook_url):
            raise ValueError("Invalid Slack webhook URL. Must start with https://hooks.slack.com/services/")

        db = SessionLocal()
        try:
            row = db.get(BrokerCredential, "slack")
            if row:
                data = json.loads(row.config_json)
            else:
                data = {}

            if webhook_url:
                data["webhook_url_encrypted"] = self._encrypt(webhook_url)
            data["channel_name"] = channel_name
            data["enabled"] = enabled

            if row:
                row.config_json = json.dumps(data)
            else:
                row = BrokerCredential(
                    broker="slack",
                    config_json=json.dumps(data),
                )
                db.add(row)
            db.commit()
            db.refresh(row)
            return SlackSettingsView(
                has_webhook_url=bool(data.get("webhook_url_encrypted")),
                channel_name=data.get("channel_name"),
                enabled=data.get("enabled", False),
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
        finally:
            db.close()

    def send_slack_test(self, message: str = "Quant Investment test notification") -> bool:
        """Send a test message via Slack webhook."""
        from api.services.notification_dispatcher import _send_slack
        return _send_slack(self, message)

_broker_settings_service = BrokerSettingsService()


def get_broker_settings_service() -> BrokerSettingsService:
    return _broker_settings_service
