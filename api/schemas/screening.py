"""
Screening API schemas.

Pydantic models for stock screening request/response validation.
"""

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class ConditionResultItem(BaseModel):
    """
    Individual condition evaluation result.

    Attributes:
        condition_name: Name of the condition
        matched: Whether the condition was satisfied
        details: Additional details about the evaluation
    """

    condition_name: str = Field(..., description="Name of the condition")
    matched: bool = Field(..., description="Whether the condition was satisfied")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional evaluation details"
    )


class ScreeningResultItem(BaseModel):
    """
    Screening result for a single stock.

    Attributes:
        ticker: Stock ticker symbol
        name: Stock name
        current_price: Current stock price
        matched: Whether all conditions were satisfied
        conditions: List of individual condition results
    """

    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Stock name")
    current_price: Optional[float] = Field(None, description="Current stock price")
    matched: bool = Field(..., description="Whether all conditions were satisfied")
    conditions: List[ConditionResultItem] = Field(
        default_factory=list,
        description="Individual condition results"
    )


class ScreeningRequest(BaseModel):
    """
    Screening request parameters.

    Attributes:
        preset: Preset name to use for screening
        universe: Stock universe to screen
        params: Optional parameters to override preset defaults
    """

    preset: str = Field(
        default="accumulation_basic",
        description="Preset name for screening conditions"
    )
    universe: str = Field(
        default="KOSPI",
        description="Stock universe (KOSPI, KOSDAQ, SP500, etc.)"
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameters to override preset defaults"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "preset": "accumulation_basic",
                    "universe": "KOSPI",
                    "params": {"min_price": 10000}
                }
            ]
        }
    }


class ScreeningResponse(BaseModel):
    """
    Screening response with results.

    Attributes:
        results: List of screening results for matched stocks
        total_count: Total number of stocks screened
        matched_count: Number of stocks that matched all conditions
    """

    results: List[ScreeningResultItem] = Field(
        default_factory=list,
        description="List of matched stocks"
    )
    total_count: int = Field(..., description="Total number of stocks screened")
    matched_count: int = Field(..., description="Number of matched stocks")


class PresetInfo(BaseModel):
    """
    Information about a screening preset.

    Attributes:
        name: Preset identifier
        description: Human-readable description
        conditions: List of condition names in the preset
    """

    name: str = Field(..., description="Preset identifier")
    description: str = Field(..., description="Human-readable description")
    conditions: List[str] = Field(
        default_factory=list,
        description="List of condition names"
    )


class UniverseInfo(BaseModel):
    """
    Information about a stock universe.

    Attributes:
        name: Universe identifier
        description: Human-readable description
        stock_count: Approximate number of stocks in the universe
    """

    name: str = Field(..., description="Universe identifier")
    description: str = Field(default="", description="Human-readable description")
    stock_count: int = Field(..., description="Approximate number of stocks")


class SingleStockRequest(BaseModel):
    """
    Request for checking a single stock.

    Attributes:
        preset: Preset name to use for screening
        params: Optional parameters to override preset defaults
    """

    preset: str = Field(
        default="accumulation_basic",
        description="Preset name for screening conditions"
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameters to override preset defaults"
    )
