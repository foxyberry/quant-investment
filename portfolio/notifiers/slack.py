"""
Slack Notifier
Slack 웹훅 알림

Usage:
    from portfolio.notifiers.slack import SlackNotifier

    notifier = SlackNotifier(webhook_url="https://hooks.slack.com/...")
    notifier.send("Hello!")
"""

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from .base import BaseNotifier, Notification


class SlackNotifier(BaseNotifier):
    """Slack 웹훅 알림"""

    def __init__(self, webhook_url: str):
        """
        Args:
            webhook_url: Slack Incoming Webhook URL
        """
        if not HAS_REQUESTS:
            raise ImportError("requests library required for SlackNotifier")

        super().__init__()
        self.webhook_url = webhook_url

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
