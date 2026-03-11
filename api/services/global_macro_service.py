"""Global macro snapshot service backed by yfinance tickers."""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import yfinance as yf

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


class GlobalMacroService:
    """Collects global macro market snapshots from yfinance symbols."""

    CACHE_TTL_WEEKDAY = 300
    CACHE_TTL_WEEKEND = 1800

    TICKERS: Dict[str, list[str]] = {
        "dxy": ["DX-Y.NYB", "DX=F"],
        "wti": ["CL=F"],
        "gold": ["GC=F"],
        "copper": ["HG=F"],
        "msci_em": ["EEM"],
        "msci_dm": ["EFA"],
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0.0

    def _is_weekday(self) -> bool:
        return datetime.now(ZoneInfo("America/New_York")).weekday() < 5

    def _get_cache_ttl(self) -> int:
        return self.CACHE_TTL_WEEKDAY if self._is_weekday() else self.CACHE_TTL_WEEKEND

    def _extract_close_values(self, frame: Any) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        if frame is None or getattr(frame, "empty", True):
            return None, None, None
        if "Close" not in frame.columns:
            return None, None, None

        closes = frame["Close"].dropna().tolist()
        if not closes:
            return None, None, None

        latest_close = float(closes[-1])
        prev_close = float(closes[-2]) if len(closes) >= 2 else None
        as_of = frame.index[-1].isoformat() if len(frame.index) else None
        return latest_close, prev_close, as_of

    def _fetch_ticker(self, symbols: list[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)

                latest: Optional[float] = None
                change_pct: Optional[float] = None
                as_of: Optional[str] = None

                try:
                    fast_info = ticker.fast_info or {}
                    last_price = fast_info.get("lastPrice")
                    if last_price is not None:
                        latest = float(last_price)
                except Exception:
                    logger.warning("Failed to read fast_info for %s", symbol, exc_info=True)

                history = ticker.history(period="2d", timeout=10)
                latest_close, prev_close, hist_as_of = self._extract_close_values(history)

                as_of = hist_as_of
                if latest is None:
                    latest = latest_close

                if latest is None:
                    continue

                if prev_close not in (None, 0):
                    change_pct = round(((latest - prev_close) / prev_close) * 100.0, 4)

                return latest, change_pct, as_of
            except Exception:
                logger.warning("Failed to fetch symbol %s", symbol, exc_info=True)

        logger.warning("Failed to fetch all fallback symbols: %s", symbols)
        return None, None, None

    def get_snapshot(self) -> Optional[Dict[str, Any]]:
        now = time.monotonic()
        ttl = self._get_cache_ttl()

        with self._lock:
            if self._cache is not None and (now - self._cache_time) < ttl:
                return self._cache

        snapshot: Dict[str, Any] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                key: executor.submit(self._fetch_ticker, symbols)
                for key, symbols in self.TICKERS.items()
            }
            for key, future in futures.items():
                try:
                    value, change_pct, as_of = future.result(timeout=15)
                except Exception:
                    logger.warning("Failed to collect global macro ticker: %s", key, exc_info=True)
                    value, change_pct, as_of = None, None, None

                snapshot[key] = {
                    "value": value,
                    "change_pct": change_pct,
                    "as_of": as_of,
                }

        values = [snapshot[key]["value"] for key in self.TICKERS]
        if all(v is None for v in values):
            return None

        msci_em = snapshot["msci_em"]["value"]
        msci_dm = snapshot["msci_dm"]["value"]
        copper = snapshot["copper"]["value"]
        gold = snapshot["gold"]["value"]

        snapshot["em_dm_ratio"] = (
            round(msci_em / msci_dm, 6)
            if msci_em is not None and msci_dm not in (None, 0)
            else None
        )
        snapshot["copper_gold_ratio"] = (
            round(copper / gold, 6)
            if copper is not None and gold not in (None, 0)
            else None
        )

        with self._lock:
            self._cache = snapshot
            self._cache_time = now

        return snapshot


_global_macro_service: Optional[GlobalMacroService] = None


def get_global_macro_service() -> GlobalMacroService:
    """Return singleton GlobalMacroService instance."""
    global _global_macro_service
    if _global_macro_service is None:
        _global_macro_service = GlobalMacroService()
    return _global_macro_service
