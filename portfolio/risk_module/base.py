"""
Risk Management Base Types
위험 관리 기본 타입

Usage:
    from portfolio.risk_module.base import (
        RiskLevel, RiskContext, RiskViolation, RiskValidationResult, RiskRule
    )
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
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
