"""
Portfolio Alert Service.

Combines alert scanning logic (background thread, price fetching, signal matching)
with dedup-aware alert recording and channel dispatch.

Absorbs content previously in:
  - api/services/portfolio_alert_scanner.py
  - api/services/portfolio_alert_service.py
"""

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError

from api.database import SessionLocal
from api.models.portfolio_alert import PortfolioAlertHistory
from api.schemas.portfolio_alert import PortfolioAlertHistoryEntry, PortfolioAlertHistoryResponse
from api.services.portfolio_alert_config_service import (
    # Re-exported here for the backward-compat scanner shim.
    _CONFIG_PATH,
    get_portfolio_alert_config_service,
)
from api.services.portfolio.portfolio_trailing_service import update_and_check_trailing

logger = logging.getLogger(__name__)

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
    """Load alert settings from DB-backed config service."""
    alert_raw = get_portfolio_alert_config_service().get_config().model_dump()
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
    """Load holdings from DB and alert settings from DB-backed config."""
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


def _is_finite(val: float) -> bool:
    """Check if a price value is finite and positive."""
    import math
    return math.isfinite(val) and val > 0


def _fetch_prices(tickers: list[str]) -> Dict[str, float]:
    """Fetch latest prices for a batch of tickers via yfinance."""
    try:
        import yfinance as yf

        prices: Dict[str, float] = {}

        kr_tickers = [t for t in tickers if t.endswith((".KS", ".KQ"))]
        us_tickers = [t for t in tickers if t not in kr_tickers]

        def _extract_batch_prices(batch_tickers: list[str], **download_kwargs: Any) -> None:
            if not batch_tickers:
                return

            try:
                data = yf.download(batch_tickers, progress=False, threads=False, **download_kwargs)
            except Exception:
                logger.warning(
                    "yfinance batch download failed for tickers: %s",
                    ", ".join(batch_tickers),
                    exc_info=True,
                )
                return

            if data.empty:
                logger.warning("No batch price data returned for tickers: %s", ", ".join(batch_tickers))
                return

            close = data.get("Close")
            if close is None:
                logger.warning("Missing Close data in batch response for tickers: %s", ", ".join(batch_tickers))
                return

            import pandas as pd

            if len(batch_tickers) == 1:
                # yf.download with single ticker may return DataFrame or Series
                if isinstance(close, pd.DataFrame):
                    series = close.iloc[:, 0].dropna()
                else:
                    series = close.dropna()
                if not series.empty:
                    val = float(series.iloc[-1])
                    if _is_finite(val):
                        prices[batch_tickers[0]] = val
                return

            for ticker in batch_tickers:
                if ticker not in close.columns:
                    continue
                series = close[ticker].dropna()
                if not series.empty:
                    val = float(series.iloc[-1])
                    if _is_finite(val):
                        prices[ticker] = val

        _extract_batch_prices(kr_tickers, period="5d", interval="5m")
        _extract_batch_prices(us_tickers, period="1d", interval="1m")

        missing_tickers = [ticker for ticker in tickers if ticker not in prices]
        for ticker in missing_tickers:
            try:
                ticker_obj = yf.Ticker(ticker)

                last_price = None
                try:
                    fast_info = ticker_obj.fast_info or {}
                    last_price = fast_info.get("lastPrice")
                except Exception:
                    last_price = None

                if last_price is None:
                    info = ticker_obj.info or {}
                    last_price = info.get("regularMarketPrice")

                if last_price is None:
                    logger.warning("Skipping ticker with no price data after fallback: %s", ticker)
                    continue

                price_val = float(last_price)
                if not _is_finite(price_val):
                    logger.warning("Non-finite fallback price for ticker %s: %s", ticker, last_price)
                    continue

                prices[ticker] = price_val
            except Exception:
                logger.warning("Fallback price fetch failed for ticker: %s", ticker, exc_info=True)

        failed_tickers = [ticker for ticker in tickers if ticker not in prices]
        if failed_tickers:
            logger.warning("Failed to fetch prices for tickers: %s", ", ".join(failed_tickers))

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
    reason: Optional[str] = None,
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

    message = (
        f"{emoji} 매도 시그널 — {label}\n"
        f"종목: {holding.name} ({ticker.split('.')[0]})\n"
        f"사유: {label} {sign}{change_pct:.1%} 도달\n"
        f"현재가: {price_str}\n"
        f"매수가: {buy_str}"
    )
    if reason:
        message += f"\n상세: {reason}"
    return message


