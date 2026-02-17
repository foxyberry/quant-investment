"""
Strategy Builder Schemas.

Pydantic models for the visual strategy builder graph serialization and execution.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StrategyNodeData(BaseModel):
    """Data payload for a strategy graph node."""

    node_type: str = Field(
        ...,
        description="Type of node: 'universe', 'condition', 'logic', 'output'",
    )
    condition_type: Optional[str] = Field(
        None, description="Condition class key (e.g., 'rsi_oversold')"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Condition parameters"
    )
    logic_operator: Optional[str] = Field(
        None, description="Logic operator: 'and', 'or', 'not'"
    )
    universe: Optional[str] = Field(
        None, description="Universe name (e.g., 'KOSPI', 'SP500')"
    )
    child_node_ids: Optional[List[str]] = Field(
        None, description="Child node IDs for group/logic nodes"
    )


class StrategyNode(BaseModel):
    """A node in the strategy graph."""

    id: str
    data: StrategyNodeData
    position: Optional[Dict[str, float]] = None


class StrategyEdge(BaseModel):
    """An edge connecting two nodes in the strategy graph."""

    id: str
    source: str
    target: str


class StrategyGraph(BaseModel):
    """Complete strategy graph with nodes and edges."""

    nodes: List[StrategyNode]
    edges: List[StrategyEdge]


class StrategyExecuteRequest(BaseModel):
    """Request to execute a visual strategy."""

    graph: StrategyGraph
    universe_override: Optional[str] = Field(
        None, description="Override universe from graph"
    )


class StrategyResultItem(BaseModel):
    """A single stock result from strategy execution."""

    ticker: str
    name: str
    current_price: Optional[float] = None
    matched: bool
    conditions: List[Dict[str, Any]] = Field(default_factory=list)


class StrategyExecuteResponse(BaseModel):
    """Response from strategy execution."""

    results: List[StrategyResultItem]
    total_count: int
    matched_count: int
    universe: str
    conditions_used: List[str] = Field(default_factory=list)


class ConditionParamInfo(BaseModel):
    """Schema for a single condition parameter."""

    name: str
    type: str = Field(description="'int', 'float', 'str', 'bool'")
    default: Any = None
    description: str = ""


class ConditionInfo(BaseModel):
    """Information about an available condition type."""

    key: str = Field(description="Condition key for CONDITION_CLASS_MAP")
    label: str
    description: str = ""
    category: str
    params: List[ConditionParamInfo] = Field(default_factory=list)


class ConditionsListResponse(BaseModel):
    """Response listing all available conditions."""

    conditions: List[ConditionInfo]
    categories: List[str]


class StrategySaveRequest(BaseModel):
    """Request to save a strategy graph."""

    name: str = Field(..., description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    graph: StrategyGraph


class StrategyUpdateRequest(BaseModel):
    """Request to partially update a saved strategy."""

    name: Optional[str] = Field(None, description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    graph: Optional[StrategyGraph] = None


class SavedStrategyResponse(BaseModel):
    """Saved strategy response model."""

    id: str
    name: str
    description: Optional[str] = None
    graph: StrategyGraph
    created_at: str
    updated_at: str


class SavedStrategiesListResponse(BaseModel):
    """Response listing saved strategies."""

    strategies: List[SavedStrategyResponse]
    total_count: int
