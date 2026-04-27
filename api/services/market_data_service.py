"""Market data fetching mixin for MacroMarketService.

Provides real-time data access for:
- KRW/USD FX rates (Naver, Frankfurter fallback)
- KOSPI200 futures (Naver)
- Investor flow (JSON file)
- Market breadth (JSON file)
- Upcoming economic events calendar
- Naver Stock mobile API helpers
"""

from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MarketDataMixin:
    """Mixin providing market-data fetch adapters for MacroMarketService.

    All methods rely on instance attributes initialised by MacroMarketService.__init__:
      self.exchange_service, self.market_service,
      self.investor_flow_path, self.breadth_path, self.events_calendar_path,
      self.futures_ticker,
      self._last_fx_value, self._session_start_fx, self._session_start_date
    """

    # Mapping from yfinance-style spot tickers to Naver index codes
    _SPOT_TICKER_MAP: Dict[str, str] = {
        "^KS11": "KOSPI",
        "^KQ11": "KOSDAQ",
    }
    # KOSPI 200 index code for proper basis calculation
    _KOSPI200_INDEX = "KPI200"

    # Naver mobile index code for KOSPI 200 futures
    _FUTURES_INDEX_CODE = "FUT"

    _BREADTH_STALE_SEC = 1200  # 20 minutes

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_datetime(value: Any) -> Optional[datetime]:
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

    # ------------------------------------------------------------------
    # Naver Stock mobile API helpers
    # ------------------------------------------------------------------

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

    @staticmethod
    def _parse_naver_trend_value(raw: str | None) -> float | None:
        """Parse Naver trend value like '+3,024' or '-14,264' to 억원 → KRW (원)."""
        if raw is None:
            return None
        try:
            cleaned = raw.replace(",", "").replace("+", "").strip()
            return float(cleaned) * 100_000_000  # 억원 → 원
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

    def _fetch_naver_index_trend(self, index: str) -> Dict[str, Any] | None:
        """Fetch investor trend data for an index from Naver Stock mobile API.

        Returns dict with foreignValue, institutionalValue, personalValue (억원 strings).
        """
        try:
            import requests
        except ImportError:
            return None
        try:
            url = f"https://m.stock.naver.com/api/index/{index}/trend"
            r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
            r.raise_for_status()
            body = r.json()
            if isinstance(body, dict) and body.get("foreignValue") is not None:
                return body
            return None
        except Exception as exc:
            logger.debug("Naver index trend API failed for %s: %s", index, exc)
            return None

    # ------------------------------------------------------------------
    # Snapshot adapters
    # ------------------------------------------------------------------

    def _get_fx_snapshot(self, now: datetime) -> Dict[str, Any]:
        # Primary: read from FX collector cache file
        try:
            from api.services.fx_collector import read_fx_cache, is_fx_cache_stale
            cache = read_fx_cache()
            if cache and not is_fx_cache_stale(cache):
                value = self._to_float(cache.get("value"))
                if value is not None:
                    self._last_fx_value = value
                    today = now.date()
                    if self._session_start_date != today or self._session_start_fx is None:
                        self._session_start_fx = value
                        self._session_start_date = today
                    return {
                        "pair": cache.get("pair", "USD/KRW"),
                        "value": value,
                        "change_pct": self._to_float(cache.get("change_pct")),
                        "updated_at": cache.get("updated_at"),
                    }
        except Exception as exc:
            logger.debug("FX cache read failed, falling back to direct fetch: %s", exc)

        # Fallback: direct Frankfurter fetch (cache stale or missing)
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

    def _get_futures_snapshot(self, now: datetime) -> Dict[str, Any]:
        # Primary: Naver Stock mobile API — real KOSPI200 futures (FUT)
        try:
            fut_data = self._fetch_naver_index(self._FUTURES_INDEX_CODE)

            if fut_data:
                fut_value = self._parse_naver_price(fut_data.get("closePrice"))
                change_pct = self._to_float(
                    str(fut_data.get("fluctuationsRatio", "")).replace(",", "") or None
                )
                updated_at = fut_data.get("localTradedAt")

                # Basis: futures premium/discount vs KOSPI 200 spot index (%)
                basis = None
                kpi200_data = self._fetch_naver_index(self._KOSPI200_INDEX)
                if kpi200_data:
                    kpi200_value = self._parse_naver_price(kpi200_data.get("closePrice"))
                    if fut_value is not None and kpi200_value is not None and kpi200_value > 0:
                        basis = round((fut_value - kpi200_value) / kpi200_value * 100, 3)

                # Real futures investor breakdown (억원) from FUT/trend
                investor = self._fetch_naver_index_trend(self._FUTURES_INDEX_CODE)
                foreign_net = self._parse_naver_trend_value(investor.get("foreignValue")) if investor else None
                institution_net = self._parse_naver_trend_value(investor.get("institutionalValue")) if investor else None
                individual_net = self._parse_naver_trend_value(investor.get("personalValue")) if investor else None

                return {
                    "symbol": "KOSPI200_FUT",
                    "value": fut_value,
                    "basis": basis,
                    "change_pct": change_pct,
                    "updated_at": self._to_iso(updated_at or now),
                    "foreign_net": foreign_net,
                    "institution_net": institution_net,
                    "individual_net": individual_net,
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
