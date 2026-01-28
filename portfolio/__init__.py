"""
Portfolio Management Module
포트폴리오 관리 모듈

Usage:
    from portfolio import Portfolio, PriceMonitor, OrderExecutor

    # Holdings management
    portfolio = Portfolio()
    portfolio.add("AAPL", quantity=10, avg_price=180)

    # Price monitoring
    monitor = PriceMonitor(interval=60)
    monitor.add("AAPL")
    monitor.start()

    # Order execution (paper trading)
    executor = OrderExecutor(dry_run=True)
    order = Order(ticker="AAPL", side="BUY", quantity=5)
    result = executor.execute(order, market_price=185)
"""

from .holdings import Portfolio, Holding
from .monitor import PriceMonitor, PriceData
from .trigger import ConditionChecker, TriggerCondition, TriggerType, TriggerEvent
from .conditions import (
    TradingContext, TradingCondition, BaseTradingCondition, ConditionChain,
    StopLossCondition, TakeProfitCondition, TrailingStopCondition,
    RSICondition, MACDCondition, HoldingPeriodCondition,
    create_default_sell_conditions, create_technical_conditions
)
from .quantity import (
    calculate_quantity, QuantityMethod, QuantityConfig,
    calculate_buy_quantity, calculate_sell_quantity, estimate_position_size
)
from .executor import Order, OrderResult, OrderExecutor, PaperExecutor, OrderStatus
from .risk import (
    RiskManager, RiskContext, RiskValidationResult, RiskViolation, RiskLevel,
    MaxPositionRule, DailyLossLimitRule, SectorLimitRule, MinCashRule,
    create_default_risk_manager
)
from .notifier import (
    BaseNotifier, ConsoleNotifier, TelegramNotifier, SlackNotifier, MultiNotifier,
    Notification, AlertType, Priority,
    format_daily_report, format_order_notification
)

__all__ = [
    # Holdings
    'Portfolio', 'Holding',

    # Monitoring
    'PriceMonitor', 'PriceData',

    # Triggers
    'ConditionChecker', 'TriggerCondition', 'TriggerType', 'TriggerEvent',

    # Trading Conditions
    'TradingContext', 'TradingCondition', 'BaseTradingCondition', 'ConditionChain',
    'StopLossCondition', 'TakeProfitCondition', 'TrailingStopCondition',
    'RSICondition', 'MACDCondition', 'HoldingPeriodCondition',
    'create_default_sell_conditions', 'create_technical_conditions',

    # Quantity
    'calculate_quantity', 'QuantityMethod', 'QuantityConfig',
    'calculate_buy_quantity', 'calculate_sell_quantity', 'estimate_position_size',

    # Executor
    'Order', 'OrderResult', 'OrderExecutor', 'PaperExecutor', 'OrderStatus',

    # Risk
    'RiskManager', 'RiskContext', 'RiskValidationResult', 'RiskViolation', 'RiskLevel',
    'MaxPositionRule', 'DailyLossLimitRule', 'SectorLimitRule', 'MinCashRule',
    'create_default_risk_manager',

    # Notifier
    'BaseNotifier', 'ConsoleNotifier', 'TelegramNotifier', 'SlackNotifier', 'MultiNotifier',
    'Notification', 'AlertType', 'Priority',
    'format_daily_report', 'format_order_notification',
]
