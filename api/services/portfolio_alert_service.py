"""
Backward-compatibility shim.

Alert recording/dispatch logic has been consolidated into
api/services/portfolio/portfolio_alert_service.py.
All public names are re-exported here so existing imports continue to work:

    from api.services.portfolio_alert_service import record_and_send, get_history
"""

from api.services.portfolio.portfolio_alert_service import (  # noqa: F401
    record_and_send,
    is_already_sent_today,
    get_history,
    _entry_from_row,
)
