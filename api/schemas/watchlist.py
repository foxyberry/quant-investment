"""
Watchlist schemas for API request/response validation.

Defines Pydantic models for watchlist management and buy rule operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

BUY_RULE_TYPES = {"target_price", "rsi_oversold"}


def _validate_buy_rule_params(rule_type: str, params: Dict[str, Any]) -> None:
    """Validate params dict for a given buy rule type."""
    if rule_type == "target_price":
        price = params.get("price")
        if isinstance(price, bool) or price is None or not isinstance(price, (int, float)):
            raise ValueError("target_price rule requires numeric 'price' param")
        if price <= 0:
            raise ValueError("target_price 'price' must be positive")
    elif rule_type == "rsi_oversold":
        rsi = params.get("rsi")
        if isinstance(rsi, bool) or rsi is None or not isinstance(rsi, (int, float)):
            raise ValueError("rsi_oversold rule requires numeric 'rsi' param")
        if not (1 <= rsi <= 100):
            raise ValueError("rsi_oversold 'rsi' must be between 1 and 100")
    else:
        raise ValueError(f"Unknown rule_type: {rule_type}. Allowed: {BUY_RULE_TYPES}")


# ── WatchlistItem schemas ─────────────────────────────────────────


class WatchlistItemCreate(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol", examples=["AAPL", "005930.KS"])
    name: Optional[str] = Field(default=None, description="Stock name")
    target_price: Optional[float] = Field(default=None, gt=0, description="Target buy price")
    note: Optional[str] = Field(default=None, description="Optional note")
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorisation")


class WatchlistItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="Stock name")
    target_price: Optional[float] = Field(default=None, description="Target buy price")
    note: Optional[str] = Field(default=None, description="Optional note")
    tags: Optional[List[str]] = Field(default=None, description="Tags")

    @field_validator("target_price")
    @classmethod
    def target_price_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("target_price must be positive")
        return v


class WatchlistItemResponse(BaseModel):
    id: int
    ticker: str
    name: Optional[str] = None
    target_price: Optional[float] = None
    current_price: Optional[float] = None
    change_pct: Optional[float] = None
    currency: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None
    buy_rules_count: int = 0
    added_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── BuyRule schemas ────────────────────────────────────────────────


class BuyRuleCreate(BaseModel):
    rule_type: str = Field(..., description="Rule type", examples=["target_price", "rsi_oversold"])
    params: Dict[str, Any] = Field(..., description="Rule parameters")
    is_active: bool = Field(default=True, description="Whether the rule is active")

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if v not in BUY_RULE_TYPES:
            raise ValueError(f"Invalid rule_type: {v}. Allowed: {BUY_RULE_TYPES}")
        return v


class BuyRuleUpdate(BaseModel):
    params: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class BuyRuleResponse(BaseModel):
    id: int
    watchlist_item_id: int
    rule_type: str
    params: Dict[str, Any]
    state_json: Optional[Dict[str, Any]] = None
    is_active: bool
    triggered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Evaluation schemas ─────────────────────────────────────────────


class BuySignal(BaseModel):
    """A triggered buy signal for a watchlist item."""
    ticker: str
    name: Optional[str] = None
    signal_type: str = Field(..., examples=["target_price", "rsi_oversold"])
    reason: str
    current_price: Optional[float] = None
    target_price: Optional[float] = None
    currency: Optional[str] = None
    rule_id: Optional[int] = None


class BuySignalsResponse(BaseModel):
    signals: List[BuySignal] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.now)
