"""
Risk Manager
위험 관리자

Usage:
    from portfolio.risk_module.manager import RiskManager, create_default_risk_manager
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import RiskRule, RiskContext, RiskLevel, RiskValidationResult
from .rules import (
    MaxPositionRule, DailyLossLimitRule, MinCashRule, MaxDailyTradesRule
)


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
