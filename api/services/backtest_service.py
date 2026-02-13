"""
Backtest Service.

Business logic for backtesting API endpoints.
Wraps the BacktestEngine to run backtests and optimizations,
and serializes results for JSON-safe API responses.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Type

import numpy as np
import pandas as pd
from backtesting import Strategy

from api.schemas.backtest import (
    BacktestMetrics,
    BacktestRequest,
    BacktestResponse,
    EquityPoint,
    OptimizeRequest,
    OptimizeResponse,
    StrategyInfo,
    StrategyParamInfo,
    TradeRecord,
)
from engine.backtesting_engine import BacktestEngine, BacktestResult
from engine.metrics import PerformanceMetrics, calculate_metrics
from engine.strategies import EmaCross, MaTouchStrategy, SmaCross

logger = logging.getLogger(__name__)


# Strategy class map
STRATEGY_MAP: Dict[str, Type[Strategy]] = {
    "sma": SmaCross,
    "ema": EmaCross,
    "ma_touch": MaTouchStrategy,
}

# Strategy metadata with descriptions and parameter schemas
STRATEGY_META: Dict[str, Dict[str, Any]] = {
    "sma": {
        "name": "SMA Crossover",
        "description": "Simple Moving Average crossover strategy. "
        "Buys on golden cross (short SMA > long SMA), "
        "sells on death cross (short SMA < long SMA).",
        "params": [
            {
                "name": "n1",
                "type": "int",
                "default": 10,
                "description": "Short-term SMA period",
            },
            {
                "name": "n2",
                "type": "int",
                "default": 20,
                "description": "Long-term SMA period",
            },
        ],
    },
    "ema": {
        "name": "EMA Crossover",
        "description": "Exponential Moving Average crossover strategy. "
        "Buys on golden cross (short EMA > long EMA), "
        "sells on death cross (short EMA < long EMA).",
        "params": [
            {
                "name": "n1",
                "type": "int",
                "default": 12,
                "description": "Short-term EMA period",
            },
            {
                "name": "n2",
                "type": "int",
                "default": 26,
                "description": "Long-term EMA period",
            },
        ],
    },
    "ma_touch": {
        "name": "MA Touch",
        "description": "Moving average touch strategy. "
        "Buys when price bounces near the MA from below. "
        "Sells at take-profit or stop-loss thresholds.",
        "params": [
            {
                "name": "ma_period",
                "type": "int",
                "default": 20,
                "description": "Moving average period",
            },
            {
                "name": "take_profit",
                "type": "float",
                "default": 0.05,
                "description": "Take profit ratio (e.g., 0.05 = 5%)",
            },
            {
                "name": "stop_loss",
                "type": "float",
                "default": 0.03,
                "description": "Stop loss ratio (e.g., 0.03 = 3%)",
            },
        ],
    },
}


def _sanitize_value(v: Any) -> Any:
    """
    Convert numpy/pandas types to native Python types for JSON serialization.

    Handles np.float64, np.int64, np.bool_, pd.Timestamp, NaN, and Inf values.
    """
    if v is None:
        return None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(item) for item in v]
    return v


def _metrics_to_schema(perf: PerformanceMetrics) -> BacktestMetrics:
    """Convert PerformanceMetrics dataclass to BacktestMetrics Pydantic model."""
    d = perf.to_dict()
    sanitized = _sanitize_value(d)
    return BacktestMetrics(**sanitized)


def _extract_trades(result: BacktestResult) -> List[TradeRecord]:
    """Extract trade records from BacktestResult, converting to JSON-safe types."""
    trades_df = result.trades
    if trades_df is None or trades_df.empty:
        return []

    records = []
    for _, row in trades_df.iterrows():
        # Backtesting.py trade columns: EntryBar, ExitBar, EntryPrice, ExitPrice,
        # PnL, ReturnPct, EntryTime, ExitTime, Size, ...
        entry_date = _sanitize_value(row.get("EntryTime"))
        exit_date = _sanitize_value(row.get("ExitTime"))
        entry_price = _sanitize_value(row.get("EntryPrice"))
        exit_price = _sanitize_value(row.get("ExitPrice"))
        pnl = _sanitize_value(row.get("PnL"))
        return_pct = _sanitize_value(row.get("ReturnPct"))
        size = _sanitize_value(row.get("Size"))

        records.append(
            TradeRecord(
                entry_date=entry_date,
                exit_date=exit_date,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=pnl,
                return_pct=return_pct,
                size=size,
            )
        )
    return records


def _extract_equity_curve(result: BacktestResult) -> List[EquityPoint]:
    """Extract equity curve points from BacktestResult."""
    eq_df = result.equity_curve
    if eq_df is None or eq_df.empty:
        return []

    if "Equity" not in eq_df.columns:
        return []

    points = []
    for idx, row in eq_df.iterrows():
        date_str = _sanitize_value(idx)
        if date_str is None:
            # Fallback for non-Timestamp index
            date_str = str(idx)
        equity = _sanitize_value(row["Equity"])
        if equity is not None:
            points.append(EquityPoint(date=date_str, equity=equity))
    return points


def get_strategies() -> List[StrategyInfo]:
    """Return list of available backtesting strategies with their parameter schemas."""
    strategies = []
    for key, meta in STRATEGY_META.items():
        params = [StrategyParamInfo(**p) for p in meta["params"]]
        strategies.append(
            StrategyInfo(
                key=key,
                name=meta["name"],
                description=meta["description"],
                params=params,
            )
        )
    return strategies


def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """
    Run a backtest with the given parameters.

    Args:
        request: BacktestRequest with ticker, strategy, period, etc.

    Returns:
        BacktestResponse with metrics, trades, and equity curve.

    Raises:
        ValueError: If strategy key is unknown or ticker is invalid.
    """
    strategy_cls = STRATEGY_MAP.get(request.strategy)
    if strategy_cls is None:
        available = ", ".join(sorted(STRATEGY_MAP.keys()))
        raise ValueError(
            f"Unknown strategy: '{request.strategy}'. Available strategies: {available}"
        )

    engine = BacktestEngine(commission=request.commission)

    # Determine start/end vs period
    start = request.start
    end = request.end
    period = request.period

    # Run the backtest
    result = engine.run(
        strategy=strategy_cls,
        ticker=request.ticker,
        period=period,
        start=start,
        end=end,
        cash=request.cash,
        **request.strategy_params,
    )

    # Calculate detailed metrics
    perf = calculate_metrics(result)
    metrics = _metrics_to_schema(perf)

    # Extract trades and equity curve
    trades = _extract_trades(result)
    equity_curve = _extract_equity_curve(result)

    return BacktestResponse(
        ticker=request.ticker,
        strategy=request.strategy,
        period=period,
        cash=request.cash,
        metrics=metrics,
        trades=trades,
        equity_curve=equity_curve,
    )


def optimize_backtest(request: OptimizeRequest) -> OptimizeResponse:
    """
    Run parameter optimization for a strategy.

    Args:
        request: OptimizeRequest with ticker, strategy, param_ranges, etc.

    Returns:
        OptimizeResponse with optimal parameters and metrics.

    Raises:
        ValueError: If strategy key is unknown or param_ranges are invalid.
    """
    strategy_cls = STRATEGY_MAP.get(request.strategy)
    if strategy_cls is None:
        available = ", ".join(sorted(STRATEGY_MAP.keys()))
        raise ValueError(
            f"Unknown strategy: '{request.strategy}'. Available strategies: {available}"
        )

    if not request.param_ranges:
        raise ValueError("param_ranges must not be empty")

    engine = BacktestEngine(commission=request.commission)

    # Convert param_ranges lists to range-like iterables for optimize()
    param_ranges_kwargs = {}
    for param_name, values in request.param_ranges.items():
        if not isinstance(values, list) or len(values) == 0:
            raise ValueError(
                f"param_ranges['{param_name}'] must be a non-empty list of values"
            )
        param_ranges_kwargs[param_name] = values

    result = engine.optimize(
        strategy=strategy_cls,
        ticker=request.ticker,
        period=request.period,
        cash=request.cash,
        maximize=request.maximize,
        **param_ranges_kwargs,
    )

    # Extract optimal parameters from stats
    # Backtesting.py stores the optimized strategy class in stats._strategy
    optimal_params: Dict[str, Any] = {}
    if hasattr(result.stats, "_strategy"):
        opt_strategy = result.stats._strategy
        for param_name in request.param_ranges:
            if hasattr(opt_strategy, param_name):
                optimal_params[param_name] = _sanitize_value(
                    getattr(opt_strategy, param_name)
                )

    # Calculate metrics for the best result
    perf = calculate_metrics(result)
    metrics = _metrics_to_schema(perf)

    # Extract trades and equity curve
    trades = _extract_trades(result)
    equity_curve = _extract_equity_curve(result)

    return OptimizeResponse(
        ticker=request.ticker,
        strategy=request.strategy,
        maximize=request.maximize,
        optimal_params=optimal_params,
        best_metrics=metrics,
        trades=trades,
        equity_curve=equity_curve,
    )
