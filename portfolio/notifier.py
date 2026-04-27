"""
Notification System — DEPRECATED.

portfolio.notifier and portfolio.notifiers are deprecated.
New code should use api.services.notification_dispatcher instead:

    from api.services.notification_dispatcher import dispatch, dispatch_blocks

This module is kept for backward compatibility only.
"""

import warnings as _warnings
_warnings.warn(
    "portfolio.notifier is deprecated. Use api.services.notification_dispatcher instead.",
    DeprecationWarning,
    stacklevel=2,
)

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
