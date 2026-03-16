"""
Pydantic schemas for portfolio alerts.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class PortfolioAlertHistoryEntry(BaseModel):
    id: int
    ticker: str
    signal_type: str
    message: str
    price_at_signal: Optional[float] = None
    fired_at: Optional[str] = None


class PortfolioAlertHistoryResponse(BaseModel):
    alerts: List[PortfolioAlertHistoryEntry]
    total_count: int


class PortfolioAlertConfigResponse(BaseModel):
    enabled: bool = False
    scan_interval_seconds: int = 60
    stop_loss_pct: float = 0.20
    take_profit_pct: float = 0.30
    trailing_stop_pct: float = 0.10
    technical_signals: bool = True
    market_hours_only: bool = True
    channels: List[str] = Field(default_factory=lambda: ["telegram"])


class PortfolioAlertConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    scan_interval_seconds: Optional[int] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    technical_signals: Optional[bool] = None
    market_hours_only: Optional[bool] = None
    channels: Optional[List[str]] = None


class PortfolioAlertScanResult(BaseModel):
    scanned_count: int
    alerts_fired: int
    message: str
