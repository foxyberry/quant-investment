"""
Strategy Comparison & Leaderboard Schemas.

Pydantic models for comparing strategies and ranking them.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyCompareRequest(BaseModel):
    """Request to compare multiple strategies."""

    strategy_ids: List[str] = Field(
        ...,
        min_length=2,
        max_length=4,
        description="Strategy IDs to compare (2-4)",
    )


class StrategyMetricsSummary(BaseModel):
    """Summary metrics for a strategy (from its latest backtest)."""

    strategy_id: str
    strategy_name: str
    status: str = "draft"
    ticker: str = ""
    period: str = ""
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    cagr: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_return: Optional[float] = None
    profit_factor: Optional[float] = None
    total_trades: int = 0
    avg_trade_return: Optional[float] = None
    backtested_at: Optional[str] = None


class StrategyCompareResponse(BaseModel):
    """Response comparing multiple strategies."""

    strategies: List[StrategyMetricsSummary]
    best_sharpe: Optional[str] = Field(None, description="Strategy ID with best Sharpe ratio")
    best_cagr: Optional[str] = Field(None, description="Strategy ID with best CAGR")
    best_win_rate: Optional[str] = Field(None, description="Strategy ID with best win rate")
    lowest_drawdown: Optional[str] = Field(None, description="Strategy ID with lowest max drawdown")


class LeaderboardEntry(BaseModel):
    """A single entry on the strategy leaderboard."""

    rank: int
    strategy_id: str
    strategy_name: str
    status: str = "draft"
    sharpe_ratio: Optional[float] = None
    cagr: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_return: Optional[float] = None
    total_trades: int = 0
    backtested_at: Optional[str] = None


class LeaderboardResponse(BaseModel):
    """Response from the strategy leaderboard."""

    entries: List[LeaderboardEntry]
    sort_by: str
    order: str
    total_count: int
