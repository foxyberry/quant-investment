"""
Strategy Analytics Service.

Backtest result persistence/retrieval, strategy comparison, and leaderboard.
Absorbs the former strategy_comparison_service and strategy_backtest_result_service.
"""

import logging
import uuid
from typing import List, Optional

from sqlalchemy import func

from api.database import SessionLocal
from api.models.strategy import Strategy
from api.models.strategy_backtest_result import StrategyBacktestResult
from api.schemas.backtest import GraphBacktestResponse
from api.schemas.strategy_backtest_result import StrategyBacktestResultResponse
from api.schemas.strategy_comparison import (
    LeaderboardEntry,
    LeaderboardResponse,
    StrategyCompareResponse,
    StrategyMetricsSummary,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backtest result persistence
# ---------------------------------------------------------------------------

def _row_to_response(row: StrategyBacktestResult) -> StrategyBacktestResultResponse:
    return StrategyBacktestResultResponse(
        id=row.id,
        strategy_id=row.strategy_id,
        ticker=row.ticker,
        period=row.period,
        initial_cash=row.initial_cash,
        sharpe_ratio=row.sharpe_ratio,
        sortino_ratio=row.sortino_ratio,
        cagr=row.cagr,
        max_drawdown=row.max_drawdown,
        win_rate=row.win_rate,
        total_return=row.total_return,
        profit_factor=row.profit_factor,
        total_trades=row.total_trades,
        avg_trade_return=row.avg_trade_return,
        equity_curve=row.equity_curve or [],
        trades=row.trades or [],
        compiled_conditions=row.compiled_conditions or [],
        skipped_conditions=row.skipped_conditions or [],
        warnings=row.warnings or [],
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


def save_backtest_result(
    strategy_id: str,
    response: GraphBacktestResponse,
) -> StrategyBacktestResultResponse:
    """Persist a backtest result from a GraphBacktestResponse.

    Args:
        strategy_id: The strategy ID this result belongs to.
        response: The backtest response to persist.

    Returns:
        The persisted result.
    """
    result_id = uuid.uuid4().hex
    metrics = response.metrics

    row = StrategyBacktestResult(
        id=result_id,
        strategy_id=strategy_id,
        ticker=response.ticker,
        period=response.period,
        initial_cash=response.cash,
        sharpe_ratio=metrics.sharpe_ratio,
        sortino_ratio=metrics.sortino_ratio,
        cagr=metrics.cagr,
        max_drawdown=metrics.mdd,
        win_rate=metrics.win_rate,
        total_return=metrics.total_return,
        profit_factor=metrics.profit_factor,
        total_trades=metrics.num_trades,
        avg_trade_return=metrics.avg_trade_return,
        equity_curve=[p.model_dump() for p in response.equity_curve],
        trades=[t.model_dump() for t in response.trades],
        compiled_conditions=response.compiled_conditions,
        skipped_conditions=response.skipped_conditions,
        warnings=response.warnings,
    )

    db = SessionLocal()
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info("Saved backtest result %s for strategy %s", result_id, strategy_id)
        return _row_to_response(row)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_results(strategy_id: str) -> List[StrategyBacktestResultResponse]:
    """List all backtest results for a strategy, most recent first."""
    db = SessionLocal()
    try:
        rows = (
            db.query(StrategyBacktestResult)
            .filter(StrategyBacktestResult.strategy_id == strategy_id)
            .order_by(StrategyBacktestResult.created_at.desc())
            .all()
        )
        return [_row_to_response(r) for r in rows]
    finally:
        db.close()


def get_latest(strategy_id: str) -> Optional[StrategyBacktestResultResponse]:
    """Get the most recent backtest result for a strategy."""
    db = SessionLocal()
    try:
        row = (
            db.query(StrategyBacktestResult)
            .filter(StrategyBacktestResult.strategy_id == strategy_id)
            .order_by(StrategyBacktestResult.created_at.desc())
            .first()
        )
        if row is None:
            return None
        return _row_to_response(row)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Comparison and leaderboard
# ---------------------------------------------------------------------------

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
