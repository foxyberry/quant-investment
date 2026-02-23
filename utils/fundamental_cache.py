"""
Persistent cache utilities for fundamentals and financial statements.
"""

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class FundamentalCache:
    """File-based JSON cache with per-entry TTL."""

    DEFAULT_CACHE_DIR = "data/cache/fundamentals"

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._entry_locks: Dict[str, threading.Lock] = {}
        self._entry_locks_guard = threading.Lock()

    @staticmethod
    def _safe_key(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace(".", "_")

    def _cache_path(self, namespace: str, key: str) -> Path:
        return self.cache_dir / f"{self._safe_key(namespace)}__{self._safe_key(key)}.json"

    def _lock_for(self, namespace: str, key: str) -> threading.Lock:
        lock_key = f"{self._safe_key(namespace)}::{self._safe_key(key)}"
        with self._entry_locks_guard:
            lock = self._entry_locks.get(lock_key)
            if lock is None:
                lock = threading.Lock()
                self._entry_locks[lock_key] = lock
            return lock

    def _read_fresh_payload(self, path: Path, ttl_seconds: int) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None

        raw = json.loads(path.read_text(encoding="utf-8"))
        updated_at = raw.get("_updated_at")
        payload = raw.get("payload")
        if not updated_at or payload is None:
            return None

        updated_dt = datetime.fromisoformat(updated_at)
        if updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - updated_dt > timedelta(seconds=ttl_seconds):
            try:
                path.unlink()
            except Exception:
                pass
            return None

        if isinstance(payload, dict):
            return payload
        return None

    def get(self, namespace: str, key: str, ttl_seconds: int) -> Optional[Dict[str, Any]]:
        """
        Return cached payload when fresh, otherwise None.
        """
        path = self._cache_path(namespace, key)
        lock = self._lock_for(namespace, key)

        try:
            with lock:
                return self._read_fresh_payload(path, ttl_seconds)
        except Exception as e:
            logger.debug("Failed to read cache %s: %s", path, e)
            return None

    def set(self, namespace: str, key: str, payload: Dict[str, Any]) -> None:
        """
        Persist payload to cache.
        """
        path = self._cache_path(namespace, key)
        envelope = {
            "_updated_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        lock = self._lock_for(namespace, key)
        try:
            with lock:
                path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to write cache %s: %s", path, e)

    def get_or_set(
        self,
        namespace: str,
        key: str,
        ttl_seconds: int,
        loader: Callable[[], Optional[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """
        Return fresh cached payload or atomically populate it with ``loader``.

        This prevents thundering herd on cold start by ensuring that only one
        thread executes loader for the same (namespace, key).
        """
        path = self._cache_path(namespace, key)
        lock = self._lock_for(namespace, key)
        with lock:
            try:
                cached = self._read_fresh_payload(path, ttl_seconds)
            except Exception as e:
                logger.debug("Failed to read cache %s: %s", path, e)
                cached = None

            if cached is not None:
                return cached

            payload = loader()
            if payload is None:
                return None

            envelope = {
                "_updated_at": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
            }
            try:
                path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                logger.debug("Failed to write cache %s: %s", path, e)
            return payload

    def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """
        Delete cached files and return removed file count.

        Args:
            namespace: Optional namespace filter.
            key: Optional cache key filter (requires namespace).
        """
        removed = 0

        if namespace and key:
            target = self._cache_path(namespace, key)
            if target.exists():
                target.unlink()
                return 1
            return 0

        if namespace:
            pattern = f"{self._safe_key(namespace)}__*.json"
        else:
            pattern = "*.json"

        for path in self.cache_dir.glob(pattern):
            try:
                path.unlink()
                removed += 1
            except Exception:
                continue
        return removed

    def clear_expired(self, ttl_seconds: int, namespace: Optional[str] = None) -> int:
        """
        Remove expired cache files and return removed file count.
        """
        removed = 0
        pattern = f"{self._safe_key(namespace)}__*.json" if namespace else "*.json"
        now = datetime.now(timezone.utc)

        for path in self.cache_dir.glob(pattern):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                updated_at = raw.get("_updated_at")
                if not updated_at:
                    path.unlink()
                    removed += 1
                    continue

                updated_dt = datetime.fromisoformat(updated_at)
                if updated_dt.tzinfo is None:
                    updated_dt = updated_dt.replace(tzinfo=timezone.utc)

                if now - updated_dt > timedelta(seconds=ttl_seconds):
                    path.unlink()
                    removed += 1
            except Exception:
                # Corrupted cache files are removed proactively.
                try:
                    path.unlink()
                    removed += 1
                except Exception:
                    pass
        return removed
