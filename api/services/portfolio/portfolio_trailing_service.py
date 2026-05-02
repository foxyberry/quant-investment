"""Helpers for portfolio-wide trailing stop state and evaluation."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from api.models.portfolio_trailing_state import PortfolioTrailingState
from portfolio.conditions import TradingContext, TrailingStopCondition


def update_and_check_trailing(
    db: Session,
    ticker: str,
    current_price: float,
    pct: float,
) -> tuple[Optional[float], Optional[str]]:
    """Update the ticker high-water mark and evaluate trailing stop."""
    state = db.get(PortfolioTrailingState, ticker)
    current_hwm = state.high_watermark if state else None

    if pct <= 0 or current_price <= 0:
        return current_hwm, None

    high_watermark = max(current_hwm or current_price, current_price)
    if state is None:
        state = PortfolioTrailingState(ticker=ticker, high_watermark=high_watermark)
        db.add(state)
    elif high_watermark != current_hwm:
        state.high_watermark = high_watermark

    condition = TrailingStopCondition(pct=pct)
    context = TradingContext(
        ticker=ticker,
        current_price=current_price,
        high_since_buy=high_watermark,
    )
    if condition.should_sell(context):
        return high_watermark, condition.get_reason()

    return high_watermark, None


def clear_trailing_state(db: Session, ticker: Optional[str] = None) -> None:
    """Delete trailing state rows for one ticker or for the whole portfolio."""
    query = db.query(PortfolioTrailingState)
    if ticker is not None:
        query = query.filter(PortfolioTrailingState.ticker == ticker)
    query.delete(synchronize_session=False)
