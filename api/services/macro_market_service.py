"""Macro market aggregation service.

Combines FX, futures proxy, and investor-flow inputs into a single
macro bundle payload with stale-data decay scoring.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from collections import deque
from datetime import date, datetime, timedelta, timezone
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

        # Session-start FX baseline for daily change calculation
        self._session_start_fx: Optional[float] = None
        self._session_start_date: Optional[date] = None

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

        interpretation = self._build_interpretation(fx, futures, flow)

        bundle = {
            "fx": fx,
            "futures": futures,
            "flow": flow,
            "signal": signal,
            "freshness": freshness,
            "interpretation": interpretation,
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

            # Reset session baseline at the start of each day
            today = now.date()
            if value is not None:
                if self._session_start_date != today or self._session_start_fx is None:
                    self._session_start_fx = value
                    self._session_start_date = today

            change_pct: Optional[float] = None
            if value is not None and self._session_start_fx not in (None, 0):
                change_pct = ((value - float(self._session_start_fx)) / float(self._session_start_fx)) * 100.0
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
        fut_basis = self._to_float(futures.get("basis"))  # now in % (premium/discount)
        futures_raw = self._clip((-(fut_change or 0.0) / 3.0) + (-(fut_basis or 0.0) / 1.0), -1.0, 1.0)

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

    # ------------------------------------------------------------------
    # Background history collector
    # ------------------------------------------------------------------

    def run_history_collector(self, interval_sec: int = 60) -> None:
        """Blocking loop that appends history every *interval_sec* seconds.

        Designed to run inside a daemon thread so the timeline fills
        independently of API calls.
        """
        logger.info("Macro history collector started (interval=%ds)", interval_sec)
        while True:
            try:
                self.get_bundle()
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


_singleton_instance: Optional[MacroMarketService] = None


def get_macro_market_service(market_service: Optional[MarketService] = None) -> MacroMarketService:
    """Return a cached singleton MacroMarketService instance."""
    global _singleton_instance  # noqa: PLW0603
    if _singleton_instance is None:
        if market_service is None:
            market_service = MarketService()
        _singleton_instance = MacroMarketService(market_service=market_service)
    return _singleton_instance
