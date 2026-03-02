"""
Portfolio schemas for API request/response validation.

Defines Pydantic models for portfolio management operations.
"""

import math
from datetime import datetime, date
from typing import List, Optional, Self

from pydantic import BaseModel, Field, model_validator


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
        sector: Stock sector classification (None if unavailable)
        bought_at: Purchase date
        note: Optional note
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    name: Optional[str] = Field(default=None, description="Stock name")
    quantity: int = Field(..., description="Number of shares")
    avg_price: float = Field(..., description="Average purchase price")
    current_price: Optional[float] = Field(default=None, description="Current market price")
    change_pct: Optional[float] = Field(default=None, description="Daily price change percentage")
    market_value: Optional[float] = Field(default=None, description="Current market value")
    cost_basis: float = Field(..., description="Total cost basis (quantity * avg_price)")
    pnl: Optional[float] = Field(default=None, description="Profit/Loss amount")
    pnl_pct: Optional[float] = Field(default=None, description="Profit/Loss percentage")
    currency: str = Field(default="KRW", description="Currency code")
    sector: Optional[str] = Field(default=None, description="Stock sector classification")
    industry: Optional[str] = Field(default=None, description="Industry classification")
    country: Optional[str] = Field(default=None, description="Country of origin")
    exchange: Optional[str] = Field(default=None, description="Stock exchange")
    bought_at: Optional[date] = Field(default=None, description="Purchase date")
    note: Optional[str] = Field(default=None, description="Optional note")

    @model_validator(mode="after")
    def _sanitize_nan(self) -> "Self":
        """Replace NaN/Inf with None (optional) or 0.0 (required) to prevent JSON serialization errors."""
        # Optional float fields -> None on bad value
        for field_name in ("current_price", "change_pct", "market_value", "pnl", "pnl_pct"):
            val = getattr(self, field_name, None)
            if val is not None and (math.isnan(val) or math.isinf(val)):
                object.__setattr__(self, field_name, None)
        # Required float fields -> 0.0 on bad value
        for field_name in ("avg_price", "cost_basis"):
            val = getattr(self, field_name)
            if math.isnan(val) or math.isinf(val):
                object.__setattr__(self, field_name, 0.0)
        return self


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

    @model_validator(mode="after")
    def _sanitize_nan(self) -> "Self":
        """Replace NaN/Inf with 0.0 for required float fields to prevent JSON serialization errors."""
        for field_name in ("total_investment", "total_market_value", "total_pnl", "total_pnl_pct"):
            val = getattr(self, field_name)
            if math.isnan(val) or math.isinf(val):
                object.__setattr__(self, field_name, 0.0)
        return self


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


class AdditionalPurchaseRequest(BaseModel):
    """
    Schema for recording an additional purchase (averaging down/up).

    Attributes:
        quantity: Number of additional shares purchased
        price: Purchase price per share for this transaction
        fee: Commission or tax for this transaction
        traded_at: Date of the trade (defaults to today)
        note: Optional memo
    """

    quantity: int = Field(..., gt=0, description="Additional shares purchased")
    price: float = Field(..., gt=0, description="Purchase price per share")
    fee: float = Field(default=0, ge=0, description="Commission/tax")
    traded_at: Optional[date] = Field(default=None, description="Trade date (YYYY-MM-DD)")
    note: Optional[str] = Field(default=None, description="Optional memo")


