"""Macro market aggregation service.

Combines FX, futures proxy, and investor-flow inputs into a single
macro bundle payload with stale-data decay scoring.
"""

from __future__ import annotations

import json
import logging
import math
import os
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Dict, Optional

from api.services.exchange_rate_service import ExchangeRateService, get_exchange_rate_service
from api.services.market_service import MarketService

logger = logging.getLogger(__name__)


class MacroMarketService:
    """Aggregates macro inputs and computes regime signal."""

    def __init__(
        self,
        market_service: MarketService,
        exchange_service: Optional[ExchangeRateService] = None,
    ) -> None:
        self.market_service = market_service
        self.exchange_service = exchange_service or get_exchange_rate_service()

        self.futures_ticker = os.getenv("MACRO_FUTURES_TICKER", "069500.KS")
        self.spot_ticker = os.getenv("MACRO_SPOT_TICKER", "^KS11")
        self.investor_flow_path = Path(
            os.getenv("MACRO_INVESTOR_FLOW_PATH", "data/market/investor_flow_latest.json")
        )

        self._history: Deque[Dict[str, Any]] = deque(maxlen=1000)
        self._last_fx_value: Optional[float] = None

    def get_bundle(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)

        fx = self._get_fx_snapshot(now)
        futures = self._get_futures_snapshot(now)
        flow = self._get_flow_snapshot()

        freshness = {
            "fx_age_sec": self._age_sec(fx.get("updated_at"), now),
            "futures_age_sec": self._age_sec(futures.get("updated_at"), now),
            "flow_age_sec": self._age_sec(flow.get("updated_at"), now),
        }

        signal = self._compute_signal(fx, futures, flow, freshness, now)

        bundle = {
            "fx": fx,
            "futures": futures,
            "flow": flow,
            "signal": signal,
            "freshness": freshness,
        }
        self._append_history(bundle, now)
        return bundle

    def get_history(self, window: str = "60m") -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        delta = self._parse_window(window)
        min_ts = now - delta

        points = [
            {
                "timestamp": p["timestamp"],
                "fx_value": p.get("fx_value"),
                "futures_value": p.get("futures_value"),
                "foreign_net": p.get("foreign_net"),
                "macro_score": p.get("macro_score"),
                "regime": p.get("regime", "unknown"),
            }
            for p in self._history
            if self._safe_datetime(p.get("timestamp")) and self._safe_datetime(p.get("timestamp")) >= min_ts
        ]

        return {"window": window, "points": points}

    def _get_fx_snapshot(self, now: datetime) -> Dict[str, Any]:
        try:
            rates = self.exchange_service.get_rates(base="USD")
            value = rates.get("rates", {}).get("KRW")
            updated_at = rates.get("updated_at")
            value = float(value) if value is not None else None

            change_pct: Optional[float] = None
            if value is not None and self._last_fx_value not in (None, 0):
                change_pct = ((value - float(self._last_fx_value)) / float(self._last_fx_value)) * 100.0
            self._last_fx_value = value

            return {
                "pair": "USD/KRW",
                "value": value,
                "change_pct": change_pct,
                "updated_at": self._to_iso(updated_at or now),
            }
        except Exception as exc:
            logger.warning("FX snapshot unavailable: %s", exc)
            return {
                "pair": "USD/KRW",
                "value": None,
                "change_pct": None,
                "updated_at": None,
            }

    def _get_futures_snapshot(self, now: datetime) -> Dict[str, Any]:
        try:
            fut = self.market_service.get_quote(self.futures_ticker)
            spot = self.market_service.get_quote(self.spot_ticker)

            fut_value = float(fut["current_price"]) if fut and fut.get("current_price") is not None else None
            spot_value = float(spot["current_price"]) if spot and spot.get("current_price") is not None else None

            basis = fut_value - spot_value if fut_value is not None and spot_value is not None else None
            change_pct = float(fut["change_pct"]) if fut and fut.get("change_pct") is not None else None
            updated_at = fut.get("timestamp") if fut else None

            return {
                "symbol": self.futures_ticker,
                "value": fut_value,
                "basis": basis,
                "change_pct": change_pct,
                "updated_at": self._to_iso(updated_at or now),
            }
        except Exception as exc:
            logger.warning("Futures snapshot unavailable: %s", exc)
            return {
                "symbol": self.futures_ticker,
                "value": None,
                "basis": None,
                "change_pct": None,
                "updated_at": None,
            }

    def _get_flow_snapshot(self) -> Dict[str, Any]:
        # Primary adapter: pipeline-populated JSON file
        try:
            if self.investor_flow_path.exists():
                raw = json.loads(self.investor_flow_path.read_text(encoding="utf-8"))
                return {
                    "market": str(raw.get("market", "KOSPI")),
                    "foreign_net": self._to_float(raw.get("foreign_net")),
                    "institution_net": self._to_float(raw.get("institution_net")),
                    "individual_net": self._to_float(raw.get("individual_net")),
                    "window_min": self._to_int(raw.get("window_min")),
                    "updated_at": self._to_iso(raw.get("updated_at")),
                }
        except Exception as exc:
            logger.warning("Investor flow file adapter failed: %s", exc)

        # Fallback: unavailable (explicit nulls to avoid fake precision)
        return {
            "market": "KOSPI",
            "foreign_net": None,
            "institution_net": None,
            "individual_net": None,
            "window_min": None,
            "updated_at": None,
        }

    def _compute_signal(
        self,
        fx: Dict[str, Any],
        futures: Dict[str, Any],
        flow: Dict[str, Any],
        freshness: Dict[str, Any],
        now: datetime,
    ) -> Dict[str, Any]:
        # Raw component scores in [-1, +1]
        fx_raw = self._clip((self._to_float(fx.get("change_pct")) or 0.0) / 0.5, -1.0, 1.0)
        fut_change = self._to_float(futures.get("change_pct"))
        fut_basis = self._to_float(futures.get("basis"))
        futures_raw = self._clip((-(fut_change or 0.0) / 1.0) + (-(fut_basis or 0.0) / 50.0), -1.0, 1.0)

        foreign_net = self._to_float(flow.get("foreign_net"))
        flow_raw = self._clip((-(foreign_net or 0.0)) / 1_000_000_000.0, -1.0, 1.0)

        # Freshness decay (half-life in seconds)
        fx_decay = self._stale_decay(freshness.get("fx_age_sec"), half_life_sec=600)
        futures_decay = self._stale_decay(freshness.get("futures_age_sec"), half_life_sec=600)
        flow_decay = self._stale_decay(freshness.get("flow_age_sec"), half_life_sec=900)

        weighted = [
            (0.40, fx_raw, fx_decay, fx.get("value") is not None),
            (0.35, futures_raw, futures_decay, futures.get("value") is not None),
            (0.25, flow_raw, flow_decay, flow.get("foreign_net") is not None),
        ]

        numerator = 0.0
        denominator = 0.0
        for w, raw, decay, available in weighted:
            if not available:
                continue
            eff_w = w * decay
            numerator += eff_w * raw
            denominator += eff_w

        macro_score: Optional[float] = None
        regime = "unknown"
        if denominator > 0:
            macro_score = round(numerator / denominator, 4)
            if macro_score >= 0.6:
                regime = "risk_off"
            elif macro_score <= -0.6:
                regime = "risk_on"
            else:
                regime = "neutral"

        reason = self._build_reason(fx_raw, futures_raw, flow_raw, fx_decay, futures_decay, flow_decay, regime)

        return {
            "macro_score": macro_score,
            "regime": regime,
            "reason": reason,
            "updated_at": self._to_iso(now),
        }

    def _build_reason(
        self,
        fx_raw: float,
        futures_raw: float,
        flow_raw: float,
        fx_decay: float,
        futures_decay: float,
        flow_decay: float,
        regime: str,
    ) -> str:
        parts = [
            f"fx={fx_raw:.2f} (decay={fx_decay:.2f})",
            f"futures={futures_raw:.2f} (decay={futures_decay:.2f})",
            f"flow={flow_raw:.2f} (decay={flow_decay:.2f})",
        ]
        return f"{regime}: " + ", ".join(parts)

    def _append_history(self, bundle: Dict[str, Any], now: datetime) -> None:
        signal = bundle.get("signal", {})
        fx = bundle.get("fx", {})
        futures = bundle.get("futures", {})
        flow = bundle.get("flow", {})

        self._history.append(
            {
                "timestamp": self._to_iso(now),
                "fx_value": self._to_float(fx.get("value")),
                "futures_value": self._to_float(futures.get("value")),
                "foreign_net": self._to_float(flow.get("foreign_net")),
                "macro_score": self._to_float(signal.get("macro_score")),
                "regime": signal.get("regime", "unknown"),
            }
        )

    def _parse_window(self, window: str) -> timedelta:
        value = (window or "60m").strip().lower()
        try:
            if value.endswith("m"):
                return timedelta(minutes=max(int(value[:-1] or "60"), 1))
            if value.endswith("h"):
                return timedelta(hours=max(int(value[:-1] or "1"), 1))
            if value.endswith("d"):
                return timedelta(days=max(int(value[:-1] or "1"), 1))
        except ValueError:
            logger.warning("Invalid macro history window: %s. Falling back to 60m.", value)
        return timedelta(minutes=60)

    def _age_sec(self, value: Any, now: datetime) -> Optional[int]:
        dt = self._safe_datetime(value)
        if dt is None:
            return None
        return max(int((now - dt).total_seconds()), 0)

    def _stale_decay(self, age_sec: Any, half_life_sec: int) -> float:
        age = self._to_float(age_sec)
        if age is None:
            return 0.0
        return float(math.exp(-math.log(2.0) * (age / float(half_life_sec))))

    def _safe_datetime(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def _to_iso(self, value: Any) -> Optional[str]:
        dt = self._safe_datetime(value)
        return dt.isoformat() if dt is not None else None

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _clip(self, value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))


def get_macro_market_service(market_service: MarketService) -> MacroMarketService:
    return MacroMarketService(market_service=market_service)
