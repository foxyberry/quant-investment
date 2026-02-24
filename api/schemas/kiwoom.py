"""
Kiwoom trading schemas for API request/response validation.

Provides Pydantic models for connection status, orders, conditions,
and condition match results matching the frontend TypeScript types.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class KiwoomConnectionStatus(BaseModel):
    """
    Kiwoom connection status response.

    Attributes:
        status: Connection state
        is_mock_trading: Whether connected to mock-trading server
        user_id: Logged-in user ID
        accounts: List of account numbers
        updated_at: Last status update timestamp (ISO 8601)
    """

    status: Literal["connected", "disconnected", "connecting", "unavailable"] = Field(
        ..., description="Connection state"
    )
    is_mock_trading: Optional[bool] = Field(
        None, description="Whether connected to mock-trading server"
    )
    user_id: Optional[str] = Field(None, description="Logged-in user ID")
    accounts: List[str] = Field(default_factory=list, description="Account numbers")
    updated_at: Optional[str] = Field(
        None, description="Last status update timestamp (ISO 8601)"
    )


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------


class KiwoomCondition(BaseModel):
    """
    Kiwoom condition definition.

    Attributes:
        index: Condition index
        name: Condition name
    """

    index: int = Field(..., description="Condition index")
    name: str = Field(..., description="Condition name")


class KiwoomConditionMatch(BaseModel):
    """
    Stock matching a Kiwoom condition.

    Attributes:
        ticker: Stock ticker code
        name: Company name (if available)
        current_price: Current price (if available)
        updated_at: Last match update timestamp (ISO 8601)
    """

    ticker: str = Field(..., description="Stock ticker code")
    name: Optional[str] = Field(None, description="Company name")
    current_price: Optional[float] = Field(None, description="Current price")
    updated_at: Optional[str] = Field(
        None, description="Last match update timestamp (ISO 8601)"
    )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class KiwoomOrderRequest(BaseModel):
    """
    Order placement request body.

    Attributes:
        ticker: Stock ticker code
        side: Order side (BUY or SELL)
        quantity: Order quantity (must be positive)
        order_type: Price type (MARKET or LIMIT)
        price: Limit price (required for LIMIT orders, ignored for MARKET)
    """

    ticker: str = Field(..., description="Stock ticker code")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    quantity: int = Field(..., gt=0, description="Order quantity")
    order_type: Literal["MARKET", "LIMIT"] = Field(..., description="Price type")
    price: Optional[float] = Field(
        None, description="Limit price (required for LIMIT orders)"
    )


class KiwoomOrder(BaseModel):
    """
    Order snapshot returned by the API.

    Attributes:
        order_id: Unique order identifier
        ticker: Stock ticker code
        side: Order side (BUY or SELL)
        quantity: Ordered quantity
        filled_quantity: Filled quantity so far
        unfilled_quantity: Remaining unfilled quantity
        order_type: Price type (MARKET or LIMIT)
        price: Limit price (None for market orders)
        filled_price: Average fill price (None if not yet filled)
        status: Current order lifecycle status
        created_at: Order creation timestamp (ISO 8601)
        updated_at: Last update timestamp (ISO 8601)
    """

    order_id: str = Field(..., description="Unique order identifier")
    ticker: str = Field(..., description="Stock ticker code")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    quantity: int = Field(..., description="Ordered quantity")
    filled_quantity: int = Field(0, description="Filled quantity so far")
    unfilled_quantity: int = Field(0, description="Remaining unfilled quantity")
    order_type: Literal["MARKET", "LIMIT"] = Field(..., description="Price type")
    price: Optional[float] = Field(
        None, description="Limit price (None for market orders)"
    )
    filled_price: Optional[float] = Field(
        None, description="Average fill price (None if not yet filled)"
    )
    status: Literal[
        "RECEIVED", "CONFIRMED", "FILLED", "CANCELED", "REJECTED", "PARTIAL"
    ] = Field(..., description="Current order lifecycle status")
    created_at: str = Field(..., description="Order creation timestamp (ISO 8601)")
    updated_at: Optional[str] = Field(
        None, description="Last update timestamp (ISO 8601)"
    )


# ---------------------------------------------------------------------------
# Composite responses
# ---------------------------------------------------------------------------


class KiwoomOrdersResponse(BaseModel):
    """Wrapper for order list endpoint."""

    orders: List[KiwoomOrder] = Field(
        default_factory=list, description="List of orders"
    )


class KiwoomConditionsResponse(BaseModel):
    """Wrapper for conditions list endpoint."""

    conditions: List[KiwoomCondition] = Field(
        default_factory=list, description="List of conditions"
    )


class KiwoomConditionMatchesResponse(BaseModel):
    """Wrapper for condition matches endpoint."""

    matches: List[KiwoomConditionMatch] = Field(
        default_factory=list, description="List of matching stocks"
    )


# ---------------------------------------------------------------------------
# Inline request bodies
# ---------------------------------------------------------------------------


class KiwoomAmendRequest(BaseModel):
    """
    Order amendment request body.

    Attributes:
        quantity: New order quantity (optional)
        price: New limit price (optional)
    """

    quantity: Optional[int] = Field(None, gt=0, description="New order quantity")
    price: Optional[float] = Field(None, description="New limit price")


class KiwoomConditionStartRequest(BaseModel):
    """
    Condition monitoring start request body.

    Attributes:
        condition_index: Condition index
        condition_name: Condition name
    """

    condition_index: int = Field(..., ge=0, description="Condition index")
    condition_name: str = Field(..., min_length=1, description="Condition name")


class KiwoomConditionStopRequest(BaseModel):
    """
    Condition monitoring stop request body.

    Attributes:
        condition_index: Condition index
        condition_name: Condition name
    """

    condition_index: int = Field(..., ge=0, description="Condition index")
    condition_name: str = Field(..., min_length=1, description="Condition name")


class KiwoomKillSwitchResponse(BaseModel):
    """
    Kill switch activation response.

    Attributes:
        activated: Whether the kill switch was activated
        cancelled_orders: Number of orders cancelled
    """

    activated: bool = Field(..., description="Whether the kill switch was activated")
    cancelled_orders: int = Field(0, description="Number of orders cancelled")
