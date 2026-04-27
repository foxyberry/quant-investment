"""
Backward-compatibility shim.

The portfolio service has been split into focused sub-modules under
api/services/portfolio/. All public names are re-exported from here so
that existing imports continue to work without changes:

    from api.services.portfolio_service import PortfolioService, get_portfolio_service
    from api.services.portfolio_service import PresetNotFoundError, PresetInactiveError
"""

from api.services.portfolio import (  # noqa: F401
    PortfolioService,
    get_portfolio_service,
    PortfolioCoreService,
    PortfolioArchiveService,
    PortfolioExecutionService,
    PortfolioRiskService,
    PresetNotFoundError,
    PresetInactiveError,
    ENRICHMENT_TIMEOUT_SECONDS,
)
