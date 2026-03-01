"""Broker settings persistence and runtime apply helpers."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from brokers import refresh_broker

from api.database import SessionLocal
from api.models.broker_credential import BrokerCredential

try:
    from cryptography.fernet import Fernet, InvalidToken

    _CRYPTO_AVAILABLE = True
except Exception:  # pragma: no cover - handled by runtime guard
    Fernet = None  # type: ignore[assignment]
    InvalidToken = Exception  # type: ignore[assignment]
    _CRYPTO_AVAILABLE = False


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


class BrokerSettingsService:
    """Manage broker config persistence and dynamic adapter refresh."""

    ENCRYPTION_KEY_ENV = "BROKER_CONFIG_ENCRYPTION_KEY"

    def _get_fernet(self) -> Fernet:
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography package is required for encrypted broker settings")
        key = os.environ.get(self.ENCRYPTION_KEY_ENV)
        if not key:
            raise RuntimeError(
                f"{self.ENCRYPTION_KEY_ENV} is required to save broker credentials"
            )
        try:
            key_bytes = key.encode("utf-8")
            # Validate key format early.
            base64.urlsafe_b64decode(key_bytes)
            return Fernet(key_bytes)
        except Exception as exc:
            raise RuntimeError(f"Invalid {self.ENCRYPTION_KEY_ENV} format") from exc

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


_broker_settings_service = BrokerSettingsService()


def get_broker_settings_service() -> BrokerSettingsService:
    return _broker_settings_service
