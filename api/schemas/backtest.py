"""
Backtest Schemas.

Pydantic models for backtesting API request/response validation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyParamInfo(BaseModel):
    """Schema for a single strategy parameter."""

    name: str = Field(description="Parameter name")
    type: str = Field(description="Parameter type: 'int', 'float'")
    default: Any = Field(description="Default value")
    description: str = Field(default="", description="Parameter description")


class StrategyInfo(BaseModel):
    """Information about an available backtesting strategy."""

    key: str = Field(description="Strategy key for STRATEGY_MAP")
    name: str = Field(description="Display name")
    description: str = Field(default="", description="Strategy description")
    params: List[StrategyParamInfo] = Field(
        default_factory=list, description="Available parameters"
    )


class StrategiesListResponse(BaseModel):
    """Response listing all available backtesting strategies."""

    strategies: List[StrategyInfo]


class BacktestRequest(BaseModel):
    """Request to run a backtest."""

    ticker: str = Field(description="Ticker symbol (e.g., 'AAPL', '005930.KS')")
    strategy: str = Field(description="Strategy key (e.g., 'sma', 'ema', 'ma_touch')")
    period: str = Field(default="1y", description="Data period (e.g., '1y', '6mo', '3mo')")
    start: Optional[str] = Field(
        default=None, description="Start date (YYYY-MM-DD). Overrides period if both start and end are set."
    )
    end: Optional[str] = Field(
        default=None, description="End date (YYYY-MM-DD). Overrides period if both start and end are set."
    )
    cash: float = Field(default=10_000_000, description="Initial cash amount")
    commission: float = Field(default=0.001, description="Commission rate (e.g., 0.001 = 0.1%)")
    strategy_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy-specific parameters (e.g., {'n1': 10, 'n2': 20})",
    )
    include_trades: bool = Field(
        default=True,
        description="Include trade records in response",
    )
    include_equity_curve: bool = Field(
        default=True,
        description="Include equity curve in response",
    )
    max_trades: int = Field(
        default=500,
        ge=1,
        le=5000,
        description="Maximum number of trades to return",
    )
    max_equity_points: int = Field(
        default=1000,
        ge=10,
        le=5000,
        description="Maximum number of equity curve points to return",
    )


class BacktestMetrics(BaseModel):
    """Performance metrics from a backtest run."""

    sharpe_ratio: Optional[float] = Field(description="Sharpe Ratio")
    sortino_ratio: Optional[float] = Field(description="Sortino Ratio")
    mdd: Optional[float] = Field(description="Maximum Drawdown (0~1)")
    win_rate: Optional[float] = Field(description="Win Rate (0~1)")
    profit_factor: Optional[float] = Field(description="Profit Factor (gross profit / gross loss)")
    cagr: Optional[float] = Field(description="Compound Annual Growth Rate")
    total_return: Optional[float] = Field(description="Total Return (0~1, e.g., 0.15 = 15%)")
    num_trades: int = Field(default=0, description="Number of trades")
    avg_trade_return: Optional[float] = Field(description="Average trade return")
    max_consecutive_wins: int = Field(default=0, description="Max consecutive winning trades")
    max_consecutive_losses: int = Field(default=0, description="Max consecutive losing trades")


class TradeRecord(BaseModel):
    """A single trade record from a backtest."""

    entry_date: Optional[str] = Field(description="Entry date (ISO format)")
    exit_date: Optional[str] = Field(description="Exit date (ISO format)")
    entry_price: Optional[float] = Field(description="Entry price")
    exit_price: Optional[float] = Field(description="Exit price")
    pnl: Optional[float] = Field(description="Profit/Loss amount")
    return_pct: Optional[float] = Field(description="Return percentage")
    size: Optional[float] = Field(description="Position size")


class EquityPoint(BaseModel):
    """A single point on the equity curve."""

    date: str = Field(description="Date (ISO format)")
    equity: float = Field(description="Equity value")


class BacktestResponse(BaseModel):
    """Response from a backtest run."""

    ticker: str
    strategy: str
    period: str
    cash: float
    metrics: BacktestMetrics
    trades: List[TradeRecord] = Field(default_factory=list)
    equity_curve: List[EquityPoint] = Field(default_factory=list)


class OptimizeRequest(BaseModel):
    """Request to optimize strategy parameters."""

    ticker: str = Field(description="Ticker symbol")
    strategy: str = Field(description="Strategy key")
    period: str = Field(default="1y", description="Data period")
    cash: float = Field(default=10_000_000, description="Initial cash amount")
    commission: float = Field(default=0.001, description="Commission rate")
    param_ranges: Dict[str, List[Any]] = Field(
        description="Parameter ranges for optimization. "
        "Each key is a param name, value is a list of values to try. "
        "Example: {'n1': [5, 10, 15, 20], 'n2': [20, 30, 40, 50]}"
    )
    maximize: str = Field(
        default="Sharpe Ratio",
        description="Metric to maximize (e.g., 'Sharpe Ratio', 'Return [%]', 'Win Rate [%]')",
    )
    include_trades: bool = Field(
        default=True,
        description="Include trade records in optimization response",
    )
    include_equity_curve: bool = Field(
        default=True,
        description="Include equity curve in optimization response",
    )
    max_trades: int = Field(
        default=500,
        ge=1,
        le=5000,
        description="Maximum number of trades to return",
    )
    max_equity_points: int = Field(
        default=1000,
        ge=10,
        le=5000,
        description="Maximum number of equity curve points to return",
    )


class OptimizeResponse(BaseModel):
    """Response from a parameter optimization run."""

    ticker: str
    strategy: str
    maximize: str
    optimal_params: Dict[str, Any] = Field(
        description="Best parameter combination found"
    )
    best_metrics: BacktestMetrics
    trades: List[TradeRecord] = Field(default_factory=list)
    equity_curve: List[EquityPoint] = Field(default_factory=list)
