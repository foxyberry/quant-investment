"""
Base Notifier
알림 발송기 기본 클래스 및 공통 타입

Usage:
    from portfolio.notifiers.base import BaseNotifier, AlertType, Notification
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AlertType(Enum):
    """알림 타입"""
    INFO = "INFO"
    PRICE_TARGET = "PRICE_TARGET"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    ORDER_EXECUTED = "ORDER_EXECUTED"
    RISK_WARNING = "RISK_WARNING"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    DAILY_REPORT = "DAILY_REPORT"


class Priority(Enum):
    """알림 우선순위"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Notification:
    """알림 데이터"""
    message: str
    alert_type: AlertType = AlertType.INFO
    priority: Priority = Priority.NORMAL
    ticker: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "alert_type": self.alert_type.value,
            "priority": self.priority.value,
            "ticker": self.ticker,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


# Alert type emoji mapping
ALERT_EMOJIS = {
    AlertType.INFO: "ℹ️",
    AlertType.PRICE_TARGET: "🎯",
    AlertType.STOP_LOSS: "🛑",
    AlertType.TAKE_PROFIT: "💰",
    AlertType.ORDER_EXECUTED: "✅",
    AlertType.RISK_WARNING: "⚠️",
    AlertType.SYSTEM_ERROR: "❌",
    AlertType.DAILY_REPORT: "📊",
}


class BaseNotifier(ABC):
    """알림 발송기 기본 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def send(self, message: str) -> bool:
        """메시지 발송"""
        pass

    def send_notification(self, notification: Notification) -> bool:
        """Notification 객체 발송"""
        formatted = self._format_notification(notification)
        return self.send(formatted)

    def send_alert(
        self,
        alert_type: str,
        ticker: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """알림 발송 (편의 메서드)"""
        notification = Notification(
            message=message,
            alert_type=AlertType(alert_type),
            ticker=ticker,
            details=details or {},
        )
        return self.send_notification(notification)

    def _format_notification(self, notification: Notification) -> str:
        """알림 포맷팅"""
        lines = []

        # Header with emoji based on type
        emoji = self._get_emoji(notification.alert_type)
        lines.append(f"{emoji} [{notification.alert_type.value}]")

        if notification.ticker:
            lines.append(f"Ticker: {notification.ticker}")

        lines.append(f"Message: {notification.message}")

        if notification.details:
            for key, value in notification.details.items():
                if isinstance(value, float):
                    lines.append(f"  {key}: {value:,.2f}")
                else:
                    lines.append(f"  {key}: {value}")

        lines.append(f"Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

    def _get_emoji(self, alert_type: AlertType) -> str:
        """알림 타입별 이모지"""
        return ALERT_EMOJIS.get(alert_type, "📢")
