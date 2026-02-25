"""Tiger Brokers session management.

Wraps the ``tigeropen`` SDK's ``TigerOpenClientConfig`` and ``TradeClient``
to provide connection management and account discovery.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from brokers.exceptions import BrokerConnectionError

logger = logging.getLogger(__name__)

# Lazy SDK imports to allow graceful degradation
try:
    from tigeropen.common.consts import Language
    from tigeropen.tiger_open_config import TigerOpenClientConfig
    from tigeropen.trade.trade_client import TradeClient

    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


class TigerSession:
    """TigerOpenClientConfig + TradeClient creation and management.

    Environment Variables
    ---------------------
    TIGER_ID:
        Tiger developer ID (required).
    TIGER_PRIVATE_KEY:
        Path to RSA private key PEM file (required).
    TIGER_ACCOUNT:
        Account number (required).
    TIGER_LICENSE:
        License type (default ``"TBNZ"``).
    """

    def __init__(self) -> None:
        if not _SDK_AVAILABLE:
            raise BrokerConnectionError(
                "tigeropen SDK is not installed; run 'pip install tigeropen'"
            )

        tiger_id = os.environ.get("TIGER_ID")
        private_key_path = os.environ.get("TIGER_PRIVATE_KEY")
        account = os.environ.get("TIGER_ACCOUNT")
        license_type = os.environ.get("TIGER_LICENSE", "TBNZ")

        if not tiger_id:
            raise BrokerConnectionError("TIGER_ID environment variable is required")
        if not private_key_path:
            raise BrokerConnectionError(
                "TIGER_PRIVATE_KEY environment variable is required"
            )
        if not account:
            raise BrokerConnectionError(
                "TIGER_ACCOUNT environment variable is required"
            )

        self._config = TigerOpenClientConfig(sandbox_debug=False)
        self._config.tiger_id = tiger_id
        self._config.account = account
        self._config.language = Language.en_US
        self._config.license = license_type

        # Read private key
        try:
            with open(private_key_path, "r") as f:
                self._config.private_key = f.read()
        except FileNotFoundError:
            raise BrokerConnectionError(
                f"Private key file not found: {private_key_path}"
            )

        self._trade_client = TradeClient(self._config)
        logger.info("Tiger session initialized for account %s", account)

    @property
    def client(self) -> Any:
        """Return the ``TradeClient`` instance."""
        return self._trade_client

    @property
    def config(self) -> Any:
        """Return the ``TigerOpenClientConfig`` (needed by PushClient)."""
        return self._config

    def check_connection(self) -> bool:
        """Verify connectivity by fetching managed accounts.

        Returns
        -------
        bool
            ``True`` if the connection is healthy.

        Raises
        ------
        BrokerConnectionError
            If the connection check fails.
        """
        try:
            accounts = self._trade_client.get_managed_accounts()
            if accounts is not None:
                return True
            raise BrokerConnectionError("Tiger connection check returned None")
        except Exception as exc:
            if isinstance(exc, BrokerConnectionError):
                raise
            raise BrokerConnectionError(
                f"Tiger connection check failed: {exc}"
            ) from exc

    def get_accounts(self) -> List[dict[str, Any]]:
        """Discover available accounts.

        Returns
        -------
        list[dict]
            Each dict has ``account_id`` (str) and ``is_paper`` (bool).
            Paper accounts are detected by 17-digit numeric IDs.
        """
        try:
            accounts = self._trade_client.get_managed_accounts()
            if not accounts:
                return []
            result = []
            for acct in accounts:
                acct_str = str(acct)
                # Paper accounts typically have 17-digit numeric IDs
                is_paper = acct_str.isdigit() and len(acct_str) == 17
                result.append({"account_id": acct_str, "is_paper": is_paper})
            return result
        except Exception as exc:
            raise BrokerConnectionError(
                f"Failed to discover Tiger accounts: {exc}"
            ) from exc
