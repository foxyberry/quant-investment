"""
Notification System
알림 시스템 (Telegram/Slack)

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드는 portfolio.notifiers 모듈을 직접 사용하세요.

Usage:
    # 기존 방식 (호환성 유지)
    from portfolio.notifier import TelegramNotifier, ConsoleNotifier

    # 권장 방식
    from portfolio.notifiers import TelegramNotifier, ConsoleNotifier
"""

# Re-export from new module structure for backward compatibility
from .notifiers import (
    # Enums & Data
    AlertType, Priority, Notification, ALERT_EMOJIS,

    # Base class
    BaseNotifier,

    # Notifier implementations
    ConsoleNotifier,
    TelegramNotifier,
    SlackNotifier,
    MultiNotifier,

    # Formatters
    format_daily_report,
    format_order_notification,
    format_price_alert,
)

__all__ = [
    'AlertType', 'Priority', 'Notification', 'ALERT_EMOJIS',
    'BaseNotifier',
    'ConsoleNotifier', 'TelegramNotifier', 'SlackNotifier', 'MultiNotifier',
    'format_daily_report', 'format_order_notification', 'format_price_alert',
]