# ---------------------------------------------------------------------------
# Dedup-aware alert recording and dispatch
# ---------------------------------------------------------------------------


def _entry_from_row(row: PortfolioAlertHistory) -> PortfolioAlertHistoryEntry:
    return PortfolioAlertHistoryEntry(
        id=row.id,
        ticker=row.ticker,
        signal_type=row.signal_type,
        message=row.message,
        price_at_signal=row.price_at_signal,
        fired_at=row.fired_at.isoformat() if row.fired_at else None,
    )


def is_already_sent_today(ticker: str, signal_type: str) -> bool:
    """Check if the same (ticker, signal_type) alert was already sent today."""
    today = date.today()
    db = SessionLocal()
    try:
        exists = (
            db.query(PortfolioAlertHistory)
            .filter(
                PortfolioAlertHistory.ticker == ticker,
                PortfolioAlertHistory.signal_type == signal_type,
                PortfolioAlertHistory.dedup_date == today,
            )
            .first()
        )
        return exists is not None
    finally:
        db.close()


def record_and_send(
    ticker: str,
    signal_type: str,
    message: str,
    price: Optional[float] = None,
    channels: Optional[list[str]] = None,
) -> bool:
    """Record alert and send to configured channels. Returns False if already sent today."""
    today = date.today()
    now = datetime.utcnow()  # noqa: DTZ003

    db = SessionLocal()
    try:
        row = PortfolioAlertHistory(
            ticker=ticker,
            signal_type=signal_type,
            message=message,
            price_at_signal=price,
            fired_at=now,
            dedup_date=today,
        )
        db.add(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.debug("Alert already sent today: %s/%s", ticker, signal_type)
        return False
    finally:
        db.close()

    # Dispatch to specified channels (or all enabled if not specified)
    from api.services.notification_dispatcher import dispatch
    dispatch(message, channels=channels)
    return True


def get_history(limit: int = 50) -> PortfolioAlertHistoryResponse:
    """Get recent alert history."""
    limit = max(1, min(limit, 200))
    db = SessionLocal()
    try:
        total = db.query(PortfolioAlertHistory).count()
        rows = (
            db.query(PortfolioAlertHistory)
            .order_by(PortfolioAlertHistory.fired_at.desc())
            .limit(limit)
            .all()
        )
        return PortfolioAlertHistoryResponse(
            alerts=[_entry_from_row(r) for r in rows],
            total_count=total,
        )
    finally:
        db.close()


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

        alerts_fired = 0
        db = SessionLocal()
        trailing_state_changed = False
        try:
            for holding in holdings:
                price = prices.get(holding.ticker)
                if price is None or holding.buy_price <= 0:
                    continue

                change_pct = (price - holding.buy_price) / holding.buy_price

                # Stop loss
                if change_pct <= -settings.stop_loss_pct:
                    msg = _format_sell_message(holding, "stop_loss", price, change_pct)
                    if record_and_send(holding.ticker, "stop_loss", msg, price, channels=settings.channels):
                        alerts_fired += 1

                # Take profit
                if change_pct >= settings.take_profit_pct:
                    msg = _format_sell_message(holding, "take_profit", price, change_pct)
                    if record_and_send(holding.ticker, "take_profit", msg, price, channels=settings.channels):
                        alerts_fired += 1

                _, trailing_reason = update_and_check_trailing(
                    db,
                    holding.ticker,
                    price,
                    settings.trailing_stop_pct,
                )
                if trailing_reason:
                    msg = _format_sell_message(
                        holding,
                        "trailing_stop",
                        price,
                        change_pct,
                        reason=trailing_reason,
                    )
                    if record_and_send(
                        holding.ticker,
                        "trailing_stop",
                        msg,
                        price,
                        channels=settings.channels,
                    ):
                        alerts_fired += 1
                if settings.trailing_stop_pct > 0 and price > 0:
                    trailing_state_changed = True
            if trailing_state_changed:
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
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
