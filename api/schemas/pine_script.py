"""
Pine Script Export Schemas.

Pydantic models for Pine Script v5 export requests and responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PineScriptExportRequest(BaseModel):
    """Request to export a strategy graph as Pine Script v5."""

    graph: Dict[str, Any] = Field(
        ...,
        description="Strategy graph dict with nodes and edges.",
    )
    strategy_name: str = Field(
        default="QuantCanvas Strategy",
        description="Name for the Pine Script strategy.",
    )
    take_profit: Optional[float] = Field(
        default=None,
        description="Take-profit ratio (e.g. 0.05 = 5%).",
    )
    stop_loss: Optional[float] = Field(
        default=None,
        description="Stop-loss ratio (e.g. 0.03 = 3%).",
    )


class PineScriptExportResponse(BaseModel):
    """Response containing generated Pine Script v5 code."""

    pine_script: str = Field(
        ...,
        description="Generated Pine Script v5 code.",
    )
    strategy_name: str
    conditions_used: List[str] = Field(
        default_factory=list,
        description="Condition types that were exported.",
    )
    conditions_skipped: List[str] = Field(
        default_factory=list,
        description="Condition types that were skipped (unsupported).",
    )
