"""
Multi Notifier
다중 알림 발송기

Usage:
    from portfolio.notifiers.multi import MultiNotifier
    from portfolio.notifiers.console import ConsoleNotifier
    from portfolio.notifiers.telegram import TelegramNotifier

    notifier = MultiNotifier()
    notifier.add(ConsoleNotifier())
    notifier.add(TelegramNotifier(bot_token="...", chat_id="..."))
    notifier.send("Hello!")  # 모든 발송기로 전송
"""

from typing import List

from .base import BaseNotifier


class MultiNotifier(BaseNotifier):
    """다중 알림 발송기"""

    def __init__(self):
        super().__init__()
        self._notifiers: List[BaseNotifier] = []

    def add(self, notifier: BaseNotifier) -> "MultiNotifier":
        """알림 발송기 추가"""
        self._notifiers.append(notifier)
        return self

    def remove(self, notifier: BaseNotifier) -> bool:
        """알림 발송기 제거"""
        try:
            self._notifiers.remove(notifier)
            return True
        except ValueError:
            return False

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

    def count(self) -> int:
        """등록된 발송기 수"""
        return len(self._notifiers)
