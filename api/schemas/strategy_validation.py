"""
Strategy Validation Schemas.

Pydantic models for the strategy validation endpoint.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from api.schemas.cross_validation import IndicatorComparison


class StrategyValidateRequest(BaseModel):
    """Request to validate a strategy's indicators."""

    ticker: str = Field(
        default="AAPL",
        description="Ticker to use for cross-validation (e.g., 'AAPL', '005930.KS')",
    )
    period: str = Field(
        default="1y",
        description="Data period for cross-validation",
    )


class StrategyValidateResponse(BaseModel):
    """Response from strategy validation."""

    strategy_id: str
    indicators_tested: List[str] = Field(default_factory=list)
    comparisons: List[IndicatorComparison] = Field(default_factory=list)
    all_pass: bool = False
    status_before: str
    status_after: str
    message: str = ""
