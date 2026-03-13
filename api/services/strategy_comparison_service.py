"""
Strategy Comparison & Leaderboard Service.

Business logic for comparing strategies and building leaderboards.
"""

import logging
from typing import List, Optional

from sqlalchemy import func

from api.database import SessionLocal
from api.models.strategy import Strategy
from api.models.strategy_backtest_result import StrategyBacktestResult
from api.schemas.strategy_comparison import (
    LeaderboardEntry,
    LeaderboardResponse,
    StrategyCompareResponse,
    StrategyMetricsSummary,
)

logger = logging.getLogger(__name__)

_SORT_COLUMNS = {
    "sharpe_ratio": StrategyBacktestResult.sharpe_ratio,
    "cagr": StrategyBacktestResult.cagr,
    "max_drawdown": StrategyBacktestResult.max_drawdown,
    "win_rate": StrategyBacktestResult.win_rate,
    "total_return": StrategyBacktestResult.total_return,
}


def _best_by(
    strategies: List[StrategyMetricsSummary],
    attr: str,
    higher_is_better: bool = True,
) -> Optional[str]:
    """Return strategy_id with the best value for a metric."""
    candidates = [(s.strategy_id, getattr(s, attr)) for s in strategies if getattr(s, attr) is not None]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=higher_is_better)
    return candidates[0][0]


def compare_strategies(strategy_ids: List[str]) -> StrategyCompareResponse:
    """Compare 2-4 strategies using their latest backtest results.

    Args:
        strategy_ids: List of strategy IDs to compare.

    Returns:
        StrategyCompareResponse with metrics side by side.

    Raises:
        ValueError: If fewer than 2 IDs or any not found.
    """
    if len(strategy_ids) < 2:
        raise ValueError("At least 2 strategy IDs required for comparison")

    db = SessionLocal()
    try:
        summaries: List[StrategyMetricsSummary] = []

        for sid in strategy_ids:
            strategy = db.get(Strategy, sid)
            if strategy is None:
                raise ValueError(f"Strategy not found: {sid}")

            # Get latest backtest result
            latest = (
                db.query(StrategyBacktestResult)
                .filter(StrategyBacktestResult.strategy_id == sid)
                .order_by(StrategyBacktestResult.created_at.desc())
                .first()
            )

            summary = StrategyMetricsSummary(
                strategy_id=sid,
                strategy_name=strategy.name,
                status=strategy.status or "draft",
            )

            if latest:
                summary.ticker = latest.ticker
                summary.period = latest.period
                summary.sharpe_ratio = latest.sharpe_ratio
                summary.sortino_ratio = latest.sortino_ratio
                summary.cagr = latest.cagr
                summary.max_drawdown = latest.max_drawdown
                summary.win_rate = latest.win_rate
                summary.total_return = latest.total_return
                summary.profit_factor = latest.profit_factor
                summary.total_trades = latest.total_trades
                summary.avg_trade_return = latest.avg_trade_return
                summary.backtested_at = (
                    latest.created_at.isoformat() if latest.created_at else None
                )

            summaries.append(summary)

        return StrategyCompareResponse(
            strategies=summaries,
            best_sharpe=_best_by(summaries, "sharpe_ratio"),
            best_cagr=_best_by(summaries, "cagr"),
            best_win_rate=_best_by(summaries, "win_rate"),
            lowest_drawdown=_best_by(summaries, "max_drawdown", higher_is_better=False),
        )
    finally:
        db.close()


def get_leaderboard(
    sort_by: str = "sharpe_ratio",
    order: str = "desc",
    status: Optional[str] = None,
    limit: int = 20,
) -> LeaderboardResponse:
    """Get a ranked leaderboard of strategies based on backtest metrics.

    Only includes strategies that have at least one backtest result.

    Args:
        sort_by: Metric to sort by (sharpe_ratio, cagr, max_drawdown, win_rate, total_return).
        order: Sort order (asc, desc).
        status: Optional status filter (draft, backtested, validated, production, retired).
        limit: Maximum entries to return.

    Returns:
        LeaderboardResponse with ranked entries.
    """
    if sort_by not in _SORT_COLUMNS:
        raise ValueError(f"Invalid sort_by: '{sort_by}'. Valid: {', '.join(_SORT_COLUMNS)}")
    if order not in ("asc", "desc"):
        raise ValueError(f"Invalid order: '{order}'. Must be 'asc' or 'desc'")

    db = SessionLocal()
    try:
        # Subquery to get the latest result ID per strategy
        latest_subq = (
            db.query(
                StrategyBacktestResult.strategy_id,
                func.max(StrategyBacktestResult.created_at).label("max_created"),
            )
            .group_by(StrategyBacktestResult.strategy_id)
            .subquery()
        )

        query = (
            db.query(StrategyBacktestResult, Strategy)
            .join(
                latest_subq,
                (StrategyBacktestResult.strategy_id == latest_subq.c.strategy_id)
                & (StrategyBacktestResult.created_at == latest_subq.c.max_created),
            )
            .join(Strategy, Strategy.id == StrategyBacktestResult.strategy_id)
        )

        if status:
            query = query.filter(Strategy.status == status)

        sort_col = _SORT_COLUMNS[sort_by]
        if order == "desc":
            query = query.order_by(sort_col.desc().nullslast())
        else:
            query = query.order_by(sort_col.asc().nullsfirst())

        rows = query.limit(limit).all()

        entries = []
        for rank, (result, strategy) in enumerate(rows, start=1):
            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    strategy_id=strategy.id,
                    strategy_name=strategy.name,
                    status=strategy.status or "draft",
                    sharpe_ratio=result.sharpe_ratio,
                    cagr=result.cagr,
                    max_drawdown=result.max_drawdown,
                    win_rate=result.win_rate,
                    total_return=result.total_return,
                    total_trades=result.total_trades,
                    backtested_at=(
                        result.created_at.isoformat() if result.created_at else None
                    ),
                )
            )

        return LeaderboardResponse(
            entries=entries,
            sort_by=sort_by,
            order=order,
            total_count=len(entries),
        )
    finally:
        db.close()
