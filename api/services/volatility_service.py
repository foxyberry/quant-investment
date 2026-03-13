"""Volatility aggregation service for VIX/VKOSPI macro enrichment."""

from __future__ import annotations

import logging
import math
import threading
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class VolatilityService:
    """Collects VIX and VKOSPI volatility data."""

    CACHE_TTL_MARKET = 300
    CACHE_TTL_OFF_HOURS = 1800

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0.0

    def _is_us_market_hours(self) -> bool:
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]
        now_et = datetime.now(ZoneInfo("America/New_York"))
        # NYSE: Mon-Fri 09:30 ~ 16:00 ET (DST-aware)
        if now_et.weekday() >= 5:
            return False
        t = now_et.hour * 60 + now_et.minute
        return 570 <= t < 960  # 9:30=570min, 16:00=960min

    def _get_cache_ttl(self) -> int:
        return self.CACHE_TTL_MARKET if self._is_us_market_hours() else self.CACHE_TTL_OFF_HOURS

    @staticmethod
    def _to_iso_ts(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _extract_close_series(frame: Any) -> list[float]:
        if frame is None or getattr(frame, "empty", True):
            return []
        close_col = "Close" if "Close" in frame.columns else "종가" if "종가" in frame.columns else None
        if close_col is None:
            return []
        closes = frame[close_col].dropna().tolist()
        return [float(v) for v in closes]

    def _fetch_vix(self) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        try:
            import yfinance as yf
        except Exception:
            logger.warning("Failed to import yfinance for VIX fetch", exc_info=True)
            return None, None, None

        value: Optional[float] = None
        change_pct: Optional[float] = None
        as_of: Optional[str] = None

        try:
            ticker = yf.Ticker("^VIX")

            try:
                fast_info = ticker.fast_info or {}
                last_price = fast_info.get("lastPrice")
                if last_price is not None:
                    value = float(last_price)
            except Exception:
                logger.warning("Failed to fetch VIX fast_info", exc_info=True)

            hist = ticker.history(period="2d")
            closes = self._extract_close_series(hist)
            if closes:
                latest_close = closes[-1]
                if value is None:
                    value = latest_close
                as_of = self._to_iso_ts(hist.index[-1])
                if len(closes) >= 2 and closes[-2] != 0:
                    change_pct = round(((latest_close - closes[-2]) / closes[-2]) * 100.0, 4)

            if value is None:
                return None, None, None
            return value, change_pct, as_of
        except Exception:
            logger.warning("Failed to fetch VIX snapshot", exc_info=True)
            return None, None, None

    @staticmethod
    def _safe_get_index_ohlcv(stock_mod: Any, fromdate: str, todate: str, ticker: str) -> Any:
        """Call pykrx get_index_ohlcv_by_date with name_display=False fallback.

        pykrx >=1.2.4 may crash with KeyError('지수명') when IndexTicker
        returns an empty DataFrame.  Passing name_display=False avoids the
        broken name-lookup path.  If the kwarg is unsupported (older versions),
        fall back to the original call.
        """
        try:
            return stock_mod.get_index_ohlcv_by_date(fromdate, todate, ticker, name_display=False)
        except TypeError:
            return stock_mod.get_index_ohlcv_by_date(fromdate, todate, ticker)

    def _fetch_vkospi(self) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        try:
            from pykrx import stock
        except Exception:
            logger.warning("Failed to import pykrx for VKOSPI fetch", exc_info=True)
            logger.warning("pykrx unavailable; using VKOSPI proxy from ^KS200")
            return self._fetch_vkospi_proxy_from_kospi200()

        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]
        today = datetime.now(ZoneInfo("Asia/Seoul")).date()
        start_5d = today - timedelta(days=5)
        ticker = "1205"

        try:
            df_today = self._safe_get_index_ohlcv(stock, today.strftime("%Y%m%d"), today.strftime("%Y%m%d"), ticker)

            df_range = None
            if df_today is None or getattr(df_today, "empty", True):
                df_range = self._safe_get_index_ohlcv(stock, start_5d.strftime("%Y%m%d"), today.strftime("%Y%m%d"), ticker)
                if df_range is None or getattr(df_range, "empty", True):
                    return self._fetch_vkospi_proxy_from_kospi200()
                base_df = df_range
            else:
                base_df = df_today
                # Change% needs at least previous close; fetch short range for robustness.
                df_range = self._safe_get_index_ohlcv(stock, start_5d.strftime("%Y%m%d"), today.strftime("%Y%m%d"), ticker)

            closes = self._extract_close_series(base_df)
            if not closes:
                return self._fetch_vkospi_proxy_from_kospi200()

            value = closes[-1]
            as_of = self._to_iso_ts(base_df.index[-1])

            change_pct = None
            range_closes = self._extract_close_series(df_range)
            if len(range_closes) >= 2 and range_closes[-2] != 0:
                change_pct = round(((range_closes[-1] - range_closes[-2]) / range_closes[-2]) * 100.0, 4)

            return value, change_pct, as_of
        except Exception:
            logger.warning("Failed to fetch VKOSPI snapshot", exc_info=True)
            # Fall back to a volatility proxy computed from KOSPI200 daily returns.
            # This keeps the macro card populated when KRX/pykrx index metadata breaks.
            return self._fetch_vkospi_proxy_from_kospi200()

    def _fetch_vkospi_proxy_from_kospi200(self) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Fallback VKOSPI proxy using 20-day realized volatility of KOSPI200 (^KS200).

        Returns:
            (value, day_over_day_change_pct, as_of)
        """
        try:
            import yfinance as yf
        except Exception:
            logger.warning("Failed to import yfinance for VKOSPI proxy fetch", exc_info=True)
            return None, None, None

        try:
            hist = yf.Ticker("^KS200").history(period="60d")
            closes = self._extract_close_series(hist)
            if len(closes) < 22:
                return None, None, None

            returns: list[float] = []
            for idx in range(1, len(closes)):
                prev = closes[idx - 1]
                curr = closes[idx]
                if prev == 0:
                    continue
                returns.append((curr / prev) - 1.0)

            if len(returns) < 21:
                return None, None, None

            window = 20
            realized_vols: list[float] = []
            for end in range(window, len(returns) + 1):
                window_rets = returns[end - window:end]
                if len(window_rets) < 2:
                    continue
                mean = sum(window_rets) / len(window_rets)
                variance = sum((r - mean) ** 2 for r in window_rets) / (len(window_rets) - 1)
                vol = math.sqrt(variance) * math.sqrt(252.0) * 100.0
                realized_vols.append(vol)

            if not realized_vols:
                return None, None, None

            value = round(realized_vols[-1], 4)
            change_pct = None
            if len(realized_vols) >= 2 and realized_vols[-2] != 0:
                change_pct = round(((realized_vols[-1] - realized_vols[-2]) / realized_vols[-2]) * 100.0, 4)

            as_of = self._to_iso_ts(hist.index[-1])
            logger.warning("VKOSPI source unavailable; using ^KS200 realized-vol proxy")
            return value, change_pct, as_of
        except Exception:
            logger.warning("Failed to compute VKOSPI proxy from ^KS200", exc_info=True)
            return None, None, None

    def _classify_fear_greed(self, vix: float) -> str:
        if vix < 15:
            return "low_vol"
        if vix < 20:
            return "normal"
        if vix < 25:
            return "elevated"
        if vix < 30:
            return "high"
        return "extreme"

    def get_snapshot(self) -> Dict[str, Any]:
        now = time.monotonic()
        ttl = self._get_cache_ttl()
        with self._lock:
            if self._cache is not None and (now - self._cache_time) < ttl:
                return self._cache

        vix_value, vix_change, vix_as_of = self._fetch_vix()
        vkospi_value, vkospi_change, vkospi_as_of = self._fetch_vkospi()

        fear_greed = self._classify_fear_greed(vix_value) if vix_value is not None else None

        vkospi_vix_ratio = None
        if vkospi_value is not None and vix_value is not None and vix_value > 0:
            vkospi_vix_ratio = round(vkospi_value / vix_value, 3)

        snapshot = {
            "vix": vix_value,
            "vix_change_pct": vix_change,
            "vix_as_of": vix_as_of,
            "vkospi": vkospi_value,
            "vkospi_change_pct": vkospi_change,
            "vkospi_as_of": vkospi_as_of,
            "fear_greed": fear_greed,
            "vkospi_vix_ratio": vkospi_vix_ratio,
        }
        with self._lock:
            self._cache = snapshot
            self._cache_time = now
        return snapshot


_volatility_service: Optional[VolatilityService] = None


def get_volatility_service() -> VolatilityService:
    """Return singleton VolatilityService instance."""
    global _volatility_service
    if _volatility_service is None:
        _volatility_service = VolatilityService()
    return _volatility_service
