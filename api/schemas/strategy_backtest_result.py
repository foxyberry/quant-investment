"""
Strategy Backtest Result Schemas.

Pydantic models for persisted backtest results.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from api.schemas.backtest import EquityPoint, TradeRecord


class StrategyBacktestResultResponse(BaseModel):
    """Persisted backtest result for a strategy."""

    id: str
    strategy_id: str
    ticker: str
    period: str
    initial_cash: float

    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    cagr: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_return: Optional[float] = None
    profit_factor: Optional[float] = None
    total_trades: int = 0
    avg_trade_return: Optional[float] = None

    equity_curve: List[EquityPoint] = Field(default_factory=list)
    trades: List[TradeRecord] = Field(default_factory=list)
    compiled_conditions: List[str] = Field(default_factory=list)
    skipped_conditions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    created_at: str


class StrategyBacktestResultsListResponse(BaseModel):
    """Response listing backtest results for a strategy."""

    strategy_id: str
    results: List[StrategyBacktestResultResponse]
    total_count: int
