"""
Notifiers Module
알림 발송기 모듈

Usage:
    from portfolio.notifiers import (
        ConsoleNotifier, TelegramNotifier, SlackNotifier, MultiNotifier,
        AlertType, Priority, Notification,
        format_daily_report, format_order_notification
    )

    # Console (for testing)
    notifier = ConsoleNotifier()
    notifier.send("Hello!")

    # Telegram
    notifier = TelegramNotifier(bot_token="...", chat_id="...")
    notifier.send_alert("PRICE_TARGET", "005930.KS", "Target reached!")

    # Multiple notifiers
    multi = MultiNotifier()
    multi.add(ConsoleNotifier())
    multi.add(TelegramNotifier(bot_token="...", chat_id="..."))
    multi.send("Hello!")
"""

from .base import (
    AlertType, Priority, Notification,
    BaseNotifier, ALERT_EMOJIS
)
from .console import ConsoleNotifier
from .telegram import TelegramNotifier
from .slack import SlackNotifier
from .multi import MultiNotifier
from .formatters import (
    format_daily_report,
    format_order_notification,
    format_price_alert
)

__all__ = [
    # Enums & Data
    'AlertType', 'Priority', 'Notification', 'ALERT_EMOJIS',

    # Base class
    'BaseNotifier',

    # Notifier implementations
    'ConsoleNotifier',
    'TelegramNotifier',
    'SlackNotifier',
    'MultiNotifier',

    # Formatters
    'format_daily_report',
    'format_order_notification',
    'format_price_alert',
]
