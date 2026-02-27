"""
Generic in-memory TTL cache with LRU eviction.

Thread-safe implementation suitable for caching API responses,
computed values, and other short-lived data.  Supports caching
``None`` values (distinguishes cache miss from stored None via
an internal sentinel).
"""

import threading
import time
from collections import OrderedDict
from typing import Callable, Generic, Optional, TypeVar

_V = TypeVar("_V")

# Sentinel to distinguish "key not in cache" from "key cached with value None".
_MISSING = object()


class TTLCache(Generic[_V]):
    """In-memory cache with per-entry TTL and bounded LRU eviction.

    Parameters
    ----------
    ttl_seconds:
        Time-to-live for each entry in seconds.
    max_size:
        Maximum number of entries.  When exceeded the least-recently-used
        entry is evicted.
    """

    def __init__(self, ttl_seconds: float, max_size: int = 512) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size

        # OrderedDict stores (monotonic_timestamp, value) tuples.
        # Most-recently-used entries are moved to the *end*.
        self._store: OrderedDict[str, tuple[float, _V]] = OrderedDict()

        # Global lock protects ``_store`` mutations.
        self._lock = threading.RLock()

        # Per-key locks prevent thundering herd in ``get_or_set``.
        self._key_locks: dict[str, threading.Lock] = {}
        self._key_locks_guard = threading.Lock()

        # Stats
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[_V]:
        """Return cached value or ``None`` on miss.

        To distinguish a cached ``None`` from a miss use the internal
        ``_get_raw`` helper (or rely on ``get_or_set``).
        """
        result = self._get_raw(key)
        if result is _MISSING:
            return None
        return result  # type: ignore[return-value]

    def set(self, key: str, value: _V) -> None:
        """Store *value* under *key*, evicting oldest if over capacity."""
        now = time.monotonic()
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (now, value)
            self._evict()

    def get_or_set(self, key: str, loader: Callable[[], _V]) -> _V:
        """Return cached value or atomically populate via *loader*.

        Only one thread will execute *loader* for the same key at a time,
        preventing the thundering-herd problem on cold start.
        """
        # Fast path: check cache under the global lock.
        raw = self._get_raw(key)
        if raw is not _MISSING:
            return raw  # type: ignore[return-value]

        # Slow path: acquire per-key lock, then double-check.
        key_lock = self._lock_for(key)
        with key_lock:
            raw = self._get_raw(key)
            if raw is not _MISSING:
                return raw  # type: ignore[return-value]

            value = loader()
            self.set(key, value)
            return value

    def invalidate(self, key: str) -> None:
        """Remove a single key from the cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    @property
    def stats(self) -> dict:
        """Return ``{hits, misses, size}``."""
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._store),
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_raw(self, key: str) -> object:
        """Return cached value or ``_MISSING`` sentinel."""
        with self._lock:
            entry = self._store.get(key, _MISSING)
            if entry is _MISSING:
                self._misses += 1
                return _MISSING

            ts, value = entry  # type: ignore[unpacking]
            if time.monotonic() - ts > self._ttl:
                # Expired – remove lazily.
                del self._store[key]
                self._misses += 1
                return _MISSING

            # Promote to most-recently-used.
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def _evict(self) -> None:
        """Pop oldest entries until size <= max_size. Caller must hold ``_lock``."""
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def _lock_for(self, key: str) -> threading.Lock:
        """Return (or create) a per-key lock for thundering-herd prevention."""
        with self._key_locks_guard:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[key] = lock
            return lock
