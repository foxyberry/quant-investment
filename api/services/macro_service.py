"""Macro market aggregation service.

Combines FX, futures, and investor-flow inputs into a single
macro bundle payload with stale-data decay scoring.

Data-fetching adapters are in market_data_service.MarketDataMixin.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from collections import deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.services import macro_interpretation_service
from api.models.macro_history import MacroHistory
from api.services.exchange_rate_service import ExchangeRateService, get_exchange_rate_service
from api.services import macro_history_service
from api.services.market_data_service import MarketDataMixin
from api.services.market_service import MarketService

logger = logging.getLogger(__name__)


class MacroMarketService(MarketDataMixin):
    """Aggregates macro inputs and computes regime signal."""

    # Batch DB writes every N ticks to reduce I/O
    _DB_FLUSH_INTERVAL = 10

    # Off-hours half-life multiplier (장외 시간에 반감기 확장)
    _OFF_HOURS_MULTIPLIER = 24

    # Default half-lives (seconds) — used during market hours
    _HALF_LIFE_FX = 600
    _HALF_LIFE_FUTURES = 600
    _HALF_LIFE_FLOW = 900

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
        self.breadth_path = Path(
            os.getenv("MACRO_BREADTH_PATH", "data/market/market_breadth_latest.json")
        )
        self.events_calendar_path = Path(
            os.getenv("MACRO_EVENTS_PATH", os.path.join(os.path.dirname(__file__), "..", "static", "events_calendar.json"))
        )

        self._lock = threading.Lock()
        self._history: Deque[Dict[str, Any]] = deque(maxlen=50_000)
        self._db_buffer: List[Dict[str, Any]] = []
        self._db_tick_count = 0
        self._last_fx_value: Optional[float] = None

        # Session-start FX baseline for daily change calculation
        self._session_start_fx: Optional[float] = None
        self._session_start_date: Optional[date] = None

        # Bundle TTL cache (separate lock to avoid contention with history)
        self._BUNDLE_TTL_SEC = 5.0
        self._cache_lock = threading.Lock()
        self._cached_bundle: Optional[Dict[str, Any]] = None
        self._cached_at: float = 0.0  # monotonic timestamp

        # Load recent history from DB on startup
        self._load_history_from_db()

        # Backfill gaps with historical daily data in background
        threading.Thread(
            target=self._backfill_history, daemon=True, name="macro-backfill"
        ).start()

    def get_bundle(self, force_refresh: bool = False) -> Dict[str, Any]:
        # Check TTL cache (lock-free read for fast path)
        if not force_refresh:
            with self._cache_lock:
                if self._cached_bundle is not None:
                    elapsed = time.monotonic() - self._cached_at
                    if elapsed < self._BUNDLE_TTL_SEC:
                        # Return shallow copy with cache_hit flag
                        hit = {**self._cached_bundle, "cache_hit": True}
                        return hit

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

        interpretation = self._build_interpretation(fx, futures, flow)

        # Derive execution posture from regime + confidence + entry_signal
        posture, posture_rationale = self._derive_posture(
            signal.get("regime", "unknown"),
            signal.get("confidence_band"),
            interpretation.get("entry_signal", "wait"),
        )
        interpretation["posture"] = posture
        interpretation["posture_rationale"] = posture_rationale
        # Demote entry_signal to match posture when they conflict
        if posture == "wait" and interpretation.get("entry_signal") == "buy_favorable":
            interpretation["entry_signal"] = "wait"

        breadth = self._get_breadth_snapshot()
        events = self._get_upcoming_events()

        generated_at = self._to_iso(now)
        bundle = {
            "fx": fx,
            "futures": futures,
            "flow": flow,
            "signal": signal,
            "freshness": freshness,
            "interpretation": interpretation,
            "cache_hit": False,
            "generated_at": generated_at,
            "is_market_hours": self._is_krx_market_hours(),
            "breadth": breadth,
            "events": events if events else None,
        }
        self._append_history(bundle, now)

        # Update cache
        with self._cache_lock:
            self._cached_bundle = bundle.copy()
            self._cached_at = time.monotonic()

        return bundle

    # Downsample bucket sizes (seconds) per window.
    # Windows with small point counts are left as-is (bucket_sec=0).
    _DOWNSAMPLE_BUCKETS: Dict[str, int] = {
        "60m": 0,        # ~60 pts max, no downsampling
        "6h": 0,         # ~360 pts max, acceptable
        "1d": 300,       # 5-min buckets → ~288 pts
        "7d": 3600,      # 1-hour buckets → ~168 pts
        "30d": 21600,    # 6-hour buckets → ~120 pts
    }

    # Target max points per window (downsample if exceeded)
    _DOWNSAMPLE_TARGETS: Dict[str, int] = {
        "60m": 0,    # no limit
        "6h": 0,     # no limit
        "1d": 300,
        "7d": 250,
        "30d": 200,
    }

    # History cache: window → (monotonic_time, result_dict)
    _HISTORY_CACHE_TTL: Dict[str, int] = {
        "60m": 30,
        "6h": 60,
        "1d": 60,
        "7d": 300,
        "30d": 300,
    }

    def get_history(self, window: str = "60m") -> Dict[str, Any]:
        return macro_history_service.get_history(self, window)

    def _cache_history(self, window: str, mono_time: float, result: Dict[str, Any]) -> None:
        macro_history_service.cache_history(self, window, mono_time, result)

    @classmethod
    def _downsample_points(
        cls, points: List[Dict[str, Any]], window: str
    ) -> List[Dict[str, Any]]:
        return macro_history_service.downsample_points(cls, points, window)

    # ------------------------------------------------------------------
    # Signal computation
    # ------------------------------------------------------------------

    def _compute_signal(
        self,
        fx: Dict[str, Any],
        futures: Dict[str, Any],
        flow: Dict[str, Any],
        freshness: Dict[str, Any],
        now: datetime,
    ) -> Dict[str, Any]:
        # Raw component scores in [-1, +1]
        fx_raw = self._clip((self._to_float(fx.get("change_pct")) or 0.0) / 1.5, -1.0, 1.0)
        fut_change = self._to_float(futures.get("change_pct"))
        fut_basis = self._to_float(futures.get("basis"))  # now in % (premium/discount)
        futures_raw = self._clip((-(fut_change or 0.0) / 3.0) + (-(fut_basis or 0.0) / 1.0), -1.0, 1.0)

        foreign_net = self._to_float(flow.get("foreign_net"))
        flow_raw = self._clip((-(foreign_net or 0.0)) / 1_000_000_000.0, -1.0, 1.0)

        # Freshness decay (half-life in seconds, extended off-hours)
        is_market = self._is_krx_market_hours()
        mult = 1 if is_market else self._OFF_HOURS_MULTIPLIER
        fx_hl = self._HALF_LIFE_FX * mult
        futures_hl = self._HALF_LIFE_FUTURES * mult
        flow_hl = self._HALF_LIFE_FLOW * mult

        fx_decay = self._stale_decay(freshness.get("fx_age_sec"), half_life_sec=fx_hl)
        futures_decay = self._stale_decay(freshness.get("futures_age_sec"), half_life_sec=futures_hl)
        flow_decay = self._stale_decay(freshness.get("flow_age_sec"), half_life_sec=flow_hl)

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

        reason_detail = self._build_reason_detail(
            fx_raw, futures_raw, flow_raw,
            fx_decay, futures_decay, flow_decay,
            regime,
            fx_hl, futures_hl, flow_hl,
        )

        # --- Confidence score (0-100) ---
        signal_confidence, confidence_band = self._compute_confidence(weighted)

        return {
            "macro_score": macro_score,
            "regime": regime,
            "reason": reason_detail["summary"],
            "reason_detail": reason_detail,
            "updated_at": self._to_iso(now),
            "signal_confidence": signal_confidence,
            "confidence_band": confidence_band,
        }

    def _build_reason_detail(
        self,
        fx_raw: float,
        futures_raw: float,
        flow_raw: float,
        fx_decay: float,
        futures_decay: float,
        flow_decay: float,
        regime: str,
        fx_hl: int = 600,
        futures_hl: int = 600,
        flow_hl: int = 900,
    ) -> Dict[str, Any]:
        weights = {"fx": 0.40, "futures": 0.35, "flow": 0.25}

        def _component(raw: float, decay: float, weight: float, half_life_sec: int) -> Dict[str, Any]:
            return {
                "raw": round(raw, 4),
                "decay": round(decay, 4),
                "weight": weight,
                "contribution": round(raw * decay * weight, 4),
                "half_life_sec": half_life_sec,
            }

        parts = [
            f"fx={fx_raw:.2f} (decay={fx_decay:.2f})",
            f"futures={futures_raw:.2f} (decay={futures_decay:.2f})",
            f"flow={flow_raw:.2f} (decay={flow_decay:.2f})",
        ]

        return {
            "version": 1,
            "summary": f"{regime}: " + ", ".join(parts),
            "components": {
                "fx": _component(fx_raw, fx_decay, weights["fx"], fx_hl),
                "futures": _component(futures_raw, futures_decay, weights["futures"], futures_hl),
                "flow": _component(flow_raw, flow_decay, weights["flow"], flow_hl),
            },
        }

    @staticmethod
    def _compute_confidence(weighted: list) -> tuple:
        """Compute signal confidence (0-100) and band.

        Components:
          1. Availability (0-100): each missing component = -33 penalty
          2. Freshness (0-100): average decay across available components × 100
          3. Agreement (0-100): all same sign = 100, mixed = proportional
        Final = (availability × 0.25) + (freshness × 0.40) + (agreement × 0.35)
        """
        available_count = sum(1 for _, _, _, avail in weighted if avail)
        availability_score = (available_count / len(weighted)) * 100

        # Average decay across available components
        decays = [decay for _, _, decay, avail in weighted if avail]
        freshness_score = (sum(decays) / len(decays) * 100) if decays else 0

        # Agreement: check sign direction of raw scores
        raws = [raw for _, raw, _, avail in weighted if avail]
        if len(raws) >= 2:
            positive = sum(1 for r in raws if r > 0.05)
            negative = sum(1 for r in raws if r < -0.05)
            dominant = max(positive, negative)
            agreement_score = (dominant / len(raws)) * 100
        else:
            agreement_score = 50  # single component — medium

        confidence = round(
            availability_score * 0.25 + freshness_score * 0.40 + agreement_score * 0.35
        )
        confidence = max(0, min(100, confidence))

        if confidence >= 70:
            band = "high"
        elif confidence >= 40:
            band = "medium"
        else:
            band = "low"

        return confidence, band

    # ------------------------------------------------------------------
    # Background history collector
    # ------------------------------------------------------------------

    def run_history_collector(self, interval_sec: int = 60) -> None:
        macro_history_service.run_history_collector(self, interval_sec)

    # ------------------------------------------------------------------
    # Interpretation helpers
    # ------------------------------------------------------------------

    def _build_interpretation(
        self,
        fx: Dict[str, Any],
        futures: Dict[str, Any],
        flow: Dict[str, Any],
    ) -> Dict[str, Any]:
        return macro_interpretation_service.build_interpretation(self, fx, futures, flow)

    def _interpret_fx(self, fx: Dict[str, Any]) -> str:
        return macro_interpretation_service.interpret_fx(self, fx)

    def _interpret_futures(self, futures: Dict[str, Any]) -> str:
        return macro_interpretation_service.interpret_futures(self, futures)

    def _interpret_flow(self, flow: Dict[str, Any]) -> str:
        return macro_interpretation_service.interpret_flow(self, flow)

    def _derive_entry_signal(self, fx_interp: str, futures_interp: str, flow_interp: str) -> str:
        return macro_interpretation_service.derive_entry_signal(fx_interp, futures_interp, flow_interp)

    @staticmethod
    def _derive_posture(
        regime: str,
        confidence_band: Optional[str],
        entry_signal: str,
    ) -> tuple:
        return macro_interpretation_service.derive_posture(regime, confidence_band, entry_signal)

    def _append_history(self, bundle: Dict[str, Any], now: datetime) -> None:
        macro_history_service.append_history(self, bundle, now)

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    def _load_history_from_db(self) -> None:
        macro_history_service.load_history_from_db(self)

    # ------------------------------------------------------------------
    # Historical backfill
    # ------------------------------------------------------------------

    _BACKFILL_MAX_DAYS = 35

    def _backfill_history(self) -> None:
        macro_history_service.backfill_history(self)

    def _fetch_fx_historical(self, start_date: date, end_date: date) -> Dict[date, float]:
        return macro_history_service.fetch_fx_historical(self, start_date, end_date)

    def _fetch_futures_historical(self, days: int) -> Dict[date, float]:
        return macro_history_service.fetch_futures_historical(self, days)

    # KST market hours for hourly interpolation (00:00-09:00 UTC = 09:00-18:00 KST)
    _BACKFILL_HOURS_UTC = list(range(0, 10))  # 0..9 UTC = 9..18 KST

    def _merge_daily_backfill(
        self,
        fx_daily: Dict[date, float],
        futures_daily: Dict[date, float],
        last_ts: datetime,
    ) -> List[Dict[str, Any]]:
        return macro_history_service.merge_daily_backfill(self, fx_daily, futures_daily, last_ts)

    def _flush_to_db(self) -> None:
        macro_history_service.flush_to_db(self)

    # Cap DB query results to prevent excessive memory usage
    _DB_QUERY_LIMIT = 50_000

    def _query_db_history(self, min_ts: datetime, max_ts: datetime) -> List[Dict[str, Any]]:
        return macro_history_service.query_db_history(self, min_ts, max_ts)

    _MAX_WINDOW = timedelta(days=90)

    def _parse_window(self, window: str) -> timedelta:
        return macro_history_service.parse_window(self, window)


_singleton_instance: Optional[MacroMarketService] = None


def get_macro_market_service(market_service: Optional[MarketService] = None) -> MacroMarketService:
    """Return a cached singleton MacroMarketService instance."""
    global _singleton_instance  # noqa: PLW0603
    if _singleton_instance is None:
        if market_service is None:
            market_service = MarketService()
        _singleton_instance = MacroMarketService(market_service=market_service)
    return _singleton_instance
