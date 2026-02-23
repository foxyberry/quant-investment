"""
Exchange rate service.

Fetches exchange rates from a public API and caches them for one hour.
Falls back to stale cached rates on upstream failures.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class ExchangeRateService:
    """Provides exchange rates with in-memory TTL cache and fallback."""

    DEFAULT_BASE = "USD"
    DEFAULT_SYMBOLS = ("KRW", "SGD", "JPY", "EUR", "GBP", "CNY", "HKD")
    CACHE_TTL_SECONDS = 3600
    API_TIMEOUT_SECONDS = 8

    def __init__(self):
        self._lock = threading.RLock()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Dict[str, float] = {}

    def get_rates(self, base: str = DEFAULT_BASE) -> Dict[str, Any]:
        """
        Get exchange rates for a base currency.

        Returns cached rates when fresh, otherwise fetches from upstream.
        On fetch failure, returns stale cached rates if available.
        """
        base_norm = (base or self.DEFAULT_BASE).upper().strip()
        now = time.monotonic()

        with self._lock:
            cached = self._cache.get(base_norm)
            cached_at = self._cache_time.get(base_norm, 0.0)
            if cached and (now - cached_at) < self.CACHE_TTL_SECONDS:
                return cached

        try:
            fetched = self._fetch_rates(base_norm)
            with self._lock:
                self._cache[base_norm] = fetched
                self._cache_time[base_norm] = now
            return fetched
        except Exception as e:
            logger.warning("Exchange rate fetch failed for base=%s: %s", base_norm, e)
            with self._lock:
                stale = self._cache.get(base_norm)
                if stale:
                    return stale
            raise RuntimeError(f"Exchange rate unavailable for base {base_norm}") from e

    def _fetch_rates(self, base: str) -> Dict[str, Any]:
        """Fetch rates from frankfurter.app for the configured symbol set."""
        symbols = ",".join(self.DEFAULT_SYMBOLS)
        url = (
            "https://api.frankfurter.app/latest"
            f"?from={base}&to={symbols}"
        )
        resp = requests.get(url, timeout=self.API_TIMEOUT_SECONDS)
        resp.raise_for_status()
        payload = resp.json()

        rates = payload.get("rates")
        if not isinstance(rates, dict) or not rates:
            raise ValueError("Invalid exchange rate payload")

        cleaned_rates: Dict[str, float] = {}
        for currency, value in rates.items():
            try:
                cleaned_rates[currency.upper()] = float(value)
            except (TypeError, ValueError):
                continue

        if not cleaned_rates:
            raise ValueError("No valid exchange rates in payload")

        return {
            "base": str(payload.get("base", base)).upper(),
            "rates": cleaned_rates,
            "updated_at": datetime.now(timezone.utc),
        }


_exchange_rate_service: Optional[ExchangeRateService] = None


def get_exchange_rate_service() -> ExchangeRateService:
    """Get singleton exchange rate service."""
    global _exchange_rate_service
    if _exchange_rate_service is None:
        _exchange_rate_service = ExchangeRateService()
    return _exchange_rate_service
