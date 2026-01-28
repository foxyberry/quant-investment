"""
Notification System
알림 시스템 (Telegram/Slack)

Usage:
    from portfolio.notifier import TelegramNotifier, ConsoleNotifier

    # Telegram (requires bot token)
    notifier = TelegramNotifier(bot_token="...", chat_id="...")
    notifier.send("Hello!")

    # Console (for testing)
    notifier = ConsoleNotifier()
    notifier.send_alert("PRICE_TARGET", "005930.KS", "Target reached!")
"""

import logging
import queue
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


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


class BaseNotifier(ABC):
    """알림 발송기 기본 클래스"""

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
        emojis = {
            AlertType.INFO: "ℹ️",
            AlertType.PRICE_TARGET: "🎯",
            AlertType.STOP_LOSS: "🛑",
            AlertType.TAKE_PROFIT: "💰",
            AlertType.ORDER_EXECUTED: "✅",
            AlertType.RISK_WARNING: "⚠️",
            AlertType.SYSTEM_ERROR: "❌",
            AlertType.DAILY_REPORT: "📊",
        }
        return emojis.get(alert_type, "📢")


class ConsoleNotifier(BaseNotifier):
    """콘솔 출력 알림 (테스트용)"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._history: List[Notification] = []

    def send(self, message: str) -> bool:
        print(f"\n{'='*50}")
        print("NOTIFICATION")
        print(f"{'='*50}")
        print(message)
        print(f"{'='*50}\n")
        return True

    def send_notification(self, notification: Notification) -> bool:
        self._history.append(notification)
        return super().send_notification(notification)

    def get_history(self) -> List[Dict[str, Any]]:
        return [n.to_dict() for n in self._history]


class TelegramNotifier(BaseNotifier):
    """텔레그램 알림"""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        rate_limit: float = 1.0  # 초당 최대 1개 메시지
    ):
        """
        Args:
            bot_token: Telegram Bot API 토큰
            chat_id: 메시지를 보낼 채팅 ID
            rate_limit: 초당 최대 메시지 수
        """
        if not HAS_REQUESTS:
            raise ImportError("requests library required for TelegramNotifier")

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.rate_limit = rate_limit
        self.logger = logging.getLogger(__name__)

        self._last_send_time = 0
        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def send(self, message: str) -> bool:
        """동기 메시지 발송"""
        # Rate limiting
        now = time.time()
        wait_time = (1.0 / self.rate_limit) - (now - self._last_send_time)
        if wait_time > 0:
            time.sleep(wait_time)

        try:
            url = self.API_URL.format(token=self.bot_token)
            response = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
                timeout=10
            )

            self._last_send_time = time.time()

            if response.status_code == 200:
                self.logger.debug("Telegram message sent")
                return True
            else:
                self.logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Telegram send error: {e}")
            return False

    def send_async(self, message: str) -> None:
        """비동기 메시지 발송 (큐에 추가)"""
        self._queue.put(message)
        self._ensure_worker_running()

    def _ensure_worker_running(self):
        """워커 스레드 확인 및 시작"""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()

    def _worker_loop(self):
        """메시지 큐 처리 루프"""
        while self._running:
            try:
                message = self._queue.get(timeout=1.0)
                self.send(message)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")

    def stop(self):
        """워커 스레드 중지"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)


class SlackNotifier(BaseNotifier):
    """Slack 웹훅 알림"""

    def __init__(self, webhook_url: str):
        """
        Args:
            webhook_url: Slack Incoming Webhook URL
        """
        if not HAS_REQUESTS:
            raise ImportError("requests library required for SlackNotifier")

        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)

    def send(self, message: str) -> bool:
        """메시지 발송"""
        try:
            response = requests.post(
                self.webhook_url,
                json={"text": message},
                timeout=10
            )

            if response.status_code == 200:
                self.logger.debug("Slack message sent")
                return True
            else:
                self.logger.error(f"Slack API error: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Slack send error: {e}")
            return False

    def _format_notification(self, notification: Notification) -> str:
        """Slack 포맷 (Markdown)"""
        lines = []

        emoji = self._get_emoji(notification.alert_type)
        lines.append(f"{emoji} *[{notification.alert_type.value}]*")

        if notification.ticker:
            lines.append(f">Ticker: `{notification.ticker}`")

        lines.append(f">{notification.message}")

        if notification.details:
            lines.append("```")
            for key, value in notification.details.items():
                if isinstance(value, float):
                    lines.append(f"{key}: {value:,.2f}")
                else:
                    lines.append(f"{key}: {value}")
            lines.append("```")

        return "\n".join(lines)


class MultiNotifier(BaseNotifier):
    """다중 알림 발송기"""

    def __init__(self):
        self._notifiers: List[BaseNotifier] = []
        self.logger = logging.getLogger(__name__)

    def add(self, notifier: BaseNotifier) -> "MultiNotifier":
        """알림 발송기 추가"""
        self._notifiers.append(notifier)
        return self

    def send(self, message: str) -> bool:
        """모든 발송기로 메시지 발송"""
        success = True
        for notifier in self._notifiers:
            try:
                if not notifier.send(message):
                    success = False
            except Exception as e:
                self.logger.error(f"Notifier error: {e}")
                success = False
        return success


# Report formatting helpers
def format_daily_report(
    date: datetime,
    portfolio_value: float,
    daily_pnl: float,
    daily_pnl_pct: float,
    holdings: List[Dict[str, Any]],
    trades: List[Dict[str, Any]] = None
) -> str:
    """일일 리포트 포맷팅"""
    lines = [
        f"📊 Daily Report - {date.strftime('%Y-%m-%d')}",
        "=" * 40,
        f"Portfolio Value: {portfolio_value:,.0f}",
        f"Daily P&L: {daily_pnl:+,.0f} ({daily_pnl_pct:+.2f}%)",
        "",
        "Holdings:",
    ]

    for h in holdings:
        pnl_pct = h.get("pnl_pct", 0)
        emoji = "📈" if pnl_pct >= 0 else "📉"
        lines.append(
            f"  {emoji} {h['ticker']}: {h.get('current_value', 0):,.0f} ({pnl_pct:+.1f}%)"
        )

    if trades:
        lines.append("")
        lines.append(f"Trades Today: {len(trades)}")
        for t in trades[:5]:  # Show max 5
            lines.append(f"  • {t.get('side', '')} {t.get('ticker', '')} x{t.get('quantity', 0)}")

    lines.append("=" * 40)
    return "\n".join(lines)


def format_order_notification(
    ticker: str,
    side: str,
    quantity: int,
    price: float,
    status: str
) -> str:
    """주문 알림 포맷팅"""
    emoji = "🟢" if side == "BUY" else "🔴"
    return (
        f"{emoji} Order {status}\n"
        f"Ticker: {ticker}\n"
        f"Side: {side}\n"
        f"Quantity: {quantity}\n"
        f"Price: {price:,.0f}\n"
        f"Value: {quantity * price:,.0f}"
    )
