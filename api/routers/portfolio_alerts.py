"""
Portfolio alert endpoints — history, config, manual scan trigger.
"""

from fastapi import APIRouter, Query

from api.schemas.portfolio_alert import (
    PortfolioAlertConfigResponse,
    PortfolioAlertConfigUpdate,
    PortfolioAlertHistoryResponse,
    PortfolioAlertScanResult,
)

router = APIRouter(prefix="/api/portfolio/alerts", tags=["portfolio-alerts"])


@router.get("/history", response_model=PortfolioAlertHistoryResponse)
async def get_alert_history(limit: int = Query(50, ge=1, le=200)):
    """Get recent portfolio alert history."""
    from api.services.portfolio_alert_service import get_history

    return get_history(limit=limit)


@router.get("/config", response_model=PortfolioAlertConfigResponse)
async def get_alert_config():
    """Get current alert settings from DB-backed config."""
    from api.services.portfolio_alert_config_service import get_portfolio_alert_config_service

    return get_portfolio_alert_config_service().get_config()


@router.put("/config", response_model=PortfolioAlertConfigResponse)
async def update_alert_config(body: PortfolioAlertConfigUpdate):
    """Update alert settings in DB-backed config."""
    from api.services.portfolio_alert_config_service import get_portfolio_alert_config_service

    return get_portfolio_alert_config_service().save_config(body.model_dump())


@router.post("/scan", response_model=PortfolioAlertScanResult)
async def trigger_scan():
    """Manually trigger a portfolio alert scan."""
    from api.services.portfolio_alert_scanner import get_portfolio_alert_scanner, load_config

    holdings, _ = load_config()
    scanner = get_portfolio_alert_scanner()
    alerts_fired = scanner.scan_once()

    return PortfolioAlertScanResult(
        scanned_count=len(holdings),
        alerts_fired=alerts_fired,
        message=f"Scanned {len(holdings)} holdings, fired {alerts_fired} alerts",
    )
