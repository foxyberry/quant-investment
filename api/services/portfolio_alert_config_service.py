"""DB-backed portfolio alert settings with YAML bootstrap fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from api.database import SessionLocal
from api.models.portfolio_alert_config import PortfolioAlertConfig
from api.schemas.portfolio_alert import PortfolioAlertConfigResponse

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "portfolio.yaml"


class PortfolioAlertConfigService:
    """Manage portfolio alert settings persistence."""

    ROW_ID = 1

    def _load_yaml_root(self) -> dict[str, Any]:
        if not _CONFIG_PATH.exists():
            return {}
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _deserialize_channels(self, raw: str | None) -> list[str]:
        if not raw:
            return ["telegram"]
        try:
            data = json.loads(raw)
        except Exception:
            return ["telegram"]
        if isinstance(data, list) and data:
            return [str(item) for item in data]
        return ["telegram"]

    def _deserialize_json_dict(self, raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _response_from_row(self, row: PortfolioAlertConfig) -> PortfolioAlertConfigResponse:
        return PortfolioAlertConfigResponse(
            enabled=row.enabled,
            scan_interval_seconds=row.scan_interval_seconds,
            stop_loss_pct=row.stop_loss_pct,
            take_profit_pct=row.take_profit_pct,
            trailing_stop_pct=row.trailing_stop_pct,
            technical_signals=row.technical_signals,
            market_hours_only=row.market_hours_only,
            channels=self._deserialize_channels(row.channels_json),
        )

    def get_config(self) -> PortfolioAlertConfigResponse:
        db = SessionLocal()
        try:
            row = db.get(PortfolioAlertConfig, self.ROW_ID)
            if row is None:
                root = self._load_yaml_root()
                fallback = root.get("alert_settings", {}) or {}
                default_sell = root.get("default_sell_conditions", {}) or {}
                technical_sell = root.get("technical_sell_signals", {}) or {}
                row = PortfolioAlertConfig(
                    id=self.ROW_ID,
                    enabled=bool(fallback.get("enabled", False if not fallback else True)),
                    scan_interval_seconds=int(fallback.get("scan_interval_seconds", 60)),
                    stop_loss_pct=float(fallback.get("stop_loss_pct", 0.20)),
                    take_profit_pct=float(fallback.get("take_profit_pct", 0.30)),
                    trailing_stop_pct=float(fallback.get("trailing_stop_pct", 0.10)),
                    technical_signals=bool(fallback.get("technical_signals", True)),
                    market_hours_only=bool(fallback.get("market_hours_only", True)),
                    channels_json=json.dumps(fallback.get("channels", ["telegram"])),
                    default_stop_loss_pct=float(default_sell.get("stop_loss_pct", 0.05)),
                    default_take_profit_pct=float(default_sell.get("take_profit_pct", 0.15)),
                    default_trailing_stop_pct=float(default_sell.get("trailing_stop_pct", 0.08)),
                    technical_signals_json=json.dumps(technical_sell),
                    migrated_from_yaml=bool(fallback or default_sell or technical_sell),
                )
                db.add(row)
                db.commit()
                db.refresh(row)
            return self._response_from_row(row)
        finally:
            db.close()

    def save_config(self, payload: dict[str, Any]) -> PortfolioAlertConfigResponse:
        current = self.get_config()
        merged = current.model_dump()
        for field, value in payload.items():
            if value is not None:
                merged[field] = value

        db = SessionLocal()
        try:
            row = db.get(PortfolioAlertConfig, self.ROW_ID)
            if row is None:
                row = PortfolioAlertConfig(id=self.ROW_ID)
                db.add(row)

            row.enabled = bool(merged["enabled"])
            row.scan_interval_seconds = int(merged["scan_interval_seconds"])
            row.stop_loss_pct = float(merged["stop_loss_pct"])
            row.take_profit_pct = float(merged["take_profit_pct"])
            row.trailing_stop_pct = float(merged["trailing_stop_pct"])
            row.technical_signals = bool(merged["technical_signals"])
            row.market_hours_only = bool(merged["market_hours_only"])
            row.channels_json = json.dumps(merged.get("channels") or ["telegram"])
            row.migrated_from_yaml = False
            db.commit()
            db.refresh(row)
            return self._response_from_row(row)
        finally:
            db.close()

    def get_default_sell_conditions(self) -> dict[str, float]:
        db = SessionLocal()
        try:
            row = db.get(PortfolioAlertConfig, self.ROW_ID)
            if row is None:
                self.get_config()
                row = db.get(PortfolioAlertConfig, self.ROW_ID)
            if row is None:
                return {
                    "stop_loss_pct": 0.05,
                    "take_profit_pct": 0.15,
                    "trailing_stop_pct": 0.08,
                }
            return {
                "stop_loss_pct": row.default_stop_loss_pct,
                "take_profit_pct": row.default_take_profit_pct,
                "trailing_stop_pct": row.default_trailing_stop_pct,
            }
        finally:
            db.close()

    def get_technical_signals_config(self) -> dict[str, Any]:
        db = SessionLocal()
        try:
            row = db.get(PortfolioAlertConfig, self.ROW_ID)
            if row is None:
                self.get_config()
                row = db.get(PortfolioAlertConfig, self.ROW_ID)
            if row is None:
                return {}
            return self._deserialize_json_dict(row.technical_signals_json)
        finally:
            db.close()


_service: PortfolioAlertConfigService | None = None


def get_portfolio_alert_config_service() -> PortfolioAlertConfigService:
    global _service
    if _service is None:
        _service = PortfolioAlertConfigService()
    return _service
