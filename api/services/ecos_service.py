"""ECOS API client for Korean government bond rates."""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class EcosService:
    """Fetches latest ECOS statistic values with in-memory TTL cache."""

    CACHE_TTL_SECONDS = 3600
    API_TIMEOUT_SECONDS = 10

    def __init__(self) -> None:
        self._api_key = os.getenv("ECOS_API_KEY")
        if not self._api_key:
            logger.warning("ECOS_API_KEY not set — KR bond rates will be unavailable")
        self._lock = threading.RLock()
        self._cache: Dict[str, Optional[float]] = {}
        self._cache_time: Dict[str, float] = {}

    def get_stat_value(self, stat_code: str, item_code: str) -> Optional[float]:
        """Return latest ECOS value for a stat/item pair."""
        if not self._api_key:
            return None

        stat = (stat_code or "").strip()
        item = (item_code or "").strip()
        if not stat or not item:
            return None

        cache_key = f"{stat}:{item}"
        now = time.monotonic()
        with self._lock:
            if cache_key in self._cache and (now - self._cache_time.get(cache_key, 0.0)) < self.CACHE_TTL_SECONDS:
                return self._cache[cache_key]

        value = self._fetch_latest(stat, item)
        with self._lock:
            self._cache[cache_key] = value
            self._cache_time[cache_key] = now
        return value

    def _fetch_latest(self, stat_code: str, item_code: str) -> Optional[float]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        # ECOS uses path-based API key — mask it in logs by only logging stat/item
        url = (
            "https://ecos.bok.or.kr/api/StatisticSearch/"
            f"{self._api_key}/json/kr/1/1/{stat_code}/DD/"
            f"{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}/{item_code}"
        )
        try:
            response = requests.get(url, timeout=self.API_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
            rows = (payload.get("StatisticSearch") or {}).get("row") or []
            if not rows:
                return None
            raw_value = rows[0].get("DATA_VALUE")
            if raw_value is None:
                return None
            return float(raw_value)
        except Exception:
            logger.warning(
                "Failed to fetch ECOS statistic: stat_code=%s item_code=%s",
                stat_code,
                item_code,
                exc_info=True,
            )
            return None


_ecos_service: Optional[EcosService] = None


def get_ecos_service() -> EcosService:
    """Return singleton EcosService instance."""
    global _ecos_service
    if _ecos_service is None:
        _ecos_service = EcosService()
    return _ecos_service

