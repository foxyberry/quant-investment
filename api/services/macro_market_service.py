"""Macro market aggregation service.

Combines FX, futures proxy, and investor-flow inputs into a single
macro bundle payload with stale-data decay scoring.
"""

from __future__ import annotations

import json
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
from api.services.market_service import MarketService

logger = logging.getLogger(__name__)


class MacroMarketService:
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

    def get_history(self, window: str = "60m") -> Dict[str, Any]:
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
                return {"window": window, "points": db_points}

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
                })
        points.reverse()  # restore chronological order

        return {"window": window, "points": points}

    def _is_krx_market_hours(self) -> bool:
        """Check if current KST time is within KRX market hours (Mon-Fri 09:00-15:40)."""
        from datetime import timezone as tz, timedelta as td

        now_kst = datetime.now(tz.utc).astimezone(tz(td(hours=9)))
        if now_kst.weekday() > 4:
            return False
        hour, minute = now_kst.hour, now_kst.minute
        if hour < 9:
            return False
        if hour > 15 or (hour == 15 and minute > 40):
            return False
        return True

    def _get_fx_snapshot(self, now: datetime) -> Dict[str, Any]:
        # Primary: Naver FX (realtime during KRW market hours)
        try:
            naver = self._fetch_naver_fx("FX_USDKRW")
            if naver:
                value = self._parse_naver_price(naver.get("closePrice"))
                change_pct = self._to_float(
                    str(naver.get("fluctuationsRatio", "")).replace(",", "") or None
                )
                updated_at = naver.get("localTradedAt")
                if value is not None:
                    self._last_fx_value = value
                    return {
                        "pair": "USD/KRW",
                        "value": value,
                        "change_pct": change_pct,
                        "updated_at": self._to_iso(updated_at or now),
                    }
        except Exception as exc:
            logger.debug("Naver FX snapshot failed, falling back: %s", exc)

        # Fallback: Frankfurter (ECB) — daily rate
        try:
            rates = self.exchange_service.get_rates(base="USD")
            value = rates.get("rates", {}).get("KRW")
            updated_at = rates.get("updated_at")
            value = float(value) if value is not None else None

            today = now.date()
            if value is not None:
                if self._session_start_date != today or self._session_start_fx is None:
                    self._session_start_fx = value
                    self._session_start_date = today

            change_pct_fb: Optional[float] = None
            if value is not None and self._session_start_fx not in (None, 0):
                change_pct_fb = ((value - float(self._session_start_fx)) / float(self._session_start_fx)) * 100.0
            self._last_fx_value = value

            return {
                "pair": "USD/KRW",
                "value": value,
                "change_pct": change_pct_fb,
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

    # Mapping from yfinance-style spot tickers to Naver index codes
    _SPOT_TICKER_MAP: Dict[str, str] = {
        "^KS11": "KOSPI",
        "^KQ11": "KOSDAQ",
    }
    # KOSPI 200 index code for proper basis calculation
    _KOSPI200_INDEX = "KPI200"
    # KODEX 200 tracks KOSPI200 at ~100x scale (KODEX price ≈ KPI200 × 100)
    _KODEX_KPI200_MULTIPLIER = 100.0

    @staticmethod
    def _parse_naver_price(raw: str | int | float | None) -> float | None:
        """Parse Naver price string like '76,245' or '5,140.87' to float."""
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        try:
            return float(raw.replace(",", "").strip())
        except (TypeError, ValueError):
            return None

    def _fetch_naver_fx(self, reuters_code: str = "FX_USDKRW") -> Dict[str, Any] | None:
        """Fetch realtime FX rate from Naver Stock front-API."""
        try:
            import requests
        except ImportError:
            return None
        try:
            url = (
                "https://m.stock.naver.com/front-api/marketIndex/productDetail"
                f"?category=exchange&reutersCode={reuters_code}"
            )
            r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
            r.raise_for_status()
            body = r.json()
            result = body.get("result") if body.get("isSuccess") else None
            return result
        except Exception as exc:
            logger.debug("Naver FX API failed for %s: %s", reuters_code, exc)
            return None

    def _fetch_naver_stock(self, code: str) -> Dict[str, Any] | None:
        """Fetch realtime stock/ETF data from Naver Stock mobile API."""
        try:
            import requests
        except ImportError:
            return None
        try:
            url = f"https://m.stock.naver.com/api/stock/{code}/basic"
            r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.debug("Naver stock API failed for %s: %s", code, exc)
            return None

    def _fetch_naver_index(self, index: str) -> Dict[str, Any] | None:
        """Fetch realtime index data from Naver Stock mobile API."""
        try:
            import requests
        except ImportError:
            return None
        try:
            url = f"https://m.stock.naver.com/api/index/{index}/basic"
            r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.debug("Naver index API failed for %s: %s", index, exc)
            return None

    def _get_futures_snapshot(self, now: datetime) -> Dict[str, Any]:
        # Primary: Naver Stock mobile API (realtime)
        try:
            futures_code = self.futures_ticker.replace(".KS", "").replace(".KQ", "")
            fut_data = self._fetch_naver_stock(futures_code)

            if fut_data:
                fut_value = self._parse_naver_price(fut_data.get("closePrice"))
                change_pct = self._to_float(
                    str(fut_data.get("fluctuationsRatio", "")).replace(",", "") or None
                )
                updated_at = fut_data.get("localTradedAt")

                # Basis: KODEX 200 premium/discount vs KOSPI 200 index (%)
                # Only meaningful when futures_ticker is KODEX 200 (069500)
                # KODEX 200 ≈ KPI200 × 100 (multiplier is fixed; deviation captured in basis %)
                basis = None
                if futures_code == "069500":
                    kpi200_data = self._fetch_naver_index(self._KOSPI200_INDEX)
                    if kpi200_data:
                        kpi200_value = self._parse_naver_price(kpi200_data.get("closePrice"))
                        if fut_value is not None and kpi200_value is not None and kpi200_value > 0:
                            theoretical = kpi200_value * self._KODEX_KPI200_MULTIPLIER
                            basis = round((fut_value - theoretical) / theoretical * 100, 3)

                return {
                    "symbol": self.futures_ticker,
                    "value": fut_value,
                    "basis": basis,
                    "change_pct": change_pct,
                    "updated_at": self._to_iso(updated_at or now),
                }
        except Exception as exc:
            logger.debug("Naver futures snapshot failed, falling back: %s", exc)

        # Fallback: yfinance cache (basis unavailable — can't compare units properly)
        try:
            fut = self.market_service.get_quote(self.futures_ticker)

            fut_value = float(fut["current_price"]) if fut and fut.get("current_price") is not None else None
            change_pct = float(fut["change_pct"]) if fut and fut.get("change_pct") is not None else None
            updated_at = fut.get("timestamp") if fut else None

            return {
                "symbol": self.futures_ticker,
                "value": fut_value,
                "basis": None,  # yfinance fallback can't compute proper basis
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

    @staticmethod
    def _compute_alignment(foreign_net: float | None, institution_net: float | None) -> str:
        """Compute foreign vs institution alignment/conflict status."""
        if foreign_net is None or institution_net is None:
            return "unknown"
        if foreign_net > 0 and institution_net > 0:
            return "aligned_buy"
        if foreign_net < 0 and institution_net < 0:
            return "aligned_sell"
        if foreign_net > 0 and institution_net < 0:
            return "foreign_lead"
        if foreign_net < 0 and institution_net > 0:
            return "institution_lead"
        return "unknown"

    @staticmethod
    def _compute_foreign_strength(foreign_net: float | None) -> str | None:
        """Compute foreign flow strength signal based on absolute value."""
        if foreign_net is None:
            return None
        abs_val = abs(foreign_net)
        if abs_val >= 500_000_000_000:  # >= 5000억
            return "strong"
        if abs_val >= 100_000_000_000:  # >= 1000억
            return "moderate"
        return "weak"

    def _get_flow_snapshot(self) -> Dict[str, Any]:
        # Primary adapter: pipeline-populated JSON file
        base = {
            "market": "KOSPI",
            "foreign_net": None,
            "institution_net": None,
            "individual_net": None,
            "window_min": None,
            "updated_at": None,
            "alignment": None,
            "foreign_strength": None,
            "kosdaq_foreign_net": None,
            "kosdaq_institution_net": None,
            "kosdaq_individual_net": None,
        }
        try:
            if self.investor_flow_path.exists():
                raw = json.loads(self.investor_flow_path.read_text(encoding="utf-8"))
                foreign = self._to_float(raw.get("foreign_net"))
                institution = self._to_float(raw.get("institution_net"))

                base.update({
                    "market": str(raw.get("market", "KOSPI")),
                    "foreign_net": foreign,
                    "institution_net": institution,
                    "individual_net": self._to_float(raw.get("individual_net")),
                    "window_min": self._to_int(raw.get("window_min")),
                    "updated_at": self._to_iso(raw.get("updated_at")),
                    "alignment": self._compute_alignment(foreign, institution),
                    "foreign_strength": self._compute_foreign_strength(foreign),
                })

                # KOSDAQ nested data (from collector)
                kq = raw.get("kosdaq")
                if isinstance(kq, dict):
                    base["kosdaq_foreign_net"] = self._to_float(kq.get("foreign_net"))
                    base["kosdaq_institution_net"] = self._to_float(kq.get("institution_net"))
                    base["kosdaq_individual_net"] = self._to_float(kq.get("individual_net"))

                return base
        except Exception as exc:
            logger.warning("Investor flow file adapter failed: %s", exc)

        return base

    _BREADTH_STALE_SEC = 1200  # 20 minutes

    def _get_breadth_snapshot(self) -> Dict[str, Any] | None:
        """Read market breadth data from JSON file produced by breadth collector."""
        try:
            if self.breadth_path.exists():
                raw = json.loads(self.breadth_path.read_text(encoding="utf-8"))
                updated_at = self._to_iso(raw.get("updated_at"))
                # Skip stale data (older than 20 min)
                if updated_at:
                    age = self._age_sec(updated_at, datetime.now(timezone.utc))
                    if age is not None and age > self._BREADTH_STALE_SEC:
                        return None
                return {
                    "market": str(raw.get("market", "KOSPI")),
                    "advancing": self._to_int(raw.get("advancing")),
                    "declining": self._to_int(raw.get("declining")),
                    "unchanged": self._to_int(raw.get("unchanged")),
                    "total": self._to_int(raw.get("total")),
                    "ad_ratio": self._to_float(raw.get("ad_ratio")),
                    "updated_at": updated_at,
                }
        except Exception as exc:
            logger.warning("Market breadth file read failed: %s", exc)
        return None

    def _get_upcoming_events(self, days_ahead: int = 14) -> list[Dict[str, Any]]:
        """Load events calendar and return events within the next N days (KST-based)."""
        try:
            if not self.events_calendar_path.exists():
                return []
            events = json.loads(self.events_calendar_path.read_text(encoding="utf-8"))
            if not isinstance(events, list):
                return []

            # Use KST-based today to match Korean market context
            kst = timezone(timedelta(hours=9))
            today = datetime.now(timezone.utc).astimezone(kst).date()

            result = []
            for ev in events:
                if not isinstance(ev, dict):
                    continue
                ev_date_str = ev.get("date")
                title_key = ev.get("title_key")
                if not ev_date_str or not title_key:
                    continue
                try:
                    ev_date = date.fromisoformat(ev_date_str)
                except ValueError:
                    continue
                d_day = (ev_date - today).days
                if 0 <= d_day <= days_ahead:
                    result.append({
                        "date": ev_date_str,
                        "type": ev.get("type", ""),
                        "title_key": title_key,
                        "importance": ev.get("importance"),
                        "d_day": d_day,
                    })
            result.sort(key=lambda x: x["d_day"])
            return result
        except Exception as exc:
            logger.warning("Events calendar load failed: %s", exc)
            return []

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

        return {
            "macro_score": macro_score,
            "regime": regime,
            "reason": reason_detail["summary"],
            "reason_detail": reason_detail,
            "updated_at": self._to_iso(now),
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

    def _append_history(self, bundle: Dict[str, Any], now: datetime) -> None:
        signal = bundle.get("signal", {})
        fx = bundle.get("fx", {})
        futures = bundle.get("futures", {})
        flow = bundle.get("flow", {})

        point = {
            "timestamp": self._to_iso(now),
            "fx_value": self._to_float(fx.get("value")),
            "futures_value": self._to_float(futures.get("value")),
            "foreign_net": self._to_float(flow.get("foreign_net")),
            "macro_score": self._to_float(signal.get("macro_score")),
            "regime": signal.get("regime", "unknown"),
        }
        should_flush = False
        with self._lock:
            self._history.append(point)
            self._db_buffer.append(point)
            self._db_tick_count += 1
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

    def _merge_daily_backfill(
        self,
        fx_daily: Dict[date, float],
        futures_daily: Dict[date, float],
        last_ts: datetime,
    ) -> List[Dict[str, Any]]:
        """Merge daily FX + futures into backfill history points."""
        all_dates = sorted(set(fx_daily.keys()) | set(futures_daily.keys()))
        if not all_dates:
            return []

        points: List[Dict[str, Any]] = []
        prev_fx: Optional[float] = None
        prev_fut: Optional[float] = None

        for d in all_dates:
            # Use 9:00 UTC (≈ 18:00 KST, after market close)
            dt = datetime(d.year, d.month, d.day, 9, 0, tzinfo=timezone.utc)
            if dt <= last_ts:
                # Track previous values for change calculation
                prev_fx = fx_daily.get(d, prev_fx)
                prev_fut = futures_daily.get(d, prev_fut)
                continue

            fx_val = fx_daily.get(d)
            fut_val = futures_daily.get(d)

            # Compute daily change percentages
            fx_change = None
            if fx_val is not None and prev_fx is not None and prev_fx > 0:
                fx_change = ((fx_val - prev_fx) / prev_fx) * 100

            fut_change = None
            if fut_val is not None and prev_fut is not None and prev_fut > 0:
                fut_change = ((fut_val - prev_fut) / prev_fut) * 100

            # Simplified signal (no basis, no flow — reweighted 55/45)
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

            points.append({
                "timestamp": dt.isoformat(),
                "fx_value": fx_val,
                "futures_value": fut_val,
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


_singleton_instance: Optional[MacroMarketService] = None


def get_macro_market_service(market_service: Optional[MarketService] = None) -> MacroMarketService:
    """Return a cached singleton MacroMarketService instance."""
    global _singleton_instance  # noqa: PLW0603
    if _singleton_instance is None:
        if market_service is None:
            market_service = MarketService()
        _singleton_instance = MacroMarketService(market_service=market_service)
    return _singleton_instance
