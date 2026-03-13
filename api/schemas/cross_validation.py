"""
Cross-Validation Schemas.

Pydantic models for the indicator cross-validation API.
Compares our indicator calculations vs TradingView-compatible reference values.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class IndicatorComparison(BaseModel):
    """Comparison of a single indicator value between our calc and reference."""

    name: str = Field(description="Indicator name (e.g., 'RSI', 'MACD Line')")
    our_value: Optional[float] = Field(None, description="Our calculated value")
    reference_value: Optional[float] = Field(None, description="TradingView-compatible reference value")
    difference: Optional[float] = Field(None, description="Absolute difference (our - ref)")
    pct_difference: Optional[float] = Field(
        None, description="Percentage difference relative to reference, or None if ref is 0/None"
    )
    match: bool = Field(description="Whether values are within acceptable tolerance")
    note: Optional[str] = Field(None, description="Explanation of any known divergence")


class CrossValidationResponse(BaseModel):
    """Response from the cross-validation endpoint."""

    ticker: str
    period: str = Field(description="Data period used (e.g., '1y')")
    data_points: int = Field(description="Number of OHLCV data points used")
    comparisons: List[IndicatorComparison] = Field(default_factory=list)
    overall_pass: bool = Field(description="True if all indicators match within tolerance")
    known_divergences: List[str] = Field(
        default_factory=list,
        description="List of known methodology differences",
    )
