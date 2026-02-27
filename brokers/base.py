"""Broker abstraction base module.

Defines the canonical enums, Pydantic DTOs, abstract adapter interface,
and a singleton registry/factory that concrete broker implementations
plug into.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Dict, List, Optional, Type

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OrderSide(str, Enum):
    """Direction of an order."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Price determination strategy."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    """Lifecycle status of an order."""

    RECEIVED = "RECEIVED"
    CONFIRMED = "CONFIRMED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"


class ConnectionState(str, Enum):
    """Broker connection state."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    UNAVAILABLE = "unavailable"


# ---------------------------------------------------------------------------
# DTOs (Pydantic v2 BaseModel)
# ---------------------------------------------------------------------------


class ConnectionStatus(BaseModel):
    """Snapshot of the broker connection state.

    Attributes:
        broker: Identifier of the broker (e.g. ``"kiwoom"``, ``"alpaca"``).
        status: Current connection state.
        is_paper_trading: ``True`` when running on a paper/mock server.
        user_id: Authenticated user identifier, if available.
        accounts: List of account numbers accessible through this connection.
        updated_at: ISO-8601 timestamp of the last status change.
    """

    broker: str = Field(..., description="Broker identifier")
    status: ConnectionState = Field(..., description="Current connection state")
    is_paper_trading: Optional[bool] = Field(
        None, description="Whether running in paper-trading mode"
    )
    user_id: Optional[str] = Field(None, description="Authenticated user ID")
    accounts: List[str] = Field(
        default_factory=list, description="Accessible account numbers"
    )
    updated_at: Optional[str] = Field(
        None, description="Last status change timestamp (ISO 8601)"
    )


class OrderRequest(BaseModel):
    """Parameters required to place a new order.

    Attributes:
        ticker: Instrument symbol (e.g. ``"005930"`` for Samsung).
        side: Buy or sell.
        quantity: Number of shares/contracts. Must be > 0.
        order_type: Market or limit.
        price: Required for limit orders; ignored for market orders.
        account_id: Target account. ``None`` uses the broker default.
    """

    ticker: str = Field(..., description="Instrument symbol")
    side: OrderSide = Field(..., description="Order direction")
    quantity: int = Field(..., gt=0, description="Number of shares/contracts")
    order_type: OrderType = Field(..., description="Market or limit")
    price: Optional[float] = Field(
        None, description="Limit price (required for LIMIT orders)"
    )
    account_id: Optional[str] = Field(
        None, description="Target account (None = broker default)"
    )

    @model_validator(mode="after")
    def _check_limit_price(self) -> OrderRequest:
        if self.order_type == OrderType.LIMIT and not self.price:
            raise ValueError("price is required for LIMIT orders")
        return self


class OrderSnapshot(BaseModel):
    """Immutable point-in-time view of an order.

    Attributes:
        order_id: Broker-assigned unique identifier.
        broker: Originating broker name.
        ticker: Instrument symbol.
        side: Buy or sell.
        quantity: Originally requested quantity.
        filled_quantity: Quantity filled so far.
        unfilled_quantity: Remaining quantity.
        order_type: Market or limit.
        price: Limit price (``None`` for market orders).
        filled_price: Volume-weighted average fill price.
        status: Current lifecycle status.
        created_at: Creation timestamp (ISO 8601).
        updated_at: Last modification timestamp (ISO 8601).
    """

    order_id: str = Field(..., description="Broker-assigned order identifier")
    broker: str = Field(..., description="Originating broker name")
    ticker: str = Field(..., description="Instrument symbol")
    side: OrderSide = Field(..., description="Order direction")
    quantity: int = Field(..., description="Originally requested quantity")
    filled_quantity: int = Field(0, description="Quantity filled so far")
    unfilled_quantity: int = Field(0, description="Remaining unfilled quantity")
    order_type: OrderType = Field(..., description="Market or limit")
    price: Optional[float] = Field(
        None, description="Limit price (None for market orders)"
    )
    filled_price: Optional[float] = Field(
        None, description="Volume-weighted average fill price"
    )
    status: OrderStatus = Field(..., description="Current lifecycle status")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: Optional[str] = Field(
        None, description="Last modification timestamp (ISO 8601)"
    )


class AmendRequest(BaseModel):
    """Parameters for amending an existing order.

    At least one of ``quantity`` or ``price`` must be provided.

    Attributes:
        quantity: New quantity (must be > 0 if provided).
        price: New limit price.
    """

    quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    price: Optional[float] = Field(None, description="New limit price")

    @model_validator(mode="after")
    def _check_at_least_one(self) -> AmendRequest:
        if self.quantity is None and self.price is None:
            raise ValueError("at least one of quantity or price must be provided")
        return self


class KillSwitchResult(BaseModel):
    """Outcome of a kill-switch activation.

    Attributes:
        activated: Whether the kill switch was successfully activated.
        cancelled_orders: Number of open orders that were cancelled.
    """

    activated: bool = Field(..., description="Whether the kill switch was activated")
    cancelled_orders: int = Field(0, description="Number of orders cancelled")


class OrderEvent(BaseModel):
    """Real-time order status update pushed to subscribers.

    Attributes:
        broker: Originating broker name.
        order_id: Broker-assigned order identifier.
        ticker: Instrument symbol.
        status: New lifecycle status.
        filled_quantity: Cumulative filled quantity.
        unfilled_quantity: Remaining unfilled quantity.
        filled_price: Latest (or average) fill price.
    """

    broker: str = Field(..., description="Originating broker name")
    order_id: str = Field(..., description="Broker-assigned order identifier")
    ticker: str = Field(..., description="Instrument symbol")
    status: OrderStatus = Field(..., description="New lifecycle status")
    filled_quantity: int = Field(0, description="Cumulative filled quantity")
    unfilled_quantity: int = Field(0, description="Remaining unfilled quantity")
    filled_price: Optional[float] = Field(None, description="Latest fill price")


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

OrderCallback = Callable[[OrderEvent], None]
"""Signature for real-time order event listeners."""


# ---------------------------------------------------------------------------
# Abstract Broker Adapter
# ---------------------------------------------------------------------------


class BrokerAdapter(ABC):
    """Vendor-agnostic interface that every broker integration must implement.

    Concrete subclasses provide market-specific logic (e.g. Kiwoom for KRX,
    Alpaca for US equities) while callers interact through this uniform API.
    """

    # -- identity -----------------------------------------------------------

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return the canonical broker identifier (e.g. ``"kiwoom"``)."""

    @property
    @abstractmethod
    def supported_markets(self) -> List[str]:
        """Return market codes this adapter can trade (e.g. ``["KRX"]``)."""

    # -- connection ---------------------------------------------------------

    @abstractmethod
    def get_connection_status(self) -> ConnectionStatus:
        """Return the current connection state.

        Returns:
            A ``ConnectionStatus`` snapshot.

        Raises:
            BrokerConnectionError: If the status cannot be determined.
        """

    # -- order lifecycle ----------------------------------------------------

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderSnapshot:
        """Submit a new order to the broker.

        Args:
            request: Validated order parameters.

        Returns:
            An ``OrderSnapshot`` with at least ``RECEIVED`` status.

        Raises:
            BrokerValidationError: If the request fails broker-side validation.
            BrokerConnectionError: If the broker is unreachable.
            BrokerSafetyError: If a safety rule blocks the order.
        """

    @abstractmethod
    def get_orders(self) -> List[OrderSnapshot]:
        """Retrieve all tracked orders for the current session.

        Returns:
            A list of ``OrderSnapshot`` objects (may be empty).

        Raises:
            BrokerConnectionError: If the broker is unreachable.
        """

    @abstractmethod
    def cancel_order(self, order_id: str) -> None:
        """Cancel an open order.

        Args:
            order_id: Broker-assigned order identifier.

        Raises:
            OrderNotFoundError: If the order does not exist.
            BrokerConnectionError: If the broker is unreachable.
            BrokerSafetyError: If cancellation is blocked by a safety rule.
        """

    @abstractmethod
    def amend_order(self, order_id: str, request: AmendRequest) -> None:
        """Modify an open order (quantity and/or price).

        Args:
            order_id: Broker-assigned order identifier.
            request: Fields to amend.

        Raises:
            OrderNotFoundError: If the order does not exist.
            BrokerValidationError: If the amendment is invalid.
            BrokerConnectionError: If the broker is unreachable.
        """

    # -- emergency ----------------------------------------------------------

    @abstractmethod
    def activate_kill_switch(self) -> KillSwitchResult:
        """Activate the emergency kill switch.

        Cancels all open orders and blocks new submissions until reset.

        Returns:
            A ``KillSwitchResult`` with the count of cancelled orders.

        Raises:
            BrokerConnectionError: If the broker is unreachable.
        """

    # -- real-time subscriptions --------------------------------------------

    @abstractmethod
    def subscribe_orders(self, callback: OrderCallback) -> None:
        """Register a callback for real-time order events.

        Args:
            callback: Function invoked with each ``OrderEvent``.

        Raises:
            BrokerConnectionError: If the subscription cannot be established.
        """

    @abstractmethod
    def unsubscribe_orders(self, callback: OrderCallback) -> None:
        """Remove a previously registered order event callback.

        Args:
            callback: The exact callback reference passed to ``subscribe_orders``.
        """


