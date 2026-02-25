"""IBKR Client Portal session management.

Handles authentication status checks, account discovery, and periodic
keepalive via the ``/tickle`` endpoint.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, List, Optional

from brokers.ibkr.client import IBKRClient
from brokers.ibkr.constants import TICKLE_INTERVAL, TICKLE_MAX_FAILURES

logger = logging.getLogger(__name__)


class IBKRSessionManager:
    """Manage the IBKR Client Portal Gateway session.

    Parameters
    ----------
    client:
        An :class:`IBKRClient` instance for API calls.
    """

    def __init__(self, client: IBKRClient) -> None:
        self._client = client

        # Keepalive state
        self._stop_event = threading.Event()
        self._keepalive_thread: Optional[threading.Thread] = None
        self._consecutive_failures: int = 0
        self._disconnected: bool = False

    # -- public API ---------------------------------------------------------

    def check_auth_status(self) -> dict[str, Any]:
        """Check gateway authentication status.

        Returns
        -------
        dict
            Keys: ``authenticated`` (bool), ``connected`` (bool).
        """
        data = self._client.post("/iserver/auth/status")
        return {
            "authenticated": bool(data.get("authenticated", False)),
            "connected": bool(data.get("connected", False)),
        }

    def discover_accounts(self) -> list[dict[str, Any]]:
        """Discover brokerage accounts.

        Returns
        -------
        list[dict]
            Each dict has ``account_id`` (str) and ``is_paper`` (bool).
            Paper accounts have IDs starting with ``DU``.
        """
        data = self._client.get("/iserver/accounts")
        raw_accounts: List[str] = data.get("accounts", [])
        return [
            {
                "account_id": acct,
                "is_paper": acct.startswith("DU"),
            }
            for acct in raw_accounts
        ]

    @property
    def is_disconnected(self) -> bool:
        """True if the keepalive has detected gateway disconnection."""
        return self._disconnected

    # -- keepalive ----------------------------------------------------------

    def start_keepalive(self) -> None:
        """Start a daemon thread that sends periodic tickle requests."""
        if self._keepalive_thread and self._keepalive_thread.is_alive():
            return

        self._stop_event.clear()
        self._consecutive_failures = 0
        self._disconnected = False
        self._keepalive_thread = threading.Thread(
            target=self._keepalive_loop,
            name="ibkr-keepalive",
            daemon=True,
        )
        self._keepalive_thread.start()
        logger.info("IBKR keepalive started (interval=%.0fs)", TICKLE_INTERVAL)

    def stop_keepalive(self) -> None:
        """Stop the keepalive thread."""
        self._stop_event.set()
        if self._keepalive_thread and self._keepalive_thread.is_alive():
            self._keepalive_thread.join(timeout=5.0)
        self._keepalive_thread = None
        logger.info("IBKR keepalive stopped")

    def _keepalive_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._client.post("/tickle")
                self._consecutive_failures = 0
            except Exception:
                self._consecutive_failures += 1
                logger.warning(
                    "IBKR tickle failed (%d/%d)",
                    self._consecutive_failures,
                    TICKLE_MAX_FAILURES,
                )
                if self._consecutive_failures >= TICKLE_MAX_FAILURES:
                    self._disconnected = True
                    logger.error(
                        "IBKR gateway presumed disconnected after %d tickle failures",
                        TICKLE_MAX_FAILURES,
                    )
                    return  # Stop the keepalive loop

            self._stop_event.wait(TICKLE_INTERVAL)