class SellRecordCreate(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    quantity: int = Field(..., gt=0, description="Number of shares sold")
    price: float = Field(..., gt=0, description="Sell price per share")
    fee: float = Field(default=0, ge=0, description="Commission")
    tax: float = Field(default=0, ge=0, description="Tax")
    traded_at: date = Field(..., description="Date of the trade")
    note: Optional[str] = Field(default=None, description="Optional memo")


class TradeResponse(BaseModel):
    id: int
    ticker: str
    name: Optional[str] = None
    trade_type: str
    quantity: int
    price: float
    fee: float
    tax: float = Field(default=0)
    realized_pnl: Optional[float] = None
    avg_price_at_trade: Optional[float] = None
    currency: str
    note: Optional[str] = None
    traded_at: date
    created_at: datetime


class TradeHistoryResponse(BaseModel):
    trades: List[TradeResponse] = Field(default_factory=list)
    total_realized_pnl: float = Field(default=0)
    trade_count: int = Field(default=0)


# ---------------------------------------------------------------------------
# Sell Rules
# ---------------------------------------------------------------------------

SELL_RULE_TYPES = {"stop_loss", "take_profit", "trailing_stop", "holding_period"}


def _validate_sell_rule_params(rule_type: str, params: dict) -> dict:
    """Validate params dict against rule_type contract."""
    if rule_type not in SELL_RULE_TYPES:
        raise ValueError(f"Unknown rule_type: {rule_type}. Must be one of {SELL_RULE_TYPES}")

    if rule_type in ("stop_loss", "take_profit", "trailing_stop"):
        pct = params.get("pct")
        if isinstance(pct, bool) or pct is None or not isinstance(pct, (int, float)):
            raise ValueError(f"{rule_type} requires 'pct' (number, e.g. 10 for 10%)")
        if pct <= 0:
            raise ValueError(f"{rule_type} 'pct' must be positive")
        return {"pct": float(pct)}

    if rule_type == "holding_period":
        max_days = params.get("max_days")
        if isinstance(max_days, bool) or max_days is None or not isinstance(max_days, int):
            raise ValueError("holding_period requires 'max_days' (integer, e.g. 30)")
        if max_days <= 0:
            raise ValueError("holding_period 'max_days' must be positive")
        return {"max_days": int(max_days)}

    return params


class SellRuleCreate(BaseModel):
    """Create a sell rule for a specific holding."""

    rule_type: str = Field(..., description="Rule type: stop_loss, take_profit, trailing_stop, holding_period")
    params: dict = Field(..., description="Rule parameters (e.g. {pct: 10} or {max_days: 30})")
    is_active: bool = Field(default=True, description="Whether the rule is active")

    @model_validator(mode="after")
    def _validate_params(self) -> "Self":
        self.params = _validate_sell_rule_params(self.rule_type, self.params)
        return self


class SellRuleUpdate(BaseModel):
    """Update an existing sell rule."""

    params: Optional[dict] = Field(default=None, description="New rule parameters")
    is_active: Optional[bool] = Field(default=None, description="Active flag")


class SellRuleResponse(BaseModel):
    """Sell rule response."""

    id: int
    ticker: str
    rule_type: str
    params: dict
    state_json: Optional[dict] = None
    is_active: bool
    triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class SellRuleEvaluateResult(BaseModel):
    """Result of evaluating a single sell rule."""

    rule_id: int
    ticker: str
    rule_type: str
    triggered: bool
    reason: Optional[str] = None
    current_price: Optional[float] = None
    pnl_pct: Optional[float] = None


class SellRulesEvaluateResponse(BaseModel):
    """Response for bulk sell rule evaluation."""

    results: List[SellRuleEvaluateResult] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.now)


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
        examples=["stop_loss", "take_profit", "trailing_stop", "holding_period"]
    )
    reason: str = Field(..., description="Reason for the signal")
    current_price: float = Field(..., description="Current market price")
    trigger_price: Optional[float] = Field(default=None, description="Trigger price")
    avg_price: float = Field(..., description="Average purchase price")
    pnl_pct: float = Field(..., description="Current profit/loss percentage")
    currency: str = Field(..., description="Holding currency code")
    rule_id: Optional[int] = Field(default=None, description="Sell rule ID (None for global threshold)")

    @model_validator(mode="after")
    def _sanitize_nan(self) -> "Self":
        """Replace NaN/Inf to prevent JSON serialization errors."""
        for field_name in ("trigger_price",):
            val = getattr(self, field_name, None)
            if val is not None and (math.isnan(val) or math.isinf(val)):
                object.__setattr__(self, field_name, None)
        for field_name in ("current_price", "avg_price", "pnl_pct"):
            val = getattr(self, field_name)
            if math.isnan(val) or math.isinf(val):
                object.__setattr__(self, field_name, 0.0)
        return self


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
