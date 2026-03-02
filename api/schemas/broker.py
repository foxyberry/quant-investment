"""
Unified broker API schemas for request/response validation.

Provides Pydantic models for broker-agnostic order management.
Reuses enums from ``brokers.base`` to stay in sync with the adapter layer.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from brokers.base import ConnectionState, OrderSide, OrderStatus, OrderType


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class BrokerOrderRequest(BaseModel):
    """Order placement request body."""

    ticker: str = Field(..., description="Instrument symbol")
    side: OrderSide = Field(..., description="Order direction")
    quantity: int = Field(..., gt=0, description="Number of shares/contracts")
    order_type: OrderType = Field(
        OrderType.MARKET, description="Market or limit"
    )
    price: Optional[float] = Field(
        None, description="Limit price (required for LIMIT orders)"
    )
    account_id: Optional[str] = Field(
        None, description="Target account (None = broker default)"
    )


class BrokerAmendRequest(BaseModel):
    """Order amendment request body."""

    quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    price: Optional[float] = Field(None, description="New limit price")


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class BrokerOrderResponse(BaseModel):
    """Order snapshot returned by the API."""

    order_id: str = Field(..., description="Broker-assigned order identifier")
    broker: str = Field(..., description="Originating broker name")
    ticker: str = Field(..., description="Instrument symbol")
    side: OrderSide = Field(..., description="Order direction")
    quantity: int = Field(..., description="Originally requested quantity")
    filled_quantity: int = Field(0, description="Quantity filled so far")
    unfilled_quantity: int = Field(0, description="Remaining unfilled quantity")
    order_type: OrderType = Field(..., description="Market or limit")
    price: Optional[float] = Field(None, description="Limit price")
    filled_price: Optional[float] = Field(None, description="Average fill price")
    status: OrderStatus = Field(..., description="Current lifecycle status")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: Optional[str] = Field(
        None, description="Last modification timestamp"
    )


class BrokerConnectionResponse(BaseModel):
    """Broker connection status response."""

    broker: str = Field(..., description="Broker identifier")
    status: ConnectionState = Field(..., description="Connection state")
    is_paper_trading: Optional[bool] = Field(
        None, description="Whether running in paper-trading mode"
    )
    accounts: List[str] = Field(
        default_factory=list, description="Accessible account numbers"
    )
    updated_at: Optional[str] = Field(
        None, description="Last status change timestamp"
    )


class BrokerKillSwitchResponse(BaseModel):
    """Kill switch activation response."""

    activated: bool = Field(
        ..., description="Whether the kill switch was activated"
    )
    cancelled_orders: int = Field(0, description="Number of orders cancelled")


class BrokerListResponse(BaseModel):
    """List of registered brokers."""

    brokers: List[str] = Field(
        default_factory=list, description="Registered broker names"
    )


class BrokerSettingsResponse(BaseModel):
    """Aggregated broker status payload for settings page."""

    brokers: List[BrokerConnectionResponse] = Field(
        default_factory=list, description="Broker statuses for settings page"
    )


class TigerSettingsRequest(BaseModel):
    """Tiger broker credential payload for settings save."""

    tiger_id: str = Field(..., description="Tiger developer ID")
    account: str = Field(..., description="Tiger account number")
    private_key: Optional[str] = Field(
        None, description="Tiger RSA private key PEM content"
    )
    license: str = Field(default="TBNZ", description="Tiger license type")
    sandbox: bool = Field(default=False, description="Tiger sandbox mode")


class TigerSettingsResponse(BaseModel):
    """Tiger broker settings payload safe for UI."""

    tiger_id: Optional[str] = None
    account: Optional[str] = None
    license: Optional[str] = None
    sandbox: bool = False
    has_private_key: bool = False
    updated_at: Optional[str] = None


class IBKRSettingsRequest(BaseModel):
    """IBKR Client Portal Gateway settings payload."""

    gateway_url: str = Field(
        default="https://localhost:5000",
        description="Client Portal Gateway base URL",
    )
    account_id: Optional[str] = Field(
        None, description="IBKR account ID (auto-discovered if empty)"
    )


class IBKRSettingsResponse(BaseModel):
    """IBKR broker settings payload safe for UI."""

    gateway_url: Optional[str] = None
    account_id: Optional[str] = None
    updated_at: Optional[str] = None
