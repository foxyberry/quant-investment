"""FRED API client for US rates and credit spread indicators."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# yfinance ticker mapping for FRED series fallback
_YFINANCE_FALLBACK: Dict[str, str] = {
    "DGS10": "^TNX",   # CBOE 10-Year Treasury Yield Index
    "DGS2": "2YY=F",   # 2-Year T-Note Yield Futures
}


class FredService:
    """Fetches latest FRED series value with in-memory TTL cache.

    When FRED_API_KEY is not set, falls back to yfinance for supported series.
    """

    CACHE_TTL_SECONDS = 3600
    API_TIMEOUT_SECONDS = 10

    def __init__(self) -> None:
        self._api_key = os.getenv("FRED_API_KEY")
        if not self._api_key:
            logger.warning("FRED_API_KEY not set — will use yfinance fallback for US rates")
        self._lock = threading.RLock()
        self._cache: Dict[str, Optional[float]] = {}
        self._cache_time: Dict[str, float] = {}

    def get_series(self, series_id: str) -> Optional[float]:
        """Return the latest observation value for a FRED series."""
        value, _ = self.get_series_with_date(series_id)
        return value

    def get_series_with_date(self, series_id: str) -> Tuple[Optional[float], Optional[str]]:
        """Return (value, observation_date) for the latest valid FRED observation."""
        series = (series_id or "").strip().upper()
        if not series:
            return None, None

        now = time.monotonic()
        cache_key = f"{series}:dated"
        with self._lock:
            if cache_key in self._cache and (now - self._cache_time.get(cache_key, 0.0)) < self.CACHE_TTL_SECONDS:
                return self._cache[cache_key], self._cache.get(f"{series}:obs_date")

        if self._api_key:
            value, obs_date = self._fetch_latest(series)
        else:
            value, obs_date = self._fetch_yfinance_fallback(series)

        with self._lock:
            self._cache[cache_key] = value
            self._cache[f"{series}:obs_date"] = obs_date
            self._cache_time[cache_key] = now
        return value, obs_date

    def _fetch_latest(self, series_id: str) -> Tuple[Optional[float], Optional[str]]:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": "10",
        }
        try:
            response = requests.get(url, params=params, timeout=self.API_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
            observations = payload.get("observations") or []
            for obs in observations:
                raw_value = obs.get("value")
                if raw_value not in (None, "."):
                    return float(raw_value), obs.get("date")
            return None, None
        except Exception:
            logger.warning("Failed to fetch FRED series: %s", series_id, exc_info=True)
            return None, None

    @staticmethod
    def _fetch_yfinance_fallback(series_id: str) -> Tuple[Optional[float], Optional[str]]:
        """Fetch US rates from yfinance when FRED API key is unavailable.

        Includes a sanity check: yield values must be in [0, 20]% range
        to guard against data-unit mismatches between sources.
        """
        ticker_symbol = _YFINANCE_FALLBACK.get(series_id)
        if ticker_symbol is None:
            return None, None

        try:
            import yfinance as yf  # noqa: PLC0415

            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")
            if hist is None or hist.empty:
                return None, None

            close_col = "Close" if "Close" in hist.columns else None
            if close_col is None:
                return None, None

            closes = hist[close_col].dropna()
            if closes.empty:
                return None, None

            value = round(float(closes.iloc[-1]), 4)

            # Sanity check: treasury yields should be in 0-20% range
            if not (0.0 <= value <= 20.0):
                logger.warning(
                    "yfinance fallback value %.4f for %s (%s) out of sane range [0, 20] — discarded",
                    value,
                    series_id,
                    ticker_symbol,
                )
                return None, None

            obs_date = closes.index[-1].strftime("%Y-%m-%d")
            return value, obs_date
        except Exception:
            logger.warning(
                "yfinance fallback failed for FRED series %s (ticker %s)",
                series_id,
                ticker_symbol,
                exc_info=True,
            )
            return None, None


_fred_service: Optional[FredService] = None


def get_fred_service() -> FredService:
    """Return singleton FredService instance."""
    global _fred_service
    if _fred_service is None:
        _fred_service = FredService()
    return _fred_service