# ---------------------------------------------------------------------------
# Broker Registry (Factory)
# ---------------------------------------------------------------------------


class BrokerRegistry:
    """Thread-safe factory that maps broker names to lazy singleton adapters.

    Usage::

        registry = BrokerRegistry()
        registry.register("kiwoom", KiwoomAdapter)
        adapter = registry.get("kiwoom")   # instantiated on first call
    """

    def __init__(self) -> None:
        self._classes: Dict[str, Type[BrokerAdapter]] = {}
        self._instances: Dict[str, BrokerAdapter] = {}
        self._lock = threading.Lock()

    def register(self, name: str, adapter_class: Type[BrokerAdapter]) -> None:
        """Register an adapter class under the given name.

        Args:
            name: Canonical broker identifier (case-sensitive).
            adapter_class: A concrete ``BrokerAdapter`` subclass.

        Raises:
            TypeError: If *adapter_class* is not a ``BrokerAdapter`` subclass.
        """
        if not (isinstance(adapter_class, type) and issubclass(adapter_class, BrokerAdapter)):
            raise TypeError(
                f"adapter_class must be a BrokerAdapter subclass, got {adapter_class!r}"
            )
        with self._lock:
            self._classes[name] = adapter_class
            # Invalidate a cached instance so the new class takes effect.
            old = self._instances.pop(name, None)
            if old is not None and hasattr(old, "close"):
                try:
                    old.close()
                except Exception:
                    pass

    def get(self, name: str) -> BrokerAdapter:
        """Return a singleton adapter instance for *name*.

        The adapter is instantiated lazily on the first call and reused
        on subsequent calls.

        Args:
            name: Registered broker identifier.

        Returns:
            A ``BrokerAdapter`` instance.

        Raises:
            KeyError: If *name* has not been registered.
        """
        with self._lock:
            if name in self._instances:
                return self._instances[name]
            cls = self._classes.get(name)
            if cls is None:
                raise KeyError(f"broker {name!r} is not registered")
            instance = cls()
            self._instances[name] = instance
            return instance

    def list_brokers(self) -> List[str]:
        """Return registered broker names in sorted order."""
        with self._lock:
            return sorted(self._classes)

    def is_registered(self, name: str) -> bool:
        """Check whether a broker name is registered."""
        with self._lock:
            return name in self._classes

    def reset(self, name: str) -> None:
        """Drop a cached adapter instance so it will be recreated on next get()."""
        with self._lock:
            old = self._instances.pop(name, None)
        if old is not None and hasattr(old, "close"):
            try:
                old.close()
            except Exception:
                pass
