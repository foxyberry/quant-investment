"""US market snapshot service for macro dashboard US mode."""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class UsMarketService:
    """Collects S&P 500 and Fed Funds Rate data for the US macro view."""

    CACHE_TTL_MARKET = 300
    CACHE_TTL_OFF_HOURS = 1800

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0.0

    def _is_us_market_hours(self) -> bool:
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]
        now_et = datetime.now(ZoneInfo("America/New_York"))
        # NYSE: Mon-Fri 09:30 ~ 16:00 ET (DST-aware)
        if now_et.weekday() >= 5:
            return False
        t = now_et.hour * 60 + now_et.minute
        return 570 <= t < 960  # 9:30=570min, 16:00=960min

    def _get_cache_ttl(self) -> int:
        return self.CACHE_TTL_MARKET if self._is_us_market_hours() else self.CACHE_TTL_OFF_HOURS

    @staticmethod
    def _to_iso_ts(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    def _fetch_sp500(self) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        try:
            import yfinance as yf
        except Exception:
            logger.warning("Failed to import yfinance for S&P 500 fetch", exc_info=True)
            return None, None, None

        value: Optional[float] = None
        change_pct: Optional[float] = None
        as_of: Optional[str] = None

        try:
            ticker = yf.Ticker("^GSPC")

            try:
                fast_info = ticker.fast_info or {}
                last_price = fast_info.get("lastPrice")
                if last_price is not None:
                    value = float(last_price)
            except Exception:
                logger.warning("Failed to fetch S&P 500 fast_info", exc_info=True)

            hist = ticker.history(period="2d")
            if hist is None or getattr(hist, "empty", True):
                if value is None:
                    return None, None, None
                return value, None, None

            close_col = "Close" if "Close" in hist.columns else None
            if close_col is None:
                if value is None:
                    return None, None, None
                return value, None, None

            closes = hist[close_col].dropna().tolist()
            closes = [float(v) for v in closes]

            if closes:
                latest_close = closes[-1]
                if value is None:
                    value = latest_close
                as_of = self._to_iso_ts(hist.index[-1])
                if len(closes) >= 2 and closes[-2] != 0:
                    change_pct = round(((latest_close - closes[-2]) / closes[-2]) * 100.0, 4)

            if value is None:
                return None, None, None
            return value, change_pct, as_of
        except Exception:
            logger.warning("Failed to fetch S&P 500 snapshot", exc_info=True)
            return None, None, None

    def _fetch_fed_funds_rate(self) -> Tuple[Optional[float], Optional[str]]:
        try:
            from api.services.fred_service import get_fred_service

            value, as_of = get_fred_service().get_series_with_date("DFF")
            return value, as_of
        except Exception:
            logger.warning("Failed to fetch Fed Funds Rate from FRED", exc_info=True)
            return None, None

    def get_snapshot(self) -> Dict[str, Any]:
        now = time.monotonic()
        ttl = self._get_cache_ttl()
        with self._lock:
            if self._cache is not None and (now - self._cache_time) < ttl:
                return self._cache

        sp500_value, sp500_change_pct, sp500_as_of = self._fetch_sp500()
        fed_funds_rate, fed_funds_as_of = self._fetch_fed_funds_rate()

        snapshot = {
            "sp500_value": sp500_value,
            "sp500_change_pct": sp500_change_pct,
            "sp500_as_of": sp500_as_of,
            "fed_funds_rate": fed_funds_rate,
            "fed_funds_as_of": fed_funds_as_of,
        }
        with self._lock:
            self._cache = snapshot
            self._cache_time = now
        return snapshot


_us_market_service: Optional[UsMarketService] = None


def get_us_market_service() -> UsMarketService:
    """Return singleton UsMarketService instance."""
    global _us_market_service
    if _us_market_service is None:
        _us_market_service = UsMarketService()
    return _us_market_service
