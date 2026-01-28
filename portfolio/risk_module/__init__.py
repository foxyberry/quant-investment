"""
Risk Management Module
위험 관리 모듈

Usage:
    from portfolio.risk_module import (
        RiskManager, RiskContext, RiskLevel, RiskValidationResult,
        MaxPositionRule, DailyLossLimitRule, SectorLimitRule,
        MinCashRule, MaxDailyTradesRule,
        create_default_risk_manager
    )

    # Create risk manager
    risk_manager = RiskManager()
    risk_manager.add_rule(MaxPositionRule(max_percent=20))
    risk_manager.add_rule(DailyLossLimitRule(max_loss_percent=3))

    # Or use default
    risk_manager = create_default_risk_manager()

    # Validate order
    result = risk_manager.validate_order(
        ticker="005930.KS",
        side="BUY",
        quantity=100,
        price=70000,
        portfolio_value=10000000,
        cash_balance=5000000,
        positions={}
    )

    if not result.allowed:
        print(f"Blocked: {result.violations}")
"""

from .base import (
    RiskLevel,
    RiskContext,
    RiskViolation,
    RiskValidationResult,
    RiskRule,
)
from .rules import (
    MaxPositionRule,
    DailyLossLimitRule,
    SectorLimitRule,
    MinCashRule,
    MaxDailyTradesRule,
)
from .manager import (
    RiskManager,
    create_default_risk_manager,
)

__all__ = [
    # Base types
    'RiskLevel',
    'RiskContext',
    'RiskViolation',
    'RiskValidationResult',
    'RiskRule',

    # Rules
    'MaxPositionRule',
    'DailyLossLimitRule',
    'SectorLimitRule',
    'MinCashRule',
    'MaxDailyTradesRule',

    # Manager
    'RiskManager',
    'create_default_risk_manager',
]
