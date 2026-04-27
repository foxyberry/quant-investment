"""
api.services.portfolio — re-exports all public symbols from the portfolio sub-services.

The unified PortfolioService class is assembled here via inheritance so that
existing callers using:

    from api.services.portfolio_service import PortfolioService, get_portfolio_service

continue to work without change when they import via the compatibility shim
at api/services/portfolio_service.py.

Inheritance chain:
    PortfolioBaseService          (init, caches, static helpers)
        -> PortfolioPriceService  (price/sector/metadata fetching)
            -> PortfolioCoreService   (holdings CRUD, P&L, CSV)
                -> PortfolioArchiveService  (portfolio archive)
                    -> PortfolioExecutionService  (trade recording, history)
                        -> PortfolioRiskService   (sell rules, evaluation, signals)
                            -> PortfolioService   (assembled — backward compat)
"""

from api.services.portfolio.portfolio_base_service import (
    PortfolioBaseService,
    PresetNotFoundError,
    PresetInactiveError,
    ENRICHMENT_TIMEOUT_SECONDS,
)
from api.services.portfolio.portfolio_price_service import PortfolioPriceService
from api.services.portfolio.portfolio_core_service import PortfolioCoreService
from api.services.portfolio.portfolio_archive_service import PortfolioArchiveService
from api.services.portfolio.portfolio_execution_service import PortfolioExecutionService
from api.services.portfolio.portfolio_risk_service import PortfolioRiskService
from api.services.portfolio.portfolio_alert_service import (
    HoldingInfo,
    AlertSettings,
    PortfolioAlertScanner,
    load_config,
    record_and_send,
    is_already_sent_today,
    get_history,
    get_portfolio_alert_scanner,
    _CONFIG_PATH,
    _load_holdings_from_db,
    _load_alert_settings,
    _is_market_hours,
    _fetch_prices,
    _format_sell_message,
    _is_finite,
)

from typing import Optional


class PortfolioService(PortfolioRiskService):
    """
    Unified portfolio service (assembled from focused sub-services).

    This class exists solely to maintain backward compatibility:
    callers that instantiate PortfolioService get the full combined API.
    """


# Singleton instance (mirrors the original portfolio_service.py pattern)
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """
    Get or create the portfolio service singleton.

    Returns:
        PortfolioService instance
    """
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service


__all__ = [
    # Assembled service (primary API)
    "PortfolioService",
    "get_portfolio_service",
    # Sub-service classes (for direct import)
    "PortfolioBaseService",
    "PortfolioPriceService",
    "PortfolioCoreService",
    "PortfolioArchiveService",
    "PortfolioExecutionService",
    "PortfolioRiskService",
    # Exceptions
    "PresetNotFoundError",
    "PresetInactiveError",
    # Constants
    "ENRICHMENT_TIMEOUT_SECONDS",
    # Alert scanner symbols
    "HoldingInfo",
    "AlertSettings",
    "PortfolioAlertScanner",
    "load_config",
    "record_and_send",
    "is_already_sent_today",
    "get_history",
    "get_portfolio_alert_scanner",
    "_CONFIG_PATH",
    "_load_holdings_from_db",
    "_load_alert_settings",
    "_is_market_hours",
    "_fetch_prices",
    "_format_sell_message",
    "_is_finite",
]
