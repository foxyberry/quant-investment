"""
Market Data Service Module.

Provides business logic for market data operations including
OHLCV data, quotes, and technical indicators.
"""

import logging
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from utils.data_cache import OHLCVCache, get_cache
from data_enrichment import TechnicalEnricher

logger = logging.getLogger(__name__)


class MarketService:
    """
    Market data service.

    Provides access to market data using OHLCVCache for efficient
    data retrieval and TechnicalEnricher for indicator calculations.
    """

    _TICKER_INFO_TTL_SECONDS = 60 * 60
    _TICKER_INFO_MAXSIZE = 256
    _ticker_info_cache: "OrderedDict[str, tuple[datetime, Dict[str, Any]]]" = OrderedDict()

    def __init__(self, cache: Optional[OHLCVCache] = None):
        """
        Initialize the market service.

        Args:
            cache: OHLCVCache instance. Uses default singleton if not provided.
        """
        self.cache = cache or get_cache()
        self.technical_enricher = TechnicalEnricher()

    def get_ohlcv(
        self,
        ticker: str,
        days: int = 100,
        data: Optional[pd.DataFrame] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get OHLCV data for a ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', '005930.KS')
            days: Number of days to retrieve (default: 100)
            data: Optional pre-fetched OHLCV DataFrame to avoid extra cache reads.

        Returns:
            Dictionary containing ticker, data list, and period_days,
            or None if data unavailable.
        """
        try:
            if data is None:
                data = self.cache.get(ticker, days=days)

            if data is None or data.empty:
                logger.warning(f"No OHLCV data found for {ticker}")
                return None

            ohlcv_items = self._serialize_ohlcv(data.tail(days))

            return {
                "ticker": ticker,
                "data": ohlcv_items,
                "period_days": len(ohlcv_items),
            }

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {ticker}: {e}")
            return None

    def get_quote(
        self,
        ticker: str,
        data: Optional[pd.DataFrame] = None,
        include_name: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current quote for a ticker.

        Uses cached data to compute the latest quote information.

        Args:
            ticker: Stock ticker symbol
            data: Optional pre-fetched OHLCV DataFrame (uses latest 5 rows).
            include_name: Whether to resolve company name from cached ticker info.

        Returns:
            Dictionary with current quote information, or None if unavailable.
        """
        try:
            if data is None:
                data = self.cache.get(ticker, days=5)
            else:
                data = data.tail(5)

            if data is None or data.empty:
                logger.warning(f"No quote data found for {ticker}")
                return None

            # Get latest row
            latest = data.iloc[-1]
            current_price = float(latest["close"])
            volume = int(latest["volume"])

            # Calculate change from previous day
            if len(data) >= 2:
                prev_close = float(data.iloc[-2]["close"])
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close != 0 else 0.0
            else:
                change = 0.0
                change_pct = 0.0

            # Get timestamp from index
            idx = data.index[-1]
            if hasattr(idx, "isoformat"):
                timestamp = idx.isoformat()
            else:
                timestamp = datetime.now().isoformat()

            name = self._get_ticker_name(ticker) if include_name else None

            return {
                "ticker": ticker,
                "name": name,
                "current_price": round(current_price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": volume,
                "timestamp": timestamp,
            }

        except Exception as e:
            logger.error(f"Error fetching quote for {ticker}: {e}")
            return None

    def get_technical_indicators(
        self,
        ticker: str,
        data: Optional[pd.DataFrame] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get technical indicators for a ticker.

        Args:
            ticker: Stock ticker symbol
            data: Optional pre-fetched OHLCV DataFrame to reuse upstream fetch.

        Returns:
            Dictionary with technical indicators, or None if unavailable.
        """
        try:
            if data is None:
                # Need sufficient data for all indicators (MA240 needs 240+ days)
                data = self.cache.get(ticker, days=300)

            if data is None or data.empty:
                logger.warning(f"No data found for technical analysis: {ticker}")
                return None

            # Get basic indicators from TechnicalEnricher
            indicators = self.technical_enricher.enrich(ticker, data)

            # Calculate additional moving averages
            close = data["close"]
            ma_20 = self._safe_ma(close, 20)
            ma_60 = self._safe_ma(close, 60)
            ma_120 = self._safe_ma(close, 120)
            ma_240 = self._safe_ma(close, 240)

            return {
                "ticker": ticker,
                "rsi": self._round_value(indicators.get("rsi")),
                "rsi_signal": indicators.get("rsi_signal"),
                "macd": self._round_value(indicators.get("macd")),
                "macd_signal": self._round_value(indicators.get("macd_signal")),
                "macd_histogram": self._round_value(indicators.get("macd_histogram")),
                "bb_upper": self._round_value(indicators.get("bb_upper")),
                "bb_middle": self._round_value(indicators.get("bb_middle")),
                "bb_lower": self._round_value(indicators.get("bb_lower")),
                "bb_position": indicators.get("bb_position"),
                "ma_20": self._round_value(ma_20),
                "ma_60": self._round_value(ma_60),
                "ma_120": self._round_value(ma_120),
                "ma_240": self._round_value(ma_240),
            }

        except Exception as e:
            logger.error(f"Error calculating technical indicators for {ticker}: {e}")
            return None

    def _safe_ma(self, series: pd.Series, period: int) -> Optional[float]:
        """Calculate moving average safely."""
        if len(series) < period:
            return None
        ma = series.rolling(window=period).mean()
        val = ma.iloc[-1]
        if pd.isna(val):
            return None
        return float(val)

    def _round_value(self, value: Optional[float], decimals: int = 4) -> Optional[float]:
        """Round value if not None."""
        if value is None:
            return None
        return round(value, decimals)

    def _serialize_ohlcv(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Vectorized DataFrame serialization for OHLCV response."""
        frame = data[["open", "high", "low", "close", "volume"]].copy().reset_index()
        date_col = frame.columns[0]
        parsed = pd.to_datetime(frame[date_col], errors="coerce")
        frame["date"] = parsed.dt.strftime("%Y-%m-%d")
        frame.loc[frame["date"].isna(), "date"] = frame.loc[
            frame["date"].isna(), date_col
        ].astype(str).str[:10]

        frame["open"] = frame["open"].astype(float)
        frame["high"] = frame["high"].astype(float)
        frame["low"] = frame["low"].astype(float)
        frame["close"] = frame["close"].astype(float)
        frame["volume"] = frame["volume"].fillna(0).astype(int)

        return frame[["date", "open", "high", "low", "close", "volume"]].to_dict("records")

    def get_ticker_info(self, ticker: str) -> Dict[str, Any]:
        """Get yfinance info with bounded in-memory cache (TTL + maxsize)."""
        now = datetime.now()
        cached = self._ticker_info_cache.get(ticker)
        if cached is not None:
            ts, payload = cached
            if (now - ts).total_seconds() <= self._TICKER_INFO_TTL_SECONDS:
                self._ticker_info_cache.move_to_end(ticker)
                return payload
            self._ticker_info_cache.pop(ticker, None)

        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info or {}
            self._ticker_info_cache[ticker] = (now, info)
            while len(self._ticker_info_cache) > self._TICKER_INFO_MAXSIZE:
                self._ticker_info_cache.popitem(last=False)
            return info
        except Exception:
            self._ticker_info_cache[ticker] = (now, {})
            while len(self._ticker_info_cache) > self._TICKER_INFO_MAXSIZE:
                self._ticker_info_cache.popitem(last=False)
            return {}

    def _get_ticker_name(self, ticker: str) -> Optional[str]:
        """
        Get company name for a ticker.

        Note: This is a best-effort lookup. Returns None if unavailable.
        """
        info = self.get_ticker_info(ticker)
        return info.get("shortName") or info.get("longName")


# Module-level service instance for convenience functions
_service: Optional[MarketService] = None


def _get_service() -> MarketService:
    """Get or create the default service instance."""
    global _service
    if _service is None:
        _service = MarketService()
    return _service


def get_ohlcv(ticker: str, days: int = 100) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get OHLCV data.

    Args:
        ticker: Stock ticker symbol
        days: Number of days

    Returns:
        OHLCV data dictionary or None
    """
    return _get_service().get_ohlcv(ticker, days)


def get_quote(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get current quote.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Quote dictionary or None
    """
    return _get_service().get_quote(ticker)


def get_technical_indicators(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get technical indicators.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Technical indicators dictionary or None
    """
    return _get_service().get_technical_indicators(ticker)
