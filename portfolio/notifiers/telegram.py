"""
Telegram Notifier
텔레그램 알림

Usage:
    from portfolio.notifiers.telegram import TelegramNotifier

    notifier = TelegramNotifier(bot_token="...", chat_id="...")
    notifier.send("Hello!")
"""

import queue
import threading
import time
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from .base import BaseNotifier


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

        super().__init__()
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.rate_limit = rate_limit

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
