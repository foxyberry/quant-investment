"""Ticker-to-conid resolution cache for IBKR.

Caches contract ID lookups with a configurable TTL (default 1 hour).
Thread-safe via ``RLock``.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from brokers.exceptions import BrokerValidationError
from brokers.ibkr.client import IBKRClient
from brokers.ibkr.constants import CONTRACT_CACHE_TTL

logger = logging.getLogger(__name__)


class _CacheEntry:
    __slots__ = ("conid", "expires_at")

    def __init__(self, conid: int, ttl: float) -> None:
        self.conid = conid
        self.expires_at = time.monotonic() + ttl


class ContractCache:
    """Resolve ticker symbols to IBKR contract IDs (conid).

    Parameters
    ----------
    client:
        An :class:`IBKRClient` for secdef searches.
    ttl:
        Cache entry lifetime in seconds (default 1 hour).
    """

    def __init__(
        self,
        client: IBKRClient,
        ttl: float = CONTRACT_CACHE_TTL,
    ) -> None:
        self._client = client
        self._ttl = ttl
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = threading.RLock()

    def resolve(self, ticker: str) -> int:
        """Return the conid for *ticker*, using cache when available.

        Parameters
        ----------
        ticker:
            Instrument symbol (e.g. ``"AAPL"``).

        Returns
        -------
        int
            The IBKR contract ID.

        Raises
        ------
        BrokerValidationError
            If the ticker cannot be resolved.
        """
        ticker_upper = ticker.upper()

        with self._lock:
            entry = self._cache.get(ticker_upper)
            if entry and entry.expires_at > time.monotonic():
                return entry.conid

        # Cache miss — query the gateway
        conid = self._search_conid(ticker_upper)

        with self._lock:
            self._cache[ticker_upper] = _CacheEntry(conid, self._ttl)

        return conid

    def invalidate(self, ticker: str) -> None:
        """Remove a ticker from the cache."""
        with self._lock:
            self._cache.pop(ticker.upper(), None)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._cache.clear()

    def _search_conid(self, ticker: str) -> int:
        """Search the IBKR secdef API for a stock contract."""
        data = self._client.post("/iserver/secdef/search", json={"symbol": ticker})

        if not isinstance(data, list) or len(data) == 0:
            raise BrokerValidationError(
                f"No IBKR contract found for ticker '{ticker}'"
            )

        # Prefer STK (stock) secType
        for entry in data:
            sections = entry.get("sections", [])
            for section in sections:
                if section.get("secType") == "STK":
                    conid = self._extract_conid(entry)
                    if conid is not None:
                        logger.debug("Resolved %s -> conid %d (STK)", ticker, conid)
                        return conid

        # Fallback: use first result
        conid = self._extract_conid(data[0])
        if conid is not None:
            logger.debug("Resolved %s -> conid %d (fallback)", ticker, conid)
            return conid

        raise BrokerValidationError(
            f"No valid conid found for ticker '{ticker}'"
        )

    @staticmethod
    def _extract_conid(entry: dict) -> Optional[int]:
        """Extract conid from a secdef search result entry."""
        raw = entry.get("conid")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
        return None
