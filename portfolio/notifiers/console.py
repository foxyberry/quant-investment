"""
Console Notifier
콘솔 출력 알림 (테스트/개발용)

Usage:
    from portfolio.notifiers.console import ConsoleNotifier

    notifier = ConsoleNotifier()
    notifier.send("Hello!")
"""

from typing import List, Dict, Any

from .base import BaseNotifier, Notification


class ConsoleNotifier(BaseNotifier):
    """콘솔 출력 알림 (테스트용)"""

    def __init__(self):
        super().__init__()
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
        """알림 히스토리 조회"""
        return [n.to_dict() for n in self._history]

    def clear_history(self) -> None:
        """히스토리 초기화"""
        self._history.clear()
