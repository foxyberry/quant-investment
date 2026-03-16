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
    """Get current alert settings from portfolio.yaml."""
    from api.services.portfolio_alert_scanner import load_config

    _, settings = load_config()
    return PortfolioAlertConfigResponse(
        enabled=settings.enabled,
        scan_interval_seconds=settings.scan_interval_seconds,
        stop_loss_pct=settings.stop_loss_pct,
        take_profit_pct=settings.take_profit_pct,
        trailing_stop_pct=settings.trailing_stop_pct,
        technical_signals=settings.technical_signals,
        market_hours_only=settings.market_hours_only,
        channels=settings.channels or ["telegram"],
    )


@router.put("/config", response_model=PortfolioAlertConfigResponse)
async def update_alert_config(body: PortfolioAlertConfigUpdate):
    """Update alert settings in portfolio.yaml."""
    import yaml
    from api.services.portfolio_alert_scanner import _CONFIG_PATH

    if not _CONFIG_PATH.exists():
        return PortfolioAlertConfigResponse()

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    alert_raw = data.setdefault("alert_settings", {})

    for field in (
        "enabled",
        "scan_interval_seconds",
        "stop_loss_pct",
        "take_profit_pct",
        "trailing_stop_pct",
        "technical_signals",
        "market_hours_only",
        "channels",
    ):
        val = getattr(body, field, None)
        if val is not None:
            alert_raw[field] = val

    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    return PortfolioAlertConfigResponse(**alert_raw)


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
