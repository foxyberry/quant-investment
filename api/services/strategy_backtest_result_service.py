"""
Strategy Backtest Result Service.

Persists and retrieves backtest results for saved strategies.
"""

import logging
import uuid
from typing import List, Optional

from api.database import SessionLocal
from api.models.strategy_backtest_result import StrategyBacktestResult
from api.schemas.backtest import GraphBacktestResponse
from api.schemas.strategy_backtest_result import StrategyBacktestResultResponse

logger = logging.getLogger(__name__)


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
