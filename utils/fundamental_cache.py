"""
Persistent cache utilities for fundamentals and financial statements.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class FundamentalCache:
    """File-based JSON cache with per-entry TTL."""

    DEFAULT_CACHE_DIR = "data/cache/fundamentals"

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_key(value: str) -> str:
        return value.replace("/", "_").replace("\\", "_").replace(".", "_")

    def _cache_path(self, namespace: str, key: str) -> Path:
        return self.cache_dir / f"{self._safe_key(namespace)}__{self._safe_key(key)}.json"

    def get(self, namespace: str, key: str, ttl_seconds: int) -> Optional[Dict[str, Any]]:
        """
        Return cached payload when fresh, otherwise None.
        """
        path = self._cache_path(namespace, key)
        if not path.exists():
            return None

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            updated_at = raw.get("_updated_at")
            payload = raw.get("payload")
            if not updated_at or payload is None:
                return None

            updated_dt = datetime.fromisoformat(updated_at)
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - updated_dt > timedelta(seconds=ttl_seconds):
                return None

            if isinstance(payload, dict):
                return payload
            return None
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
        try:
            path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to write cache %s: %s", path, e)
