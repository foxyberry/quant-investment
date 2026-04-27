"""
Backward-compatibility shim.

The alert scanner has been moved to api/services/portfolio/portfolio_alert_service.py.
All public names are re-exported here so existing imports continue to work:

    from api.services.portfolio_alert_scanner import load_config, get_portfolio_alert_scanner
    from api.services.portfolio_alert_scanner import _CONFIG_PATH, HoldingInfo, AlertSettings
"""

from api.services.portfolio.portfolio_alert_service import (  # noqa: F401
    HoldingInfo,
    AlertSettings,
    PortfolioAlertScanner,
    load_config,
    get_portfolio_alert_scanner,
    _CONFIG_PATH,
    _load_holdings_from_db,
    _load_alert_settings,
    _is_market_hours,
    _fetch_prices,
    _format_sell_message,
    _is_finite,
)
