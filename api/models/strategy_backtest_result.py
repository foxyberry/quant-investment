"""
SQLAlchemy model for strategy backtest results.

Stores backtest metrics, trades, and equity curve per strategy run.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from api.database import Base


class StrategyBacktestResult(Base):
    __tablename__ = "strategy_backtest_results"

    id = Column(String(32), primary_key=True)
    strategy_id = Column(String(32), nullable=False, index=True)
    ticker = Column(String(32), nullable=False)
    period = Column(String(16), nullable=False, default="1y")
    initial_cash = Column(Float, nullable=False, default=10_000_000)

    # Core metrics
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    cagr = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    total_return = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=False, default=0)
    avg_trade_return = Column(Float, nullable=True)

    # Detailed data (JSON)
    equity_curve = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    trades = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    compiled_conditions = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    skipped_conditions = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    warnings = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
