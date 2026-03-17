"""
Portfolio Alert Scanner — background thread that periodically checks holdings
against sell/buy conditions and fires dedup-aware Telegram alerts.

Uses yfinance for price data (free, 1-minute polling acceptable).
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "portfolio.yaml"


@dataclass
class HoldingInfo:
    ticker: str
    name: str
    buy_price: float
    quantity: int


@dataclass
class AlertSettings:
    enabled: bool = True
    scan_interval_seconds: int = 60
    stop_loss_pct: float = 0.20
    take_profit_pct: float = 0.30
    trailing_stop_pct: float = 0.10
    technical_signals: bool = True
    market_hours_only: bool = True
    channels: list = None

    def __post_init__(self):
        if self.channels is None:
            self.channels = ["telegram"]


def _load_holdings_from_db() -> list[HoldingInfo]:
    """Load current holdings from the database (source of truth)."""
    try:
        from api.database import SessionLocal
        from api.models.portfolio import Holding

        db = SessionLocal()
        try:
            rows = db.query(Holding).filter(Holding.quantity > 0).all()
            return [
                HoldingInfo(
                    ticker=row.ticker,
                    name=row.name or row.ticker,
                    buy_price=float(row.avg_price or 0),
                    quantity=int(row.quantity),
                )
                for row in rows
            ]
        finally:
            db.close()
    except Exception:
        logger.warning("Failed to load holdings from DB", exc_info=True)
        return []


def _load_alert_settings() -> AlertSettings:
    """Load alert settings from portfolio.yaml."""
    if not _CONFIG_PATH.exists():
        return AlertSettings(enabled=False)

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    alert_raw = data.get("alert_settings", {})
    return AlertSettings(
        enabled=alert_raw.get("enabled", True),
        scan_interval_seconds=alert_raw.get("scan_interval_seconds", 60),
        stop_loss_pct=alert_raw.get("stop_loss_pct", 0.20),
        take_profit_pct=alert_raw.get("take_profit_pct", 0.30),
        trailing_stop_pct=alert_raw.get("trailing_stop_pct", 0.10),
        technical_signals=alert_raw.get("technical_signals", True),
        market_hours_only=alert_raw.get("market_hours_only", True),
        channels=alert_raw.get("channels", ["telegram"]),
    )


def load_config() -> tuple[list[HoldingInfo], AlertSettings]:
    """Load holdings from DB and alert settings from YAML."""
    holdings = _load_holdings_from_db()
    settings = _load_alert_settings()
    return holdings, settings


# ---------------------------------------------------------------------------
# Market hours check
# ---------------------------------------------------------------------------


def _is_market_hours() -> bool:
    """Simple check: skip weekends. For more precision, use market_calendar."""
    now = datetime.utcnow()
    # Skip Saturday (5) and Sunday (6)
    if now.weekday() in (5, 6):
        return False
    return True


# ---------------------------------------------------------------------------
# Price fetcher
# ---------------------------------------------------------------------------


def _fetch_prices(tickers: list[str]) -> Dict[str, float]:
    """Fetch latest prices for a batch of tickers via yfinance."""
    try:
        import yfinance as yf

        prices: Dict[str, float] = {}
        # Batch download — single HTTP request for all tickers
        data = yf.download(tickers, period="1d", interval="1m", progress=False, threads=True)
        if data.empty:
            return prices

        close = data.get("Close")
        if close is None:
            return prices

        if len(tickers) == 1:
            # Single ticker: close is a Series
            last_val = close.dropna().iloc[-1] if not close.dropna().empty else None
            if last_val is not None:
                prices[tickers[0]] = float(last_val)
        else:
            # Multiple tickers: close is a DataFrame
            for t in tickers:
                if t in close.columns:
                    col = close[t].dropna()
                    if not col.empty:
                        prices[t] = float(col.iloc[-1])

        return prices
    except Exception:
        logger.warning("yfinance price fetch failed", exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Message formatters
# ---------------------------------------------------------------------------


def _format_sell_message(
    holding: HoldingInfo,
    signal_type: str,
    price: float,
    change_pct: float,
) -> str:
    """Format a sell signal alert message."""
    labels = {
        "stop_loss": "손절",
        "take_profit": "익절",
        "trailing_stop": "트레일링 스톱",
    }
    label = labels.get(signal_type, signal_type)
    emoji = "🔴" if signal_type == "stop_loss" else "🟢" if signal_type == "take_profit" else "🟡"
    sign = "+" if change_pct >= 0 else ""

    # Currency formatting
    ticker = holding.ticker
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        price_str = f"₩{price:,.0f}"
        buy_str = f"₩{holding.buy_price:,.0f}"
    else:
        price_str = f"${price:,.2f}"
        buy_str = f"${holding.buy_price:,.2f}"

    return (
        f"{emoji} 매도 시그널 — {label}\n"
        f"종목: {holding.name} ({ticker.split('.')[0]})\n"
        f"사유: {label} {sign}{change_pct:.1%} 도달\n"
        f"현재가: {price_str}\n"
        f"매수가: {buy_str}"
    )


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class PortfolioAlertScanner:
    """Background scanner that checks portfolio holdings and fires alerts."""

    def __init__(self):
        self._running = False
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3

    def start(self) -> None:
        """Launch as daemon thread."""
        self._running = True
        threading.Thread(
            target=self._run_loop, daemon=True, name="portfolio-alert-scanner"
        ).start()
        logger.info("Portfolio alert scanner started")

    def stop(self) -> None:
        self._running = False

    def _run_loop(self) -> None:
        while self._running:
            holdings, settings = load_config()
            if not settings.enabled:
                time.sleep(60)
                continue

            interval = max(settings.scan_interval_seconds, 30)

            try:
                self._scan(holdings, settings)
                self._consecutive_failures = 0
            except Exception:
                self._consecutive_failures += 1
                logger.exception("Portfolio alert scan failed (attempt %d)", self._consecutive_failures)
                if self._consecutive_failures >= self._max_consecutive_failures:
                    interval = max(interval, 300)  # Back off to 5 minutes
                    logger.warning("Too many consecutive failures, backing off to %ds", interval)

            time.sleep(interval)

    def _scan(self, holdings: list[HoldingInfo], settings: AlertSettings) -> int:
        """Run a single scan cycle. Returns number of alerts fired."""
        if not holdings:
            return 0

        if settings.market_hours_only and not _is_market_hours():
            logger.debug("Market closed, skipping scan")
            return 0

        tickers = [h.ticker for h in holdings]
        prices = _fetch_prices(tickers)
        if not prices:
            logger.debug("No prices fetched, skipping")
            return 0

        from api.services.portfolio_alert_service import record_and_send

        alerts_fired = 0
        for holding in holdings:
            price = prices.get(holding.ticker)
            if price is None or holding.buy_price <= 0:
                continue

            change_pct = (price - holding.buy_price) / holding.buy_price

            # Stop loss
            if change_pct <= -settings.stop_loss_pct:
                msg = _format_sell_message(holding, "stop_loss", price, change_pct)
                if record_and_send(holding.ticker, "stop_loss", msg, price):
                    alerts_fired += 1

            # Take profit
            if change_pct >= settings.take_profit_pct:
                msg = _format_sell_message(holding, "take_profit", price, change_pct)
                if record_and_send(holding.ticker, "take_profit", msg, price):
                    alerts_fired += 1

        if alerts_fired:
            logger.info("Portfolio scan fired %d alerts", alerts_fired)

        return alerts_fired

    def scan_once(self) -> int:
        """Manual trigger for a single scan. Returns alerts fired count."""
        holdings, settings = load_config()
        # Override market hours check for manual scans
        original = settings.market_hours_only
        settings.market_hours_only = False
        try:
            return self._scan(holdings, settings)
        finally:
            settings.market_hours_only = original


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_scanner: Optional[PortfolioAlertScanner] = None


def get_portfolio_alert_scanner() -> PortfolioAlertScanner:
    global _scanner
    if _scanner is None:
        _scanner = PortfolioAlertScanner()
    return _scanner
