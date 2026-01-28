"""
Risk Rules
위험 규칙 구현

Usage:
    from portfolio.risk_module.rules import (
        MaxPositionRule, DailyLossLimitRule, SectorLimitRule,
        MinCashRule, MaxDailyTradesRule
    )
"""

from typing import Optional

from .base import RiskRule, RiskContext, RiskViolation, RiskLevel


class MaxPositionRule(RiskRule):
    """최대 포지션 비율 규칙"""

    def __init__(self, max_percent: float = 20, level: RiskLevel = RiskLevel.BLOCK):
        """
        Args:
            max_percent: 단일 종목 최대 비율 (%)
            level: 위반 시 처리 수준
        """
        self.max_percent = max_percent
        self.level = level

    @property
    def name(self) -> str:
        return "max_position"

    def validate(self, context: RiskContext) -> Optional[RiskViolation]:
        if context.side != "BUY":
            return None

        position_after = context.position_after_order
        position_pct = (position_after / context.portfolio_value * 100) if context.portfolio_value > 0 else 0

        if position_pct > self.max_percent:
            return RiskViolation(
                rule_name=self.name,
                level=self.level,
                message=f"Position limit exceeded: would be {position_pct:.1f}% (max {self.max_percent}%)",
                details={
                    "current_pct": context.current_position_value / context.portfolio_value * 100,
                    "after_pct": position_pct,
                    "max_pct": self.max_percent,
                }
            )
        return None


class DailyLossLimitRule(RiskRule):
    """일일 손실 한도 규칙"""

    def __init__(self, max_loss_percent: float = 3, level: RiskLevel = RiskLevel.BLOCK):
        """
        Args:
            max_loss_percent: 일일 최대 손실률 (%)
        """
        self.max_loss_percent = max_loss_percent
        self.level = level

    @property
    def name(self) -> str:
        return "daily_loss_limit"

    def validate(self, context: RiskContext) -> Optional[RiskViolation]:
        daily_loss_pct = abs(context.daily_pnl / context.portfolio_value * 100) if context.portfolio_value > 0 else 0

        if context.daily_pnl < 0 and daily_loss_pct >= self.max_loss_percent:
            return RiskViolation(
                rule_name=self.name,
                level=self.level,
                message=f"Daily loss limit reached: {daily_loss_pct:.1f}% (max {self.max_loss_percent}%)",
                details={
                    "daily_pnl": context.daily_pnl,
                    "daily_loss_pct": daily_loss_pct,
                    "max_loss_pct": self.max_loss_percent,
                }
            )
        return None


class SectorLimitRule(RiskRule):
    """섹터별 한도 규칙"""

    def __init__(self, max_per_sector: float = 30, level: RiskLevel = RiskLevel.WARNING):
        """
        Args:
            max_per_sector: 섹터당 최대 비율 (%)
        """
        self.max_per_sector = max_per_sector
        self.level = level

    @property
    def name(self) -> str:
        return "sector_limit"

    def validate(self, context: RiskContext) -> Optional[RiskViolation]:
        if context.side != "BUY" or not context.sector:
            return None

        current_sector_value = context.sector_positions.get(context.sector, 0)
        after_sector_value = current_sector_value + context.order_value
        sector_pct = (after_sector_value / context.portfolio_value * 100) if context.portfolio_value > 0 else 0

        if sector_pct > self.max_per_sector:
            return RiskViolation(
                rule_name=self.name,
                level=self.level,
                message=f"Sector limit exceeded: {context.sector} would be {sector_pct:.1f}% (max {self.max_per_sector}%)",
                details={
                    "sector": context.sector,
                    "current_pct": current_sector_value / context.portfolio_value * 100,
                    "after_pct": sector_pct,
                    "max_pct": self.max_per_sector,
                }
            )
        return None


class MinCashRule(RiskRule):
    """최소 현금 보유 규칙"""

    def __init__(self, min_cash_percent: float = 10, level: RiskLevel = RiskLevel.WARNING):
        """
        Args:
            min_cash_percent: 최소 현금 비율 (%)
        """
        self.min_cash_percent = min_cash_percent
        self.level = level

    @property
    def name(self) -> str:
        return "min_cash"

    def validate(self, context: RiskContext) -> Optional[RiskViolation]:
        if context.side != "BUY":
            return None

        cash_after = context.cash_balance - context.order_value
        cash_pct = (cash_after / context.portfolio_value * 100) if context.portfolio_value > 0 else 0

        if cash_pct < self.min_cash_percent:
            return RiskViolation(
                rule_name=self.name,
                level=self.level,
                message=f"Cash would drop below minimum: {cash_pct:.1f}% (min {self.min_cash_percent}%)",
                details={
                    "current_cash": context.cash_balance,
                    "cash_after": cash_after,
                    "cash_pct_after": cash_pct,
                    "min_cash_pct": self.min_cash_percent,
                }
            )
        return None


class MaxDailyTradesRule(RiskRule):
    """일일 최대 거래 횟수 규칙"""

    def __init__(self, max_trades: int = 10, level: RiskLevel = RiskLevel.WARNING):
        self.max_trades = max_trades
        self.level = level

    @property
    def name(self) -> str:
        return "max_daily_trades"

    def validate(self, context: RiskContext) -> Optional[RiskViolation]:
        if context.daily_trades >= self.max_trades:
            return RiskViolation(
                rule_name=self.name,
                level=self.level,
                message=f"Daily trade limit reached: {context.daily_trades} (max {self.max_trades})",
                details={
                    "daily_trades": context.daily_trades,
                    "max_trades": self.max_trades,
                }
            )
        return None
