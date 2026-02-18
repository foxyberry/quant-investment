"""
API Schemas module.

Export all Pydantic schemas for request/response validation.
"""

from api.schemas.analysis import (
    EnrichRequest,
    EnrichedStock,
    AnalysisRequest,
    AnalysisResult,
    ReportSummary,
    ReportDetail,
    ReportListResponse,
    EnrichedDataResponse,
    OHLCVDataPoint,
    TickerTechnicalIndicators,
    TickerFundamental,
    TickerAnalysisResponse,
    SearchResult,
)
from api.schemas.common import ApiResponse, ErrorResponse, HealthResponse
from api.schemas.market import (
    OHLCVItem,
    OHLCVResponse,
    QuoteResponse,
    TechnicalIndicators,
)
from api.schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioSummary,
    PortfolioResponse,
    SellSignal,
    SellSignalsResponse,
)
from api.schemas.screening import (
    ConditionResultItem,
    ScreeningResultItem,
    ScreeningRequest,
    ScreeningResponse,
    PresetInfo,
    UniverseInfo,
    SingleStockRequest,
)
from api.schemas.backtest import (
    StrategyParamInfo,
    StrategyInfo,
    StrategiesListResponse,
    BacktestRequest,
    BacktestMetrics,
    TradeRecord,
    EquityPoint,
    BacktestResponse,
    OptimizeRequest,
    OptimizeResponse,
)
from api.schemas.strategy import (
    StrategyNodeData,
    StrategyNode,
    StrategyEdge,
    StrategyGraph,
    StrategyExecuteRequest,
    StrategyExecuteResponse,
    StrategyResultItem,
    NodeIntermediateResult,
    ConditionInfo,
    ConditionParamInfo,
    ConditionsListResponse,
)

__all__ = [
    # Analysis
    "EnrichRequest",
    "EnrichedStock",
    "AnalysisRequest",
    "AnalysisResult",
    "ReportSummary",
    "ReportDetail",
    "ReportListResponse",
    "EnrichedDataResponse",
    "OHLCVDataPoint",
    "TickerTechnicalIndicators",
    "TickerFundamental",
    "TickerAnalysisResponse",
    "SearchResult",
    # Common
    "ApiResponse",
    "ErrorResponse",
    "HealthResponse",
    # Market
    "OHLCVItem",
    "OHLCVResponse",
    "QuoteResponse",
    "TechnicalIndicators",
    # Portfolio
    "HoldingCreate",
    "HoldingUpdate",
    "HoldingResponse",
    "PortfolioSummary",
    "PortfolioResponse",
    "SellSignal",
    "SellSignalsResponse",
    # Screening
    "ConditionResultItem",
    "ScreeningResultItem",
    "ScreeningRequest",
    "ScreeningResponse",
    "PresetInfo",
    "UniverseInfo",
    "SingleStockRequest",
    # Backtest
    "StrategyParamInfo",
    "StrategyInfo",
    "StrategiesListResponse",
    "BacktestRequest",
    "BacktestMetrics",
    "TradeRecord",
    "EquityPoint",
    "BacktestResponse",
    "OptimizeRequest",
    "OptimizeResponse",
    # Strategy
    "StrategyNodeData",
    "StrategyNode",
    "StrategyEdge",
    "StrategyGraph",
    "StrategyExecuteRequest",
    "StrategyExecuteResponse",
    "StrategyResultItem",
    "NodeIntermediateResult",
    "ConditionInfo",
    "ConditionParamInfo",
    "ConditionsListResponse",
]
