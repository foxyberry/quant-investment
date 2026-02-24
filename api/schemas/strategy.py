"""
Strategy Builder Schemas.

Pydantic models for the visual strategy builder graph serialization and execution.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

from api.schemas.screening import normalize_universe_values


class StrategyNodeData(BaseModel):
    """Data payload for a strategy graph node."""

    node_type: str = Field(
        ...,
        description="Type of node: 'universe', 'sector', 'condition', 'logic', 'output'",
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
    universes: List[str] = Field(
        default_factory=list,
        description="Normalized multi-market values for universe node",
    )
    sector: Optional[str] = Field(
        None, description="Sector name for sector node filtering (e.g., '전기전자')"
    )
    child_node_ids: Optional[List[str]] = Field(
        None, description="Child node IDs for group/logic nodes"
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_universe_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("node_type") != "universe":
            return data
        explicit = data.get("universes")
        primary = data.get("universe")
        normalized = normalize_universe_values(explicit if explicit is not None else primary)
        if not normalized:
            return data
        data["universes"] = normalized
        data["universe"] = normalized[0]
        return data


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
    universe_overrides: List[str] = Field(
        default_factory=list,
        description="Normalized multi-market universe overrides",
    )
    portfolio_construction: Optional["PortfolioConstructionConfig"] = Field(
        default=None,
        description="Optional post-screening portfolio construction configuration",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_override_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        explicit = data.get("universe_overrides")
        primary = data.get("universe_override")
        normalized = normalize_universe_values(explicit if explicit is not None else primary)
        data["universe_overrides"] = normalized
        data["universe_override"] = normalized[0] if normalized else None
        return data

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "graph": {
                        "nodes": [
                            {
                                "id": "u1",
                                "data": {"node_type": "universe", "universe": "KOSPI"},
                            },
                            {
                                "id": "c1",
                                "data": {
                                    "node_type": "condition",
                                    "condition_type": "min_price",
                                    "params": {"min_price": 5000},
                                },
                            },
                            {"id": "o1", "data": {"node_type": "output"}},
                        ],
                        "edges": [
                            {"id": "e1", "source": "u1", "target": "c1"},
                            {"id": "e2", "source": "c1", "target": "o1"},
                        ],
                    },
                    "universe_override": "KOSPI",
                    "universe_overrides": ["KOSPI"],
                },
                {
                    "graph": {
                        "nodes": [
                            {
                                "id": "u1",
                                "data": {"node_type": "universe", "universe": "KOSPI"},
                            },
                            {
                                "id": "c1",
                                "data": {
                                    "node_type": "condition",
                                    "condition_type": "min_price",
                                    "params": {"min_price": 5000},
                                },
                            },
                            {"id": "o1", "data": {"node_type": "output"}},
                        ],
                        "edges": [
                            {"id": "e1", "source": "u1", "target": "c1"},
                            {"id": "e2", "source": "c1", "target": "o1"},
                        ],
                    },
                    "universe_override": "KOSPI",
                    "universe_overrides": ["KOSPI", "KOSDAQ"],
                },
            ]
        }
    }


class StrategyResultItem(BaseModel):
    """A single stock result from strategy execution."""

    ticker: str
    name: str
    current_price: Optional[float] = None
    per: Optional[float] = None
    pbr: Optional[float] = None
    dividend_yield: Optional[float] = None
    matched: bool
    conditions: List[Dict[str, Any]] = Field(default_factory=list)


class NodeIntermediateResult(BaseModel):
    """Intermediate results for a specific graph node."""

    node_id: str
    node_type: str  # 'universe' | 'condition' | 'logic' | 'output'
    label: str
    stock_count: int
    stocks: List[StrategyResultItem] = Field(default_factory=list)


class StrategyExecuteResponse(BaseModel):
    """Response from strategy execution."""

    results: List[StrategyResultItem]
    total_count: int
    matched_count: int
    universe: str
    universes: List[str] = Field(default_factory=list)
    conditions_used: List[str] = Field(default_factory=list)
    node_results: Dict[str, NodeIntermediateResult] = Field(default_factory=dict)
    weighted_portfolio: List["WeightedPortfolioItem"] = Field(default_factory=list)
    portfolio_construction_result: Optional["PortfolioConstructionResult"] = None


class PortfolioConstructionConfig(BaseModel):
    """Optional portfolio construction settings after screening."""

    mode: Literal["inverse_vol", "risk_parity"] = Field(
        default="inverse_vol",
        description="Weight construction mode",
    )
    lookback_days: int = Field(
        default=60,
        ge=20,
        le=252,
        description="Lookback window used for return volatility/covariance estimation",
    )
    max_assets: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of matched assets to include in weight optimization",
    )
    target_volatility: Optional[float] = Field(
        default=None,
        gt=0,
        le=2.0,
        description="Optional annualized target volatility (e.g. 0.12 = 12%)",
    )


class WeightedPortfolioItem(BaseModel):
    """Single weighted allocation entry from strategy output."""

    ticker: str
    name: str
    weight: float = Field(ge=0.0, le=1.0)
    current_price: Optional[float] = None
    annualized_volatility: Optional[float] = None


class PortfolioConstructionResult(BaseModel):
    """Metadata from portfolio construction stage."""

    mode_requested: str
    mode_applied: str
    lookback_days: int
    assets_requested: int
    assets_used: int
    estimated_portfolio_volatility: Optional[float] = None
    target_volatility: Optional[float] = None
    suggested_gross_leverage: Optional[float] = None
    fallback_reason: Optional[str] = None


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
    recommended: bool = False
    order: int = 0


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


class StrategyProgressEvent(BaseModel):
    """SSE progress event during strategy execution."""

    processed_tickers: int = 0
    total_tickers: int = 0
    matched_count: int = 0
    progress_pct: float = 0.0
    status: Literal["running", "done", "error"] = Field(description="Event status")
    message: Optional[str] = None


class SectorInfo(BaseModel):
    """Information about a market sector."""

    name: str = Field(description="Sector name (e.g., '전기전자')")
    stock_count: int = Field(description="Number of stocks in this sector")


class SectorListResponse(BaseModel):
    """Response listing available sectors for a market."""

    market: str
    sectors: List[SectorInfo]
    total_sectors: int


StrategyExecuteRequest.model_rebuild()
StrategyExecuteResponse.model_rebuild()
