"""HTTP client for the IBKR Client Portal Gateway API.

Uses ``httpx.Client`` with token-bucket rate limiting and automatic retry
for transient errors (429 / 5xx).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

import httpx

from brokers.exceptions import BrokerConnectionError
from brokers.ibkr.constants import (
    DEFAULT_GATEWAY_URL,
    HTTP_BACKOFF_BASE,
    HTTP_MAX_RETRIES,
    RATE_LIMIT_MAX_TOKENS,
    RATE_LIMIT_REFILL_INTERVAL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token bucket rate limiter
# ---------------------------------------------------------------------------


class _TokenBucket:
    """Simple token-bucket rate limiter (thread-safe)."""

    def __init__(
        self,
        max_tokens: int = RATE_LIMIT_MAX_TOKENS,
        refill_interval: float = RATE_LIMIT_REFILL_INTERVAL,
    ) -> None:
        self._max_tokens = max_tokens
        self._tokens = float(max_tokens)
        self._refill_interval = refill_interval
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            time.sleep(0.05)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed / self._refill_interval * self._max_tokens
        self._tokens = min(self._max_tokens, self._tokens + new_tokens)
        self._last_refill = now


# ---------------------------------------------------------------------------
# IBKR HTTP Client
# ---------------------------------------------------------------------------


class IBKRClient:
    """Thin HTTP wrapper around the Client Portal REST API.

    Parameters
    ----------
    base_url:
        Gateway URL (default ``https://localhost:5000``).
    """

    def __init__(self, base_url: str = DEFAULT_GATEWAY_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._bucket = _TokenBucket()
        self._http = httpx.Client(
            base_url=f"{self._base_url}/v1/api",
            verify=False,  # Client Portal uses self-signed certs
            timeout=httpx.Timeout(10.0, connect=5.0),
        )

    # -- public methods -----------------------------------------------------

    def get(self, path: str) -> Any:
        """Send a GET request and return the parsed JSON body."""
        return self._request("GET", path)

    def post(self, path: str, json: Optional[dict] = None) -> Any:
        """Send a POST request and return the parsed JSON body."""
        return self._request("POST", path, json=json)

    def delete(self, path: str) -> Any:
        """Send a DELETE request and return the parsed JSON body."""
        return self._request("DELETE", path)

    def close(self) -> None:
        """Close the underlying HTTP transport."""
        self._http.close()

    # -- internal -----------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict] = None,
    ) -> Any:
        last_exc: Optional[Exception] = None

        for attempt in range(HTTP_MAX_RETRIES):
            self._bucket.acquire()
            try:
                resp = self._http.request(method, path, json=json)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise BrokerConnectionError(
                    f"IBKR gateway unreachable at {self._base_url}: {exc}"
                ) from exc

            if resp.status_code < 400:
                return resp.json() if resp.content else {}

            # Client errors (4xx except 429) are not retryable
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                body = resp.text
                logger.warning(
                    "IBKR API %s %s returned %d: %s",
                    method,
                    path,
                    resp.status_code,
                    body,
                )
                return resp.json() if resp.content else {}

            # 429 or 5xx: exponential backoff
            last_exc = httpx.HTTPStatusError(
                f"{resp.status_code}",
                request=resp.request,
                response=resp,
            )
            wait = HTTP_BACKOFF_BASE * (2**attempt)
            logger.warning(
                "IBKR API %s %s returned %d, retrying in %.1fs (attempt %d/%d)",
                method,
                path,
                resp.status_code,
                wait,
                attempt + 1,
                HTTP_MAX_RETRIES,
            )
            time.sleep(wait)

        raise BrokerConnectionError(
            f"IBKR API {method} {path} failed after {HTTP_MAX_RETRIES} retries"
        ) from last_exc
