"""
Risk Management Rules Engine
위험 관리 규칙 엔진

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드는 portfolio.risk_module 모듈을 직접 사용하세요.

Usage:
    # 기존 방식 (호환성 유지)
    from portfolio.risk import RiskManager, MaxPositionRule

    # 권장 방식
    from portfolio.risk_module import RiskManager, MaxPositionRule
"""

# Re-export from new module structure for backward compatibility
from .risk_module import (
    # Base types
    RiskLevel,
    RiskContext,
    RiskViolation,
    RiskValidationResult,
    RiskRule,

    # Rules
    MaxPositionRule,
    DailyLossLimitRule,
    SectorLimitRule,
    MinCashRule,
    MaxDailyTradesRule,

    # Manager
    RiskManager,
    create_default_risk_manager,
)

__all__ = [
    'RiskLevel',
    'RiskContext',
    'RiskViolation',
    'RiskValidationResult',
    'RiskRule',
    'MaxPositionRule',
    'DailyLossLimitRule',
    'SectorLimitRule',
    'MinCashRule',
    'MaxDailyTradesRule',
    'RiskManager',
    'create_default_risk_manager',
]
