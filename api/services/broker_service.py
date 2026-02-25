"""
Unified broker service layer.

Wraps :func:`brokers.get_broker` / :func:`brokers.list_brokers` behind a
thin service that API routers consume.  Adapter instances are cached by
the underlying :class:`BrokerRegistry` singleton, so this service itself
is stateless and safe to instantiate per-request or as a module-level
singleton.
"""

from __future__ import annotations

import logging
from typing import List

from brokers import get_broker, list_brokers
from brokers.base import (
    AmendRequest,
    BrokerAdapter,
    ConnectionStatus,
    KillSwitchResult,
    OrderRequest,
    OrderSnapshot,
)

logger = logging.getLogger(__name__)


class BrokerService:
    """Broker-agnostic service exposing the common trading operations."""

    def get_adapter(self, broker: str) -> BrokerAdapter:
        """Return the cached adapter for *broker*.

        Raises ``KeyError`` if the broker name is not registered.
        """
        return get_broker(broker)

    def list_brokers(self) -> List[str]:
        """Return registered broker names."""
        return list_brokers()

    def get_connection_status(self, broker: str) -> ConnectionStatus:
        """Return the connection status for *broker*."""
        adapter = self.get_adapter(broker)
        return adapter.get_connection_status()

    def place_order(self, broker: str, request: OrderRequest) -> OrderSnapshot:
        """Place a new order through *broker*."""
        adapter = self.get_adapter(broker)
        return adapter.place_order(request)

    def get_orders(self, broker: str) -> List[OrderSnapshot]:
        """Return all tracked orders for *broker*."""
        adapter = self.get_adapter(broker)
        return adapter.get_orders()

    def cancel_order(self, broker: str, order_id: str) -> None:
        """Cancel an open order on *broker*."""
        adapter = self.get_adapter(broker)
        adapter.cancel_order(order_id)

    def amend_order(
        self, broker: str, order_id: str, request: AmendRequest
    ) -> None:
        """Amend an open order on *broker*."""
        adapter = self.get_adapter(broker)
        adapter.amend_order(order_id, request)

    def activate_kill_switch(self, broker: str) -> KillSwitchResult:
        """Activate the kill switch on *broker*."""
        adapter = self.get_adapter(broker)
        return adapter.activate_kill_switch()
