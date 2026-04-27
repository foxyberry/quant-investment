"""
Portfolio Price Service.

Handles current price fetching, daily change calculation, sector lookup,
and static metadata retrieval for tickers. Uses parallel execution and
TTL caching for efficiency.
"""

import logging
from concurrent.futures import as_completed
from typing import Dict, List, Optional

from api.services.portfolio.portfolio_base_service import PortfolioBaseService

logger = logging.getLogger(__name__)


class PortfolioPriceService(PortfolioBaseService):
    """
    Extends PortfolioBaseService with price and metadata enrichment.

    Methods here are internal helpers used by higher-level service layers.
    """

    def _get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None if unavailable
        """
        try:
            data = self._cache.get(ticker, days=5, force_refresh=False)
            if data is not None and not data.empty:
                # Drop NaN close rows (e.g. pre-market placeholder for today)
                valid = data["close"].dropna()
                if valid.empty:
                    return None
                price = float(valid.iloc[-1])
                return self._sanitize_float(price, default=None)
        except Exception as e:
            logger.warning(f"Failed to get current price for {ticker}: {e}")
        return None

    def _get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple tickers.

        Uses TTLCache (PRICE_CACHE_TTL seconds per ticker) to deduplicate
        concurrent requests from the same page load.
        Fetches prices in parallel using ThreadPoolExecutor.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to current price
        """
        if not tickers:
            return {}

        from utils.ttl_cache import _MISSING

        # Check which tickers already have a fresh cache entry.
        prices: Dict[str, float] = {}
        uncached: List[str] = []
        for t in tickers:
            raw = self._price_cache._get_raw(t)
            if raw is not _MISSING:
                prices[t] = raw  # type: ignore[assignment]
            else:
                uncached.append(t)

        if not uncached:
            return prices

        # Prefer OHLCVCache batch path to avoid N independent yfinance calls.
        batch_prices: Dict[str, float] = {}
        if hasattr(self._cache, "get_latest_prices"):
            try:
                batch_prices = self._cache.get_latest_prices(uncached, days=5)
            except Exception as e:
                logger.warning(f"Batch price fetch failed; fallback to per-ticker: {e}")

        # Store batch results in TTLCache.
        for ticker, price in batch_prices.items():
            self._price_cache.set(ticker, price)
            prices[ticker] = price

        # Fallback: per-ticker parallel fetch for any still-missing tickers.
        missing_tickers = [t for t in uncached if t not in batch_prices]
        if missing_tickers:
            futures = {
                self._executor.submit(self._get_current_price, t): t
                for t in missing_tickers
            }
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    price = future.result()
                    if price is not None:
                        self._price_cache.set(ticker, price)
                        prices[ticker] = price
                except Exception as e:
                    logger.warning(f"Failed to fetch price for {ticker}: {e}")

        return prices

    def _get_daily_changes(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get daily price change percentages for multiple tickers.

        Computes (last_close - prev_close) / prev_close * 100
        from OHLCV cache data.  Results are cached per-ticker for
        CHANGE_CACHE_TTL seconds.

        Returns:
            Dict mapping ticker to change_pct (e.g. -1.5 for -1.5%)
        """
        if not tickers:
            return {}

        from utils.ttl_cache import _MISSING

        changes: Dict[str, float] = {}
        uncached: List[str] = []
        for t in tickers:
            raw = self._change_cache._get_raw(t)
            if raw is not _MISSING:
                if raw is not None:
                    changes[t] = raw  # type: ignore[assignment]
            else:
                uncached.append(t)

        if not uncached:
            return changes

        def _calc_change(ticker: str) -> Optional[float]:
            try:
                data = self._cache.get(ticker, days=5, force_refresh=False)
                if data is not None and len(data) >= 2:
                    cur = self._sanitize_float(float(data["close"].iloc[-1]), default=None)
                    prev = self._sanitize_float(float(data["close"].iloc[-2]), default=None)
                    if cur is not None and prev is not None and prev > 0:
                        return self._sanitize_float((cur - prev) / prev * 100, default=None)
            except Exception:
                pass
            return None

        futures = {self._executor.submit(_calc_change, t): t for t in uncached}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                result = future.result()
                self._change_cache.set(ticker, result)
                if result is not None:
                    changes[ticker] = result
            except Exception:
                pass

        return changes

    def _get_sectors(self, tickers: List[str]) -> Dict[str, Optional[str]]:
        """
        Get sector classifications for multiple tickers.

        For Korean stocks (.KS, .KQ): uses pykrx via SectorFetcher batch lookup.
        For US stocks (no dot suffix): uses yfinance Ticker.info["sector"],
        cached per-ticker for SECTOR_CACHE_TTL seconds.
        Best-effort: returns None for any ticker whose sector cannot be resolved.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to sector name (or None)
        """
        if not tickers:
            return {}

        from utils.ttl_cache import _MISSING

        sectors: Dict[str, Optional[str]] = {}
        uncached: List[str] = []
        for t in tickers:
            raw = self._sector_cache._get_raw(t)
            if raw is not _MISSING:
                sectors[t] = raw  # type: ignore[assignment]
            else:
                uncached.append(t)

        if not uncached:
            return sectors

        # Partition uncached tickers by market
        kr_kospi: List[str] = []
        kr_kosdaq: List[str] = []
        us_tickers: List[str] = []

        for t in uncached:
            if t.endswith(".KS"):
                kr_kospi.append(t)
            elif t.endswith(".KQ"):
                kr_kosdaq.append(t)
            else:
                us_tickers.append(t)

        # Korean stocks: batch lookup via SectorFetcher
        try:
            from screener.sector_fetcher import get_sector_fetcher
            fetcher = get_sector_fetcher()

            if kr_kospi:
                kospi_map = fetcher.get_all_sector_classifications("KOSPI")
                for t in kr_kospi:
                    sector = kospi_map.get(t)
                    self._sector_cache.set(t, sector)
                    sectors[t] = sector

            if kr_kosdaq:
                kosdaq_map = fetcher.get_all_sector_classifications("KOSDAQ")
                for t in kr_kosdaq:
                    sector = kosdaq_map.get(t)
                    self._sector_cache.set(t, sector)
                    sectors[t] = sector
        except Exception as e:
            logger.warning(f"Failed to fetch Korean sector data: {e}")
            for t in kr_kospi + kr_kosdaq:
                sectors[t] = None

        # US stocks: per-ticker yfinance lookup in parallel, cached individually
        if us_tickers:
            def _fetch_us_sector(ticker: str) -> Optional[str]:
                try:
                    import yfinance as yf
                    return yf.Ticker(ticker).info.get("sector")
                except Exception:
                    return None

            futures = {
                self._executor.submit(_fetch_us_sector, t): t
                for t in us_tickers
            }
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    sector = future.result()
                    self._sector_cache.set(ticker, sector)
                    sectors[ticker] = sector
                except Exception as e:
                    logger.warning(f"Failed to fetch sector for {ticker}: {e}")
                    sectors[ticker] = None

        return sectors

    @staticmethod
    def _fetch_static_metadata(ticker: str) -> Dict[str, Optional[str]]:
        """Fetch static metadata (name/sector/industry/country/exchange) for a ticker. Called once at creation."""
        result: Dict[str, Optional[str]] = {
            "name": None, "sector": None, "industry": None, "country": None, "exchange": None,
        }
        try:
            if ticker.endswith(".KS") or ticker.endswith(".KQ"):
                # Korean stock
                suffix = ticker[-3:]  # .KS or .KQ
                result["country"] = "South Korea"
                result["exchange"] = "KOSPI" if suffix == ".KS" else "KOSDAQ"
                # Name + Sector from master CSV via KospiListFetcher
                try:
                    from screener.kospi_fetcher import KospiListFetcher
                    kf = KospiListFetcher(use_cache=True)
                    symbols = (
                        kf.get_kospi_symbols()
                        if suffix == ".KS"
                        else kf.get_kosdaq_symbols()
                    )
                    for s in symbols:
                        if s["symbol"] == ticker:
                            result["name"] = s["name"]
                            result["sector"] = s.get("sector") or None
                            break
                except Exception as e:
                    logger.warning(f"Failed to fetch KR metadata for {ticker}: {e}")
                # Fallback name from pykrx if master CSV didn't have it
                if not result["name"]:
                    try:
                        from pykrx import stock as pykrx_stock
                        code = ticker.split(".")[0]
                        result["name"] = pykrx_stock.get_market_ticker_name(code) or None
                    except Exception:
                        pass
                # Fallback sector from SectorFetcher if not found above
                if not result["sector"]:
                    try:
                        from screener.sector_fetcher import get_sector_fetcher
                        sf = get_sector_fetcher()
                        market = "KOSPI" if suffix == ".KS" else "KOSDAQ"
                        sector_map = sf.get_all_sector_classifications(market)
                        result["sector"] = sector_map.get(ticker)
                    except Exception as e:
                        logger.warning(f"Failed to fetch KR sector for {ticker}: {e}")
            else:
                # US/Other: yfinance
                try:
                    import yfinance as yf
                    info = yf.Ticker(ticker).info
                    result["name"] = info.get("shortName") or info.get("longName")
                    result["sector"] = info.get("sector")
                    result["industry"] = info.get("industry")
                    result["country"] = info.get("country")
                    result["exchange"] = info.get("exchange")
                except Exception as e:
                    logger.warning(f"Failed to fetch metadata for {ticker}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error fetching metadata for {ticker}: {e}")
        return result
