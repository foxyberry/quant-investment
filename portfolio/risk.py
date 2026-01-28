"""
Risk Management Rules Engine
위험 관리 규칙 엔진

Usage:
    from portfolio.risk import RiskManager, MaxPositionRule, DailyLossLimitRule

    risk_manager = RiskManager()
    risk_manager.add_rule(MaxPositionRule(max_percent=20))
    risk_manager.add_rule(DailyLossLimitRule(max_loss_percent=3))

    order = Order(ticker="005930.KS", side="BUY", quantity=100)
    result = risk_manager.validate(order, context)

    if not result.allowed:
        print(f"Blocked: {result.violations}")
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum


class RiskLevel(Enum):
    """위험 수준"""
    BLOCK = "BLOCK"  # 주문 차단
    WARNING = "WARNING"  # 경고만
    INFO = "INFO"  # 정보성


@dataclass
class RiskContext:
    """위험 평가 컨텍스트"""
    # Portfolio info
    portfolio_value: float
    cash_balance: float

    # Position info
    positions: Dict[str, Dict[str, Any]]  # {ticker: {quantity, avg_price, ...}}

    # Order info
    ticker: str
    side: str  # BUY or SELL
    quantity: int
    price: float

    # Daily stats
    daily_pnl: float = 0
    daily_trades: int = 0

    # Sector info (optional)
    sector: Optional[str] = None
    sector_positions: Dict[str, float] = field(default_factory=dict)

    @property
    def order_value(self) -> float:
        """주문 금액"""
        return self.quantity * self.price

    @property
    def current_position_value(self) -> float:
        """현재 해당 종목 포지션 가치"""
        pos = self.positions.get(self.ticker, {})
        qty = pos.get("quantity", 0)
        avg_price = pos.get("avg_price", self.price)
        return qty * avg_price

    @property
    def position_after_order(self) -> float:
        """주문 후 예상 포지션 가치"""
        current = self.current_position_value
        if self.side == "BUY":
            return current + self.order_value
        else:
            return max(0, current - self.order_value)


@dataclass
class RiskViolation:
    """위험 규칙 위반"""
    rule_name: str
    level: RiskLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class RiskValidationResult:
    """위험 검증 결과"""
    allowed: bool
    violations: List[RiskViolation] = field(default_factory=list)
    warnings: List[RiskViolation] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [v.to_dict() for v in self.warnings],
            "timestamp": self.timestamp.isoformat(),
        }


class RiskRule(ABC):
    """위험 규칙 기본 클래스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """규칙 이름"""
        pass

    @abstractmethod
    def validate(self, context: RiskContext) -> Optional[RiskViolation]:
        """
        규칙 검증

        Returns:
            위반 시 RiskViolation, 통과 시 None
        """
        pass


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


class RiskManager:
    """위험 관리자"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._rules: List[RiskRule] = []
        self._violation_log: List[Dict[str, Any]] = []

    def add_rule(self, rule: RiskRule) -> "RiskManager":
        """규칙 추가"""
        self._rules.append(rule)
        self.logger.info(f"Added risk rule: {rule.name}")
        return self

    def remove_rule(self, rule_name: str) -> bool:
        """규칙 제거"""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != rule_name]
        return len(self._rules) < before

    def get_rules(self) -> List[str]:
        """규칙 목록"""
        return [r.name for r in self._rules]

    def validate(self, context: RiskContext) -> RiskValidationResult:
        """
        주문 검증

        Args:
            context: 위험 평가 컨텍스트

        Returns:
            검증 결과
        """
        violations = []
        warnings = []

        for rule in self._rules:
            try:
                violation = rule.validate(context)
                if violation:
                    if violation.level == RiskLevel.BLOCK:
                        violations.append(violation)
                    else:
                        warnings.append(violation)
            except Exception as e:
                self.logger.error(f"Rule {rule.name} error: {e}")

        allowed = len(violations) == 0

        result = RiskValidationResult(
            allowed=allowed,
            violations=violations,
            warnings=warnings,
        )

        # Log violations
        if violations or warnings:
            self._violation_log.append({
                "timestamp": datetime.now().isoformat(),
                "ticker": context.ticker,
                "side": context.side,
                "result": result.to_dict(),
            })

        if not allowed:
            self.logger.warning(f"Order blocked: {[v.message for v in violations]}")

        return result

    def validate_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        portfolio_value: float,
        cash_balance: float,
        positions: Dict[str, Dict[str, Any]],
        daily_pnl: float = 0,
        daily_trades: int = 0,
        sector: Optional[str] = None,
        sector_positions: Optional[Dict[str, float]] = None
    ) -> RiskValidationResult:
        """
        주문 검증 (편의 메서드)
        """
        context = RiskContext(
            portfolio_value=portfolio_value,
            cash_balance=cash_balance,
            positions=positions,
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            daily_pnl=daily_pnl,
            daily_trades=daily_trades,
            sector=sector,
            sector_positions=sector_positions or {},
        )
        return self.validate(context)

    def get_violation_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """위반 로그 조회"""
        return self._violation_log[-limit:]

    def clear_violation_log(self) -> None:
        """위반 로그 초기화"""
        self._violation_log.clear()


def create_default_risk_manager() -> RiskManager:
    """기본 위험 관리자 생성"""
    manager = RiskManager()
    manager.add_rule(MaxPositionRule(max_percent=20))
    manager.add_rule(DailyLossLimitRule(max_loss_percent=3))
    manager.add_rule(MinCashRule(min_cash_percent=10))
    manager.add_rule(MaxDailyTradesRule(max_trades=10))
    return manager
