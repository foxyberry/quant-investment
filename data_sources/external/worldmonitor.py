"""
Worldmonitor API client.
Canonical location: data_sources/external/worldmonitor.py

Connects to a self-hosted worldmonitor instance (koala73/worldmonitor)
to fetch global macro intelligence: market radar, country risk, global brief.

Usage:
    from data_sources.external.worldmonitor import get_worldmonitor_client

    client = get_worldmonitor_client()
    radar = client.get_market_radar()
    brief = client.get_global_brief()
    risk = client.get_country_risk("KR")
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Default: self-hosted worldmonitor in docker-compose
_DEFAULT_BASE_URL = "http://localhost:3000"
_DEFAULT_TIMEOUT = 15


class WorldmonitorClient:
    """HTTP client for self-hosted worldmonitor API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("WORLDMONITOR_API_URL")
            or _DEFAULT_BASE_URL
        ).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            logger.warning("Worldmonitor unavailable at %s", self.base_url)
            return None
        except requests.exceptions.Timeout:
            logger.warning("Worldmonitor request timed out: %s", path)
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning("Worldmonitor HTTP error %s: %s", e.response.status_code, path)
            return None
        except Exception:
            logger.warning("Worldmonitor request failed: %s", path, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Market Radar — 92-exchange finance radar
    # ------------------------------------------------------------------

    def get_market_radar(self) -> Optional[Dict[str, Any]]:
        """
        Fetch global market radar data from worldmonitor.

        Returns dict with exchange quotes, indices, commodities, crypto
        across 92 exchanges worldwide.
        """
        return self._get("/api/market/v1/quotes")

    # ------------------------------------------------------------------
    # Country Risk — Country Intelligence Index (CII)
    # ------------------------------------------------------------------

    def get_country_risk(self, country_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch Country Intelligence Index for a specific country.

        Args:
            country_code: ISO 3166-1 alpha-2 code (e.g., "KR", "US", "CN")

        Returns dict with risk scores across 12 signal categories.
        """
        return self._get(
            "/api/intelligence/v1/cii",
            params={"country": country_code.upper()},
        )

    def get_all_country_risks(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch CII scores for all tracked countries."""
        return self._get("/api/intelligence/v1/cii")

    # ------------------------------------------------------------------
    # Global Brief — AI-synthesized world situation summary
    # ------------------------------------------------------------------

    def get_global_brief(self) -> Optional[Dict[str, Any]]:
        """
        Fetch AI-generated global situation brief.

        Returns a curated summary of world events across geopolitics,
        finance, energy, climate, and security domains.
        """
        return self._get("/api/intelligence/v1/brief")

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if worldmonitor instance is reachable."""
        try:
            resp = self._session.get(
                f"{self.base_url}/health",
                timeout=3,
            )
            return resp.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_client: Optional[WorldmonitorClient] = None


def get_worldmonitor_client() -> WorldmonitorClient:
    global _client
    if _client is None:
        _client = WorldmonitorClient()
    return _client
