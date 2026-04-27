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
from api.models.macro_history import MacroHistory
from api.services.exchange_rate_service import ExchangeRateService, get_exchange_rate_service
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
        now_mono = time.monotonic()
        normalized = (window or "60m").strip().lower()

        # Check history cache
        with self._lock:
            cached = getattr(self, "_history_cache", {}).get(normalized)
            if cached:
                cached_at, cached_result = cached
                ttl = self._HISTORY_CACHE_TTL.get(normalized, 60)
                if (now_mono - cached_at) < ttl:
                    return {"window": cached_result["window"], "points": list(cached_result["points"])}

        now = datetime.now(timezone.utc)
        delta = self._parse_window(window)
        min_ts = now - delta

        # Check if deque covers the requested range
        with self._lock:
            deque_min_ts = None
            if self._history:
                deque_min_ts = self._safe_datetime(self._history[0].get("timestamp"))

        # If deque doesn't cover the range, query DB
        if deque_min_ts is None or deque_min_ts > min_ts:
            # Flush pending buffer first so DB is up-to-date
            self._flush_to_db()
            db_points = self._query_db_history(min_ts, now)
            if db_points:
                result = {"window": window, "points": self._downsample_points(db_points, window)}
                self._cache_history(normalized, now_mono, result)
                return result

        # Reverse scan: deque is chronological, so iterate from newest.
        # Stop early once we pass the time boundary.
        points = []
        with self._lock:
            for p in reversed(self._history):
                dt = self._safe_datetime(p.get("timestamp"))
                if not dt:
                    continue
                if dt < min_ts:
                    break
                points.append({
                    "timestamp": p["timestamp"],
                    "fx_value": p.get("fx_value"),
                    "futures_value": p.get("futures_value"),
                    "foreign_net": p.get("foreign_net"),
                    "macro_score": p.get("macro_score"),
                    "regime": p.get("regime", "unknown"),
                    "vix": p.get("vix"),
                })
        points.reverse()  # restore chronological order

        result = {"window": window, "points": self._downsample_points(points, window)}
        self._cache_history(normalized, now_mono, result)
        return result

    def _cache_history(self, window: str, mono_time: float, result: Dict[str, Any]) -> None:
        """Store history result in per-window TTL cache."""
        with self._lock:
            if not hasattr(self, "_history_cache"):
                self._history_cache: Dict[str, tuple] = {}
            self._history_cache[window] = (mono_time, result)

    @classmethod
    def _downsample_points(
        cls, points: List[Dict[str, Any]], window: str
    ) -> List[Dict[str, Any]]:
        """Downsample history points by bucketing into fixed time intervals.

        For each bucket, take the *last* value of every field (snapshot semantics).
        This keeps the data accurate while reducing SVG DOM nodes for Recharts.
        """
        normalized = (window or "60m").strip().lower()
        bucket_sec = cls._DOWNSAMPLE_BUCKETS.get(normalized, 0)
        target = cls._DOWNSAMPLE_TARGETS.get(normalized, 0)
        # Skip if no bucket size or point count is within target
        if bucket_sec <= 0 or (target > 0 and len(points) <= target) or (target <= 0 and len(points) <= 500):
            return points

        buckets: Dict[int, Dict[str, Any]] = {}
        for p in points:
            ts_str = p.get("timestamp")
            if not ts_str:
                continue
            dt = cls._safe_datetime(ts_str)
            if not dt:
                continue
            epoch = int(dt.timestamp())
            bucket_key = (epoch // bucket_sec) * bucket_sec
            # Last-write wins: later points in the same bucket overwrite earlier ones
            buckets[bucket_key] = p

        # Fallback to original if bucketing produced nothing (e.g. all timestamps invalid)
        downsampled = [buckets[k] for k in sorted(buckets)]
        return downsampled if downsampled else points

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
        """Blocking loop that appends history every *interval_sec* seconds.

        Designed to run inside a daemon thread so the timeline fills
        independently of API calls.  Flushes to DB after each tick.
        """
        logger.info("Macro history collector started (interval=%ds)", interval_sec)
        while True:
            try:
                self.get_bundle(force_refresh=True)
                # Flush any buffered points to DB each tick
                self._flush_to_db()
            except Exception as exc:
                logger.warning("History collector tick failed: %s", exc)
            time.sleep(interval_sec)

    # ------------------------------------------------------------------
    # Interpretation helpers
    # ------------------------------------------------------------------

    def _build_interpretation(
        self,
        fx: Dict[str, Any],
        futures: Dict[str, Any],
        flow: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Produce human-readable interpretation of each data source."""
        fx_interp = self._interpret_fx(fx)
        futures_interp = self._interpret_futures(futures)
        flow_interp = self._interpret_flow(flow)
        entry_signal = self._derive_entry_signal(fx_interp, futures_interp, flow_interp)

        return {
            "entry_signal": entry_signal,
            "fx_interpretation": fx_interp,
            "futures_interpretation": futures_interp,
            "flow_interpretation": flow_interp,
        }

    def _interpret_fx(self, fx: Dict[str, Any]) -> str:
        change = self._to_float(fx.get("change_pct"))
        if change is None:
            return "unavailable"
        if change > 0.5:
            return "rising_strong"
        if change > 0.1:
            return "rising"
        if change < -0.5:
            return "falling_strong"
        if change < -0.1:
            return "falling"
        return "stable"

    def _interpret_futures(self, futures: Dict[str, Any]) -> str:
        basis = self._to_float(futures.get("basis"))  # premium/discount in %
        if basis is None:
            return "unavailable"
        if basis > 0.1:
            return "contango"
        if basis < -0.1:
            return "backwardation"
        return "flat"

    def _interpret_flow(self, flow: Dict[str, Any]) -> str:
        foreign = self._to_float(flow.get("foreign_net"))
        if foreign is None:
            return "unavailable"
        if foreign > 50_000_000_000:
            return "foreign_strong_buy"
        if foreign > 0:
            return "foreign_buy"
        if foreign < -50_000_000_000:
            return "foreign_strong_sell"
        if foreign < 0:
            return "foreign_sell"
        return "neutral"

    def _derive_entry_signal(self, fx_interp: str, futures_interp: str, flow_interp: str) -> str:
        """Combine interpretations into an actionable entry signal."""
        positive = 0
        negative = 0

        # FX: falling KRW/USD is good for KR equities (capital inflow)
        if fx_interp in ("falling", "falling_strong"):
            positive += 1
        elif fx_interp in ("rising", "rising_strong"):
            negative += 1

        # Futures: contango means optimistic
        if futures_interp == "contango":
            positive += 1
        elif futures_interp == "backwardation":
            negative += 1

        # Flow: foreign buying is positive
        if flow_interp in ("foreign_buy", "foreign_strong_buy"):
            positive += 1
        elif flow_interp in ("foreign_sell", "foreign_strong_sell"):
            negative += 1

        if positive >= 2 and negative == 0:
            return "buy_favorable"
        if negative >= 2:
            return "caution"
        return "wait"

    @staticmethod
    def _derive_posture(
        regime: str,
        confidence_band: Optional[str],
        entry_signal: str,
    ) -> tuple:
        """Derive execution posture from regime + confidence + entry_signal.

        Returns (posture, posture_rationale_key) where rationale_key is an
        i18n key the frontend maps to a translated explanation.

        Posture matrix:
          risk_on + caution entry              → wait (override)
          risk_on + high conf + buy_favorable  → risk_on_full
          risk_on + medium conf                → risk_on_small
          neutral / low conf                   → wait
          risk_off + any                       → risk_off_defensive
          risk_off + high conf + caution       → hedge_bias
        """
        if regime == "risk_off":
            if confidence_band == "high" and entry_signal == "caution":
                return "hedge_bias", "posture_hedge_bias"
            return "risk_off_defensive", "posture_risk_off_defensive"

        if regime == "risk_on":
            # Caution entry overrides risk-on → demote to wait
            if entry_signal == "caution":
                return "wait", "posture_wait_neutral"
            if confidence_band == "high" and entry_signal == "buy_favorable":
                return "risk_on_full", "posture_risk_on_full"
            if confidence_band in ("high", "medium"):
                return "risk_on_small", "posture_risk_on_small"
            return "wait", "posture_wait_low_confidence"

        # neutral or unknown
        return "wait", "posture_wait_neutral"

    def _append_history(self, bundle: Dict[str, Any], now: datetime) -> None:
        signal = bundle.get("signal", {})
        fx = bundle.get("fx", {})
        futures = bundle.get("futures", {})
        flow = bundle.get("flow", {})

        # Fetch VIX from volatility service (lazy import to avoid circular deps)
        vix_value: float | None = None
        try:
            from api.services.volatility_service import get_volatility_service
            vol = get_volatility_service().get_snapshot()
            if vol:
                vix_value = self._to_float(vol.get("vix"))
        except Exception as exc:
            logger.debug("VIX fetch for history point failed: %s", exc)

        point = {
            "timestamp": self._to_iso(now),
            "fx_value": self._to_float(fx.get("value")),
            "futures_value": self._to_float(futures.get("value")),
            "foreign_net": self._to_float(flow.get("foreign_net")),
            "macro_score": self._to_float(signal.get("macro_score")),
            "regime": signal.get("regime", "unknown"),
            "vix": vix_value,
        }
        should_flush = False
        with self._lock:
            self._history.append(point)
            self._db_buffer.append(point)
            self._db_tick_count += 1
            # Invalidate history cache — new data available
            if hasattr(self, "_history_cache"):
                self._history_cache.clear()
            if self._db_tick_count >= self._DB_FLUSH_INTERVAL:
                should_flush = True

        if should_flush:
            self._flush_to_db()

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    def _load_history_from_db(self) -> None:
        """Load recent macro history rows from DB into the in-memory deque."""
        try:
            db: Session = SessionLocal()
            try:
                rows = (
                    db.query(MacroHistory)
                    .order_by(desc(MacroHistory.timestamp))
                    .limit(self._history.maxlen or 50_000)
                    .all()
                )
                rows.reverse()  # oldest first
                for row in rows:
                    ts = row.timestamp
                    if ts and ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    self._history.append({
                        "timestamp": ts.isoformat() if ts else None,
                        "fx_value": row.fx_value,
                        "futures_value": row.futures_value,
                        "foreign_net": row.foreign_net,
                        "macro_score": row.macro_score,
                        "regime": row.regime or "unknown",
                        "vix": getattr(row, "vix", None),
                    })
                if rows:
                    logger.info("Loaded %d macro history rows from DB", len(rows))
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Failed to load macro history from DB: %s", exc)

    # ------------------------------------------------------------------
    # Historical backfill
    # ------------------------------------------------------------------

    _BACKFILL_MAX_DAYS = 35

    def _backfill_history(self) -> None:
        """Backfill missing daily history from external APIs.

        Detects the last recorded timestamp in DB and fills gaps with daily
        FX + futures data so the 30d timeline is complete even after server
        restarts.
        """
        try:
            db: Session = SessionLocal()
            try:
                latest = db.query(MacroHistory).order_by(desc(MacroHistory.timestamp)).first()
            finally:
                db.close()

            now = datetime.now(timezone.utc)
            if latest and latest.timestamp:
                last_ts = latest.timestamp
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                gap = now - last_ts
            else:
                gap = timedelta(days=self._BACKFILL_MAX_DAYS)
                last_ts = now - gap

            if gap < timedelta(hours=12):
                logger.info("Macro history gap < 12h, skipping backfill")
                return

            days_to_fill = min(int(gap.total_seconds() / 86400) + 1, self._BACKFILL_MAX_DAYS)
            start_date = (now - timedelta(days=days_to_fill)).date()
            end_date = (now - timedelta(days=1)).date()

            if start_date >= end_date:
                return

            logger.info(
                "Backfilling macro history from %s to %s (%d days gap)",
                start_date, end_date, days_to_fill,
            )

            fx_daily = self._fetch_fx_historical(start_date, end_date)
            futures_daily = self._fetch_futures_historical(days_to_fill + 5)
            backfill_points = self._merge_daily_backfill(fx_daily, futures_daily, last_ts)

            if not backfill_points:
                logger.info("No backfill points to insert")
                return

            db = SessionLocal()
            try:
                for point in backfill_points:
                    ts = self._safe_datetime(point.get("timestamp"))
                    if ts is None:
                        continue
                    db.add(MacroHistory(
                        timestamp=ts,
                        fx_value=point.get("fx_value"),
                        futures_value=point.get("futures_value"),
                        foreign_net=None,
                        macro_score=point.get("macro_score"),
                        regime=point.get("regime"),
                    ))
                db.commit()
                logger.info("Backfilled %d macro history points", len(backfill_points))
            finally:
                db.close()

            # Reload deque to include backfilled data
            with self._lock:
                self._history.clear()
            self._load_history_from_db()

        except Exception as exc:
            logger.warning("Macro history backfill failed: %s", exc)

    def _fetch_fx_historical(self, start_date: date, end_date: date) -> Dict[date, float]:
        """Fetch daily USD/KRW rates from Frankfurter API."""
        try:
            import requests

            url = (
                f"https://api.frankfurter.app/{start_date}..{end_date}"
                f"?from=USD&to=KRW"
            )
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            result: Dict[date, float] = {}
            for date_str, rate_dict in data.get("rates", {}).items():
                d = date.fromisoformat(date_str)
                krw = rate_dict.get("KRW")
                if krw is not None:
                    result[d] = float(krw)
            logger.info("Fetched %d daily FX rates for backfill", len(result))
            return result
        except Exception as exc:
            logger.warning("Failed to fetch historical FX rates: %s", exc)
            return {}

    def _fetch_futures_historical(self, days: int) -> Dict[date, float]:
        """Fetch daily KODEX 200 close prices via market service."""
        try:
            ohlcv = self.market_service.get_ohlcv(self.futures_ticker, days=days)
            if not ohlcv or not ohlcv.get("data"):
                return {}
            result: Dict[date, float] = {}
            for item in ohlcv["data"]:
                d = date.fromisoformat(item["time"])
                result[d] = float(item["close"])
            logger.info("Fetched %d daily futures prices for backfill", len(result))
            return result
        except Exception as exc:
            logger.warning("Failed to fetch historical futures data: %s", exc)
            return {}

    # KST market hours for hourly interpolation (00:00-09:00 UTC = 09:00-18:00 KST)
    _BACKFILL_HOURS_UTC = list(range(0, 10))  # 0..9 UTC = 9..18 KST

    def _merge_daily_backfill(
        self,
        fx_daily: Dict[date, float],
        futures_daily: Dict[date, float],
        last_ts: datetime,
    ) -> List[Dict[str, Any]]:
        """Merge daily FX + futures into hourly-interpolated backfill points.

        For each trading day, generates hourly points during KST market hours
        (09:00-18:00 KST = 00:00-09:00 UTC) with linearly interpolated values.
        This ensures ~270 points for 30 days instead of ~30 daily points.
        """
        all_dates = sorted(set(fx_daily.keys()) | set(futures_daily.keys()))
        if not all_dates:
            return []

        points: List[Dict[str, Any]] = []
        prev_fx: Optional[float] = None
        prev_fut: Optional[float] = None

        for idx, d in enumerate(all_dates):
            if d.weekday() > 4:  # skip weekends
                continue

            # Get current day's close values
            fx_val = fx_daily.get(d)
            fut_val = futures_daily.get(d)

            # Compute daily change for macro_score
            fx_change = None
            if fx_val is not None and prev_fx is not None and prev_fx > 0:
                fx_change = ((fx_val - prev_fx) / prev_fx) * 100
            fut_change = None
            if fut_val is not None and prev_fut is not None and prev_fut > 0:
                fut_change = ((fut_val - prev_fut) / prev_fut) * 100

            fx_raw = self._clip((fx_change or 0) / 1.5, -1.0, 1.0)
            fut_raw = self._clip(-(fut_change or 0) / 3.0, -1.0, 1.0)

            numerator = 0.0
            denominator = 0.0
            if fx_val is not None:
                numerator += 0.55 * fx_raw
                denominator += 0.55
            if fut_val is not None:
                numerator += 0.45 * fut_raw
                denominator += 0.45

            macro_score = round(numerator / denominator, 4) if denominator > 0 else None
            regime = "unknown"
            if macro_score is not None:
                if macro_score >= 0.6:
                    regime = "risk_off"
                elif macro_score <= -0.6:
                    regime = "risk_on"
                else:
                    regime = "neutral"

            # Generate hourly points within market hours
            # Interpolate from previous day's close to current day's close (no look-ahead)
            n_hours = len(self._BACKFILL_HOURS_UTC)
            for hi, h in enumerate(self._BACKFILL_HOURS_UTC):
                dt = datetime(d.year, d.month, d.day, h, 0, tzinfo=timezone.utc)
                if dt <= last_ts:
                    continue

                frac = hi / max(n_hours - 1, 1)
                h_fx = None
                if fx_val is not None:
                    start_fx = prev_fx if prev_fx is not None else fx_val
                    h_fx = round(start_fx + frac * (fx_val - start_fx), 2)
                h_fut = None
                if fut_val is not None:
                    start_fut = prev_fut if prev_fut is not None else fut_val
                    h_fut = round(start_fut + frac * (fut_val - start_fut), 2)

                points.append({
                    "timestamp": dt.isoformat(),
                    "fx_value": h_fx,
                    "futures_value": h_fut,
                    "foreign_net": None,
                    "macro_score": macro_score,
                    "regime": regime,
                })

            prev_fx = fx_val if fx_val is not None else prev_fx
            prev_fut = fut_val if fut_val is not None else prev_fut

        return points

    def _flush_to_db(self) -> None:
        """Write buffered history points to the database."""
        with self._lock:
            if not self._db_buffer:
                return
            batch = self._db_buffer[:]
            self._db_buffer.clear()
            self._db_tick_count = 0
            # Invalidate history cache on new data
            if hasattr(self, "_history_cache"):
                self._history_cache.clear()
        try:
            db: Session = SessionLocal()
            try:
                for point in batch:
                    ts = self._safe_datetime(point.get("timestamp"))
                    if ts is None:
                        continue
                    db.add(MacroHistory(
                        timestamp=ts,
                        fx_value=point.get("fx_value"),
                        futures_value=point.get("futures_value"),
                        foreign_net=point.get("foreign_net"),
                        macro_score=point.get("macro_score"),
                        regime=point.get("regime"),
                        vix=point.get("vix"),
                    ))
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Failed to flush macro history to DB: %s", exc)
            # Restore failed batch to buffer for retry
            with self._lock:
                self._db_buffer = batch + self._db_buffer

    # Cap DB query results to prevent excessive memory usage
    _DB_QUERY_LIMIT = 50_000

    def _query_db_history(self, min_ts: datetime, max_ts: datetime) -> List[Dict[str, Any]]:
        """Query macro history from DB for a time range."""
        try:
            db: Session = SessionLocal()
            try:
                rows = (
                    db.query(MacroHistory)
                    .filter(MacroHistory.timestamp >= min_ts, MacroHistory.timestamp <= max_ts)
                    .order_by(MacroHistory.timestamp)
                    .limit(self._DB_QUERY_LIMIT)
                    .all()
                )
                return [
                    {
                        "timestamp": (r.timestamp.replace(tzinfo=timezone.utc) if r.timestamp and r.timestamp.tzinfo is None else r.timestamp).isoformat() if r.timestamp else None,
                        "fx_value": r.fx_value,
                        "futures_value": r.futures_value,
                        "foreign_net": r.foreign_net,
                        "macro_score": r.macro_score,
                        "regime": r.regime or "unknown",
                        "vix": getattr(r, "vix", None),
                    }
                    for r in rows
                ]
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Failed to query macro history from DB: %s", exc)
            return []

    _MAX_WINDOW = timedelta(days=90)

    def _parse_window(self, window: str) -> timedelta:
        value = (window or "60m").strip().lower()
        try:
            if value.endswith("m"):
                delta = timedelta(minutes=max(int(value[:-1] or "60"), 1))
            elif value.endswith("h"):
                delta = timedelta(hours=max(int(value[:-1] or "1"), 1))
            elif value.endswith("d"):
                delta = timedelta(days=max(int(value[:-1] or "1"), 1))
            else:
                delta = timedelta(minutes=60)
            return min(delta, self._MAX_WINDOW)
        except ValueError:
            logger.warning("Invalid macro history window: %s. Falling back to 60m.", value)
        return timedelta(minutes=60)


_singleton_instance: Optional[MacroMarketService] = None


def get_macro_market_service(market_service: Optional[MarketService] = None) -> MacroMarketService:
    """Return a cached singleton MacroMarketService instance."""
    global _singleton_instance  # noqa: PLW0603
    if _singleton_instance is None:
        if market_service is None:
            market_service = MarketService()
        _singleton_instance = MacroMarketService(market_service=market_service)
    return _singleton_instance
