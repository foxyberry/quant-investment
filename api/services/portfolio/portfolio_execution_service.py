"""
Portfolio Execution Service.

Handles trade recording (sell, buy), trade history retrieval.
"""

import logging
from datetime import date
from typing import Dict, List, Optional

from api.database import SessionLocal
from api.models.portfolio import Holding, Trade
from api.schemas.portfolio import (
    SellRecordCreate,
    TradeResponse,
    TradeHistoryResponse,
)
from api.services.portfolio.portfolio_archive_service import PortfolioArchiveService

logger = logging.getLogger(__name__)


class PortfolioExecutionService(PortfolioArchiveService):
    """
    Extends PortfolioCoreService with trade execution operations.

    Responsible for recording sells and querying trade history.
    """

    def record_sell(self, data: SellRecordCreate) -> TradeResponse:
        """Record a manual sell and update the holding accordingly."""
        db = SessionLocal()
        try:
            holding = db.get(Holding, data.ticker)
            if not holding:
                raise ValueError(f"Holding not found: {data.ticker}")
            if data.quantity > holding.quantity:
                raise ValueError(
                    f"Sell quantity ({data.quantity}) exceeds holding ({holding.quantity})"
                )

            avg_price = holding.avg_price
            total_cost = data.fee + data.tax
            realized_pnl = (data.price - avg_price) * data.quantity - total_cost

            trade = Trade(
                ticker=data.ticker,
                name=holding.name,
                trade_type="SELL",
                quantity=data.quantity,
                price=data.price,
                fee=data.fee,
                tax=data.tax,
                realized_pnl=realized_pnl,
                avg_price_at_trade=avg_price,
                currency=holding.currency,
                note=data.note,
                traded_at=data.traded_at,
            )
            db.add(trade)

            remaining = holding.quantity - data.quantity
            if remaining == 0:
                db.delete(holding)
                logger.info(f"Sold all of {data.ticker} — holding removed")
            else:
                holding.quantity = remaining
                logger.info(
                    f"Partial sell {data.ticker}: {data.quantity} shares, "
                    f"{remaining} remaining"
                )

            db.commit()
            db.refresh(trade)

            return TradeResponse(
                id=trade.id,
                ticker=trade.ticker,
                name=trade.name,
                trade_type=trade.trade_type,
                quantity=trade.quantity,
                price=trade.price,
                fee=trade.fee or 0,
                tax=trade.tax or 0,
                realized_pnl=trade.realized_pnl,
                avg_price_at_trade=trade.avg_price_at_trade,
                currency=trade.currency,
                note=trade.note,
                traded_at=trade.traded_at,
                created_at=trade.created_at,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_trade_history(
        self, ticker: Optional[str] = None
    ) -> TradeHistoryResponse:
        """Get trade history, optionally filtered by ticker."""
        db = SessionLocal()
        try:
            query = db.query(Trade).order_by(Trade.traded_at.desc(), Trade.id.desc())
            if ticker:
                query = query.filter(Trade.ticker == ticker)
            rows = query.all()

            # Fallback: fill name from Holding for legacy rows missing name
            nameless = [r.ticker for r in rows if not r.name]
            name_map: Dict[str, str] = {}
            if nameless:
                holdings = db.query(Holding.ticker, Holding.name).filter(
                    Holding.ticker.in_(list(set(nameless)))
                ).all()
                name_map = {h.ticker: h.name for h in holdings if h.name}
        finally:
            db.close()

        trades = [
            TradeResponse(
                id=r.id,
                ticker=r.ticker,
                name=r.name or name_map.get(r.ticker),
                trade_type=r.trade_type,
                quantity=r.quantity,
                price=r.price,
                fee=r.fee or 0,
                tax=r.tax or 0,
                realized_pnl=r.realized_pnl,
                avg_price_at_trade=r.avg_price_at_trade,
                currency=r.currency,
                note=r.note,
                traded_at=r.traded_at,
                created_at=r.created_at,
            )
            for r in rows
        ]
        total_pnl = sum(t.realized_pnl or 0 for t in trades)
        return TradeHistoryResponse(
            trades=trades,
            total_realized_pnl=total_pnl,
            trade_count=len(trades),
        )
