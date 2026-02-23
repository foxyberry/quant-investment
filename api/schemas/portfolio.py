"""
Portfolio schemas for API request/response validation.

Defines Pydantic models for portfolio management operations.
"""

from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    """
    Schema for creating a new holding.

    Attributes:
        ticker: Stock ticker symbol (e.g., AAPL, 005930.KS)
        quantity: Number of shares
        avg_price: Average purchase price per share
        name: Stock name (optional, defaults to ticker)
        currency: Currency code (default: KRW)
        note: Optional note for the holding
    """

    ticker: str = Field(..., description="Stock ticker symbol", examples=["AAPL", "005930.KS"])
    quantity: int = Field(..., gt=0, description="Number of shares")
    avg_price: float = Field(..., gt=0, description="Average purchase price per share")
    name: Optional[str] = Field(default=None, description="Stock name")
    currency: str = Field(default="KRW", description="Currency code")
    note: Optional[str] = Field(default=None, description="Optional note")


class HoldingUpdate(BaseModel):
    """
    Schema for updating an existing holding.

    All fields are optional - only provided fields will be updated.

    Attributes:
        quantity: New number of shares
        avg_price: New average price
        name: New stock name
        note: New note
    """

    quantity: Optional[int] = Field(default=None, gt=0, description="New number of shares")
    avg_price: Optional[float] = Field(default=None, gt=0, description="New average price")
    name: Optional[str] = Field(default=None, description="New stock name")
    note: Optional[str] = Field(default=None, description="New note")


class HoldingResponse(BaseModel):
    """
    Schema for holding response with calculated fields.

    Attributes:
        ticker: Stock ticker symbol
        name: Stock name
        quantity: Number of shares
        avg_price: Average purchase price
        current_price: Current market price (None if unavailable)
        market_value: Current market value (quantity * current_price)
        pnl: Profit/Loss amount
        pnl_pct: Profit/Loss percentage
        currency: Currency code
        bought_at: Purchase date
        note: Optional note
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    name: Optional[str] = Field(default=None, description="Stock name")
    quantity: int = Field(..., description="Number of shares")
    avg_price: float = Field(..., description="Average purchase price")
    current_price: Optional[float] = Field(default=None, description="Current market price")
    market_value: Optional[float] = Field(default=None, description="Current market value")
    cost_basis: float = Field(..., description="Total cost basis (quantity * avg_price)")
    pnl: Optional[float] = Field(default=None, description="Profit/Loss amount")
    pnl_pct: Optional[float] = Field(default=None, description="Profit/Loss percentage")
    currency: str = Field(default="KRW", description="Currency code")
    bought_at: Optional[date] = Field(default=None, description="Purchase date")
    note: Optional[str] = Field(default=None, description="Optional note")


class PortfolioSummary(BaseModel):
    """
    Schema for portfolio summary with aggregated P&L.

    Attributes:
        total_investment: Total amount invested (cost basis)
        total_market_value: Current total market value
        total_pnl: Total profit/loss amount
        total_pnl_pct: Total profit/loss percentage
        holdings_count: Number of holdings
        currency: Primary currency
        last_updated: Last update timestamp
    """

    total_investment: float = Field(..., description="Total cost basis")
    total_market_value: float = Field(..., description="Current market value")
    total_pnl: float = Field(..., description="Total profit/loss amount")
    total_pnl_pct: float = Field(..., description="Total profit/loss percentage")
    holdings_count: int = Field(..., description="Number of holdings")
    currency: str = Field(default="KRW", description="Primary currency")
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )


class CsvRowError(BaseModel):
    """
    Schema for a CSV row validation error.

    Attributes:
        row: 1-based row number in the CSV
        ticker: Ticker value from the row (None if missing)
        reason: Description of the validation error
    """

    row: int = Field(..., description="1-based row number")
    ticker: Optional[str] = Field(default=None, description="Ticker from the row")
    reason: str = Field(..., description="Error description")


class CsvImportResponse(BaseModel):
    """
    Schema for CSV import result.

    Attributes:
        imported: Number of newly created holdings
        updated: Number of existing holdings updated
        skipped: Number of rows skipped due to errors
        errors: List of row-level validation errors
    """

    imported: int = Field(..., description="Newly created holdings count")
    updated: int = Field(..., description="Updated holdings count")
    skipped: int = Field(..., description="Skipped rows count")
    errors: List[CsvRowError] = Field(default_factory=list, description="Row errors")


class SellSignal(BaseModel):
    """
    Schema for sell signal information.

    Attributes:
        ticker: Stock ticker symbol
        name: Stock name
        signal_type: Type of signal (stop_loss, take_profit, technical)
        reason: Human-readable reason for the signal
        current_price: Current market price
        trigger_price: Price that triggered the signal (optional)
        avg_price: Average purchase price
        pnl_pct: Current profit/loss percentage
        currency: Holding currency code
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Stock name")
    signal_type: str = Field(
        ...,
        description="Type of signal",
        examples=["stop_loss", "take_profit", "technical"]
    )
    reason: str = Field(..., description="Reason for the signal")
    current_price: float = Field(..., description="Current market price")
    trigger_price: Optional[float] = Field(default=None, description="Trigger price")
    avg_price: float = Field(..., description="Average purchase price")
    pnl_pct: float = Field(..., description="Current profit/loss percentage")
    currency: str = Field(..., description="Holding currency code")


class PortfolioResponse(BaseModel):
    """
    Schema for full portfolio response (holdings + summary).

    Attributes:
        holdings: List of holdings with P&L
        summary: Portfolio summary
    """

    holdings: List[HoldingResponse] = Field(..., description="List of holdings")
    summary: PortfolioSummary = Field(..., description="Portfolio summary")


class SellSignalsResponse(BaseModel):
    """
    Schema for sell signals response.

    Attributes:
        signals: List of sell signals
        checked_at: Timestamp when signals were checked
    """

    signals: List[SellSignal] = Field(..., description="List of sell signals")
    checked_at: datetime = Field(
        default_factory=datetime.now,
        description="Check timestamp"
    )
