"""Broker abstraction layer.

Provides a vendor-agnostic interface for trading operations.
Concrete adapters (e.g. Kiwoom, Alpaca) implement ``BrokerAdapter``
and register themselves via ``BrokerRegistry``.

Module-level convenience helpers :func:`get_broker` and
:func:`list_brokers` operate on a default registry that auto-registers
all built-in adapters on first import.
"""

from __future__ import annotations

import logging
from typing import List

from brokers.base import (
    AmendRequest,
    BrokerAdapter,
    BrokerRegistry,
    ConnectionState,
    ConnectionStatus,
    KillSwitchResult,
    OrderCallback,
    OrderEvent,
    OrderRequest,
    OrderSide,
    OrderSnapshot,
    OrderStatus,
    OrderType,
)
from brokers.exceptions import (
    BrokerConnectionError,
    BrokerError,
    BrokerSafetyError,
    BrokerValidationError,
    OrderNotFoundError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default global registry
# ---------------------------------------------------------------------------

_default_registry: BrokerRegistry = BrokerRegistry()
_registry_initialised: bool = False


def _register_default_brokers() -> None:
    """Lazily register all built-in broker adapters.

    Each adapter import is wrapped in a ``try``/``except`` so that a
    missing optional dependency (e.g. the Kiwoom COM library on Linux)
    does not prevent the rest of the package from loading.
    """
    global _registry_initialised  # noqa: PLW0603
    if _registry_initialised:
        return
    _registry_initialised = True

    # -- Kiwoom adapter ----------------------------------------------------
    try:
        from brokers.kiwoom.adapter import KiwoomBrokerAdapter

        _default_registry.register("kiwoom", KiwoomBrokerAdapter)
        logger.debug("Registered broker adapter: kiwoom")
    except Exception:
        logger.debug("Kiwoom adapter not available; skipping registration", exc_info=True)

    # -- IBKR adapter ------------------------------------------------------
    try:
        from brokers.ibkr.adapter import IBKRBrokerAdapter

        _default_registry.register("ibkr", IBKRBrokerAdapter)
        logger.debug("Registered broker adapter: ibkr")
    except Exception:
        logger.debug("IBKR adapter not available; skipping registration", exc_info=True)

    # -- Tiger adapter ------------------------------------------------------
    try:
        from brokers.tiger.adapter import TigerBrokerAdapter

        _default_registry.register("tiger", TigerBrokerAdapter)
        logger.debug("Registered broker adapter: tiger")
    except Exception:
        logger.debug("Tiger adapter not available; skipping registration", exc_info=True)


def get_broker(name: str) -> BrokerAdapter:
    """Return an adapter instance from the default registry.

    Parameters
    ----------
    name:
        Broker identifier (e.g. ``"kiwoom"``).

    Raises
    ------
    KeyError
        If *name* is not registered.
    """
    _register_default_brokers()
    return _default_registry.get(name)


def list_brokers() -> List[str]:
    """Return the names of all registered brokers."""
    _register_default_brokers()
    return _default_registry.list_brokers()


def refresh_broker(name: str) -> None:
    """Reset a cached broker adapter instance by name."""
    _register_default_brokers()
    _default_registry.reset(name)


__all__ = [
    # Exceptions
    "BrokerError",
    "BrokerConnectionError",
    "BrokerValidationError",
    "OrderNotFoundError",
    "BrokerSafetyError",
    # Enums
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "ConnectionState",
    # DTOs
    "ConnectionStatus",
    "OrderRequest",
    "OrderSnapshot",
    "AmendRequest",
    "KillSwitchResult",
    "OrderEvent",
    # Type aliases
    "OrderCallback",
    # ABC
    "BrokerAdapter",
    # Factory
    "BrokerRegistry",
    # Convenience helpers
    "get_broker",
    "list_brokers",
    "refresh_broker",
]
