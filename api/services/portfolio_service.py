"""
Portfolio Service.

Business logic for portfolio management operations.
Provides CRUD operations for holdings and P&L calculations.
"""

import csv
import io
import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from api.database import SessionLocal
from api.models.portfolio import Holding, Trade
from api.schemas.portfolio import (
    AdditionalPurchaseRequest,
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioSummary,
    SellSignal,
    SellRecordCreate,
    TradeResponse,
    TradeHistoryResponse,
)
from api.services.exchange_rate_service import ExchangeRateService, get_exchange_rate_service

# Import data cache for current price retrieval
from utils.data_cache import OHLCVCache, get_cache
from utils.ttl_cache import TTLCache

logger = logging.getLogger(__name__)

# Timeout for each enrichment future in get_all_holdings (seconds).
ENRICHMENT_TIMEOUT_SECONDS = 30


class PortfolioService:
    """
    Portfolio service for managing holdings.

    Provides methods for CRUD operations on holdings,
    P&L calculations, and sell signal detection.
    """

    # Default sell signal thresholds
    STOP_LOSS_PCT = -10.0  # -10% triggers stop loss
    TAKE_PROFIT_PCT = 20.0  # +20% triggers take profit

    # Price cache TTL in seconds (deduplicates concurrent requests)
    PRICE_CACHE_TTL = 60
    # Sector cache TTL (1 hour – sectors change infrequently)
    SECTOR_CACHE_TTL = 3600
    # Daily change cache TTL (same as price)
    CHANGE_CACHE_TTL = 60

    def __init__(self):
        self._cache = get_cache()
        self._fx: ExchangeRateService = get_exchange_rate_service()
        self._price_cache: TTLCache[float] = TTLCache(self.PRICE_CACHE_TTL, max_size=512)
        self._sector_cache: TTLCache[Optional[str]] = TTLCache(self.SECTOR_CACHE_TTL, max_size=512)
        self._change_cache: TTLCache[Optional[float]] = TTLCache(self.CHANGE_CACHE_TTL, max_size=512)

    @staticmethod
    def _convert_to_base(
        amount: float,
        currency: str,
        base_currency: str,
        rates: Dict[str, float],
    ) -> float:
        """Convert an amount from currency to base_currency using rates(base->currency)."""
        from_currency = (currency or base_currency).upper()
        base = base_currency.upper()
        if from_currency == base:
            return amount
        rate = rates.get(from_currency)
        if rate is None or rate <= 0:
            raise ValueError(f"Missing exchange rate for currency: {from_currency}")
        return amount / rate

    @staticmethod
    def _row_to_dict(row: Holding) -> Dict[str, Any]:
        """Convert ORM Holding to dict for _holding_to_response()."""
        return {
            "ticker": row.ticker,
            "name": row.name,
            "quantity": row.quantity,
            "avg_price": row.avg_price,
            "currency": row.currency,
            "note": row.note,
            "bought_at": row.bought_at,
            "sector": row.sector,
            "industry": row.industry,
            "country": row.country,
            "exchange": row.exchange,
        }

    @staticmethod
    def _sanitize_float(value: Optional[float], default: Optional[float] = 0.0) -> Optional[float]:
        """Return *default* if value is NaN/Inf, else value. None passes through."""
        if value is None:
            return None
        if math.isnan(value) or math.isinf(value):
            return default if default is not None else None
        return value

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
                price = float(data["close"].iloc[-1])
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
            with ThreadPoolExecutor(max_workers=min(len(missing_tickers), 8)) as executor:
                futures = {
                    executor.submit(self._get_current_price, t): t
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

        with ThreadPoolExecutor(max_workers=min(len(uncached), 8)) as executor:
            futures = {executor.submit(_calc_change, t): t for t in uncached}
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

            with ThreadPoolExecutor(max_workers=min(len(us_tickers), 8)) as executor:
                futures = {
                    executor.submit(_fetch_us_sector, t): t
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
        """Fetch static metadata (sector/industry/country/exchange) for a ticker. Called once at creation."""
        result = {"sector": None, "industry": None, "country": None, "exchange": None}
        try:
            if ticker.endswith(".KS") or ticker.endswith(".KQ"):
                # Korean stock
                suffix = ticker[-3:]  # .KS or .KQ
                result["country"] = "South Korea"
                result["exchange"] = "KOSPI" if suffix == ".KS" else "KOSDAQ"
                # Sector from SectorFetcher
                try:
                    from screener.sector_fetcher import get_sector_fetcher
                    fetcher = get_sector_fetcher()
                    market = "KOSPI" if suffix == ".KS" else "KOSDAQ"
                    sector_map = fetcher.get_all_sector_classifications(market)
                    result["sector"] = sector_map.get(ticker)
                except Exception as e:
                    logger.warning(f"Failed to fetch KR sector for {ticker}: {e}")
            else:
                # US/Other: yfinance
                try:
                    import yfinance as yf
                    info = yf.Ticker(ticker).info
                    result["sector"] = info.get("sector")
                    result["industry"] = info.get("industry")
                    result["country"] = info.get("country")
                    result["exchange"] = info.get("exchange")
                except Exception as e:
                    logger.warning(f"Failed to fetch metadata for {ticker}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error fetching metadata for {ticker}: {e}")
        return result

    def _holding_to_response(
        self,
        holding: Dict[str, Any],
        current_price: Optional[float] = None,
        sector: Optional[str] = None,
        change_pct: Optional[float] = None,
    ) -> HoldingResponse:
        """
        Convert holding dict to HoldingResponse with P&L.

        Args:
            holding: Holding data dict
            current_price: Current market price (optional)
            sector: Stock sector classification (optional)

        Returns:
            HoldingResponse with calculated fields
        """
        quantity = holding.get("quantity", 0)
        avg_price = holding.get("avg_price", 0)
        cost_basis = quantity * avg_price

        market_value = None
        pnl = None
        pnl_pct = None

        if current_price is not None:
            market_value = self._sanitize_float(quantity * current_price)
            pnl = self._sanitize_float(market_value - cost_basis if market_value is not None else None)
            pnl_pct = self._sanitize_float(
                (pnl / cost_basis * 100) if cost_basis > 0 and pnl is not None else 0
            )

        # Parse bought_at date
        bought_at = holding.get("bought_at")
        if isinstance(bought_at, str):
            try:
                bought_at = date.fromisoformat(bought_at)
            except ValueError:
                bought_at = None

        return HoldingResponse(
            ticker=holding.get("ticker", ""),
            name=holding.get("name"),
            quantity=quantity,
            avg_price=avg_price,
            current_price=current_price,
            change_pct=change_pct,
            market_value=market_value,
            cost_basis=cost_basis,
            pnl=pnl,
            pnl_pct=pnl_pct,
            currency=holding.get("currency", "KRW"),
            sector=sector,
            industry=holding.get("industry"),
            country=holding.get("country"),
            exchange=holding.get("exchange"),
            bought_at=bought_at,
            note=holding.get("note")
        )

    def get_all_holdings(self, with_prices: bool = True) -> List[HoldingResponse]:
        """
        Get all holdings with optional current prices.

        Args:
            with_prices: Whether to fetch current prices

        Returns:
            List of HoldingResponse objects
        """
        db = SessionLocal()
        try:
            rows = db.query(Holding).all()
            holdings_dicts = [self._row_to_dict(r) for r in rows]
        finally:
            db.close()

        prices: Dict[str, float] = {}
        changes: Dict[str, float] = {}
        if with_prices and holdings_dicts:
            tickers = [h["ticker"] for h in holdings_dicts]

            # Run price and change enrichment in parallel (sector is now in DB).
            with ThreadPoolExecutor(max_workers=2) as outer:
                f_prices = outer.submit(self._get_current_prices, tickers)
                f_changes = outer.submit(self._get_daily_changes, tickers)

                prices = f_prices.result(timeout=ENRICHMENT_TIMEOUT_SECONDS)
                try:
                    changes = f_changes.result(timeout=ENRICHMENT_TIMEOUT_SECONDS)
                except Exception as e:
                    logger.warning(f"Daily change enrichment failed: {e}")

        return [
            self._holding_to_response(
                h,
                prices.get(h["ticker"]),
                sector=h.get("sector"),
                change_pct=changes.get(h["ticker"]),
            )
            for h in holdings_dicts
        ]

    def get_holding(self, ticker: str, with_price: bool = True) -> Optional[HoldingResponse]:
        """
        Get a single holding by ticker.

        Args:
            ticker: Stock ticker symbol
            with_price: Whether to fetch current price

        Returns:
            HoldingResponse or None if not found
        """
        db = SessionLocal()
        try:
            row = db.get(Holding, ticker)
            if not row:
                return None
            holding = self._row_to_dict(row)
        finally:
            db.close()

        current_price = None
        change_pct = None
        if with_price:
            current_price = self._get_current_price(ticker)
            try:
                changes = self._get_daily_changes([ticker])
                change_pct = changes.get(ticker)
            except Exception as e:
                logger.warning(f"Daily change enrichment failed for {ticker}: {e}")

        return self._holding_to_response(holding, current_price, sector=holding.get("sector"), change_pct=change_pct)

    def add_holding(self, data: HoldingCreate) -> HoldingResponse:
        """
        Add a new holding or add to existing position.

        If the ticker already exists, calculates new average price.

        Args:
            data: HoldingCreate schema with holding details

        Returns:
            Created/updated HoldingResponse
        """
        ticker = data.ticker
        db = SessionLocal()
        try:
            existing = db.get(Holding, ticker)

            if existing:
                # Add to existing position - calculate new average price
                old_cost = existing.quantity * existing.avg_price
                new_cost = data.quantity * data.avg_price
                total_quantity = existing.quantity + data.quantity
                new_avg_price = (old_cost + new_cost) / total_quantity if total_quantity > 0 else 0

                existing.quantity = total_quantity
                existing.avg_price = new_avg_price
                if data.name:
                    existing.name = data.name
                if data.note:
                    existing.note = data.note
                existing.currency = data.currency

                logger.info(f"Updated holding: {ticker} (qty: {total_quantity}, avg: {new_avg_price:.2f})")
            else:
                # Create new holding
                meta = self._fetch_static_metadata(ticker)
                existing = Holding(
                    ticker=ticker,
                    name=data.name or ticker,
                    quantity=data.quantity,
                    avg_price=data.avg_price,
                    currency=data.currency,
                    note=data.note,
                    bought_at=date.today(),
                    sector=meta.get("sector"),
                    industry=meta.get("industry"),
                    country=meta.get("country"),
                    exchange=meta.get("exchange"),
                )
                db.add(existing)
                logger.info(f"Added holding: {ticker} (qty: {data.quantity}, avg: {data.avg_price:.2f})")

            db.commit()
            db.refresh(existing)
            holding = self._row_to_dict(existing)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        current_price = self._get_current_price(ticker)
        return self._holding_to_response(holding, current_price, sector=holding.get("sector"), change_pct=None)

    def update_holding(self, ticker: str, data: HoldingUpdate) -> Optional[HoldingResponse]:
        """
        Update an existing holding.

        Records an ADJUST trade when quantity or avg_price changes.

        Args:
            ticker: Stock ticker symbol
            data: HoldingUpdate schema with fields to update

        Returns:
            Updated HoldingResponse or None if not found
        """
        db = SessionLocal()
        try:
            row = db.get(Holding, ticker)
            if not row:
                return None

            # Snapshot before update for ADJUST trade recording
            old_qty = row.quantity
            old_avg = row.avg_price
            qty_changed = data.quantity is not None and data.quantity != old_qty
            price_changed = data.avg_price is not None and data.avg_price != old_avg

            if data.quantity is not None:
                row.quantity = data.quantity
            if data.avg_price is not None:
                row.avg_price = data.avg_price
            if data.name is not None:
                row.name = data.name
            if data.note is not None:
                row.note = data.note

            # Record ADJUST trade if quantity or price changed
            if qty_changed or price_changed:
                trade = Trade(
                    ticker=ticker,
                    name=row.name,
                    trade_type="ADJUST",
                    quantity=row.quantity,
                    price=row.avg_price,
                    fee=0,
                    realized_pnl=None,
                    avg_price_at_trade=old_avg,
                    currency=row.currency,
                    note=f"Manual adjust: {old_qty}@{old_avg:.2f} -> {row.quantity}@{row.avg_price:.2f}",
                    traded_at=date.today(),
                )
                db.add(trade)

            db.commit()
            db.refresh(row)
            holding = self._row_to_dict(row)
            logger.info(f"Updated holding: {ticker}")
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        current_price = self._get_current_price(ticker)
        return self._holding_to_response(holding, current_price)

    def add_purchase(self, ticker: str, data: AdditionalPurchaseRequest) -> Optional[HoldingResponse]:
        """
        Record an additional purchase for an existing holding.

        Recalculates the average price and records a BUY trade.

        Args:
            ticker: Stock ticker symbol
            data: AdditionalPurchaseRequest with purchase details

        Returns:
            Updated HoldingResponse or None if not found
        """
        db = SessionLocal()
        try:
            row = db.get(Holding, ticker)
            if not row:
                return None

            old_qty = row.quantity
            old_avg = row.avg_price

            # Recalculate average price
            total_cost = old_qty * old_avg + data.quantity * data.price
            new_qty = old_qty + data.quantity
            new_avg = total_cost / new_qty if new_qty > 0 else 0

            row.quantity = new_qty
            row.avg_price = new_avg

            # Record BUY trade
            trade = Trade(
                ticker=ticker,
                name=row.name,
                trade_type="BUY",
                quantity=data.quantity,
                price=data.price,
                fee=data.fee,
                realized_pnl=None,
                avg_price_at_trade=old_avg,
                currency=row.currency,
                note=data.note,
                traded_at=data.traded_at or date.today(),
            )
            db.add(trade)

            db.commit()
            db.refresh(row)
            holding = self._row_to_dict(row)
            logger.info(
                f"Additional purchase {ticker}: +{data.quantity}@{data.price:.2f}, "
                f"new avg: {new_avg:.2f}, total qty: {new_qty}"
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        current_price = self._get_current_price(ticker)
        return self._holding_to_response(holding, current_price)

    def remove_holding(self, ticker: str) -> bool:
        """
        Remove a holding.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if removed, False if not found
        """
        db = SessionLocal()
        try:
            row = db.get(Holding, ticker)
            if not row:
                return False
            db.delete(row)
            db.commit()
            logger.info(f"Removed holding: {ticker}")
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_summary(self, base_currency: Optional[str] = None) -> PortfolioSummary:
        """
        Get portfolio summary with total P&L.

        Returns:
            PortfolioSummary with aggregated metrics
        """
        holdings = self.get_all_holdings(with_prices=True)

        total_investment = 0.0
        total_market_value = 0.0

        # Determine primary currency (most common) for default summary currency
        currencies = [h.currency for h in holdings]
        primary_currency = max(set(currencies), key=currencies.count) if currencies else "KRW"

        target_currency = (base_currency or primary_currency).upper()
        fx_rates: Dict[str, float] = {}
        if base_currency:
            fx_payload = self._fx.get_rates(base=target_currency)
            fx_rates = fx_payload.get("rates", {})

        for h in holdings:
            investment = h.cost_basis
            market_value = h.market_value if h.market_value is not None else h.cost_basis

            if base_currency:
                investment = self._convert_to_base(
                    amount=investment,
                    currency=h.currency,
                    base_currency=target_currency,
                    rates=fx_rates,
                )
                market_value = self._convert_to_base(
                    amount=market_value,
                    currency=h.currency,
                    base_currency=target_currency,
                    rates=fx_rates,
                )

            total_investment += investment
            total_market_value += market_value

        total_pnl = total_market_value - total_investment
        total_pnl_pct = self._sanitize_float(
            (total_pnl / total_investment * 100) if total_investment > 0 else 0,
            default=0.0,
        )

        return PortfolioSummary(
            total_investment=total_investment,
            total_market_value=total_market_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            holdings_count=len(holdings),
            currency=target_currency,
            last_updated=datetime.now()
        )

    def import_from_csv(self, csv_content: str, mode: str = "merge") -> Dict[str, Any]:
        """
        Import holdings from CSV content.

        Args:
            csv_content: CSV string with headers
            mode: "merge" (upsert) or "replace" (clear first)

        Returns:
            Dict with imported, updated, skipped counts and errors list
        """
        errors = []
        imported = 0
        updated = 0

        reader = csv.DictReader(io.StringIO(csv_content))
        fieldnames = reader.fieldnames or []
        lower_fields = [f.strip().lower() for f in fieldnames]

        required = {"ticker", "quantity", "avg_price"}
        if not required.issubset(set(lower_fields)):
            missing = required - set(lower_fields)
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        # Build field mapping (handle case-insensitive headers)
        field_map = {}
        for original, lower in zip(fieldnames, lower_fields):
            field_map[lower] = original

        valid_rows = []
        for row_num, row in enumerate(reader, start=2):  # row 1 is header
            ticker_val = row.get(field_map["ticker"], "").strip()
            qty_val = row.get(field_map["quantity"], "").strip()
            price_val = row.get(field_map["avg_price"], "").strip()

            if not ticker_val:
                errors.append({"row": row_num, "ticker": None, "reason": "Empty ticker"})
                continue

            try:
                quantity = int(qty_val)
                if quantity <= 0:
                    raise ValueError("must be > 0")
            except (ValueError, TypeError):
                errors.append({"row": row_num, "ticker": ticker_val, "reason": f"Invalid quantity: {qty_val}"})
                continue

            try:
                avg_price = float(price_val)
                if avg_price <= 0:
                    raise ValueError("must be > 0")
            except (ValueError, TypeError):
                errors.append({"row": row_num, "ticker": ticker_val, "reason": f"Invalid avg_price: {price_val}"})
                continue

            parsed = {
                "ticker": ticker_val,
                "quantity": quantity,
                "avg_price": avg_price,
                "name": row.get(field_map.get("name", ""), "").strip() or ticker_val,
                "currency": row.get(field_map.get("currency", ""), "").strip() or "KRW",
                "note": row.get(field_map.get("note", ""), "").strip() or None,
                "bought_at": row.get(field_map.get("bought_at", ""), "").strip() or None,
            }
            valid_rows.append(parsed)

        db = SessionLocal()
        try:
            if mode == "replace":
                db.query(Holding).delete()

            existing_tickers = {
                row[0] for row in db.query(Holding.ticker).all()
            }

            for parsed in valid_rows:
                ticker = parsed["ticker"]
                bought_at_val = parsed["bought_at"]
                bought_at_date = None
                if bought_at_val:
                    try:
                        bought_at_date = date.fromisoformat(bought_at_val)
                    except (ValueError, TypeError):
                        bought_at_date = None

                if ticker in existing_tickers and mode == "merge":
                    row = db.get(Holding, ticker)
                    existing_bought_at = row.bought_at
                    row.name = parsed["name"]
                    row.quantity = parsed["quantity"]
                    row.avg_price = parsed["avg_price"]
                    row.currency = parsed["currency"]
                    row.note = parsed["note"]
                    # Preserve existing bought_at if CSV didn't provide one
                    if bought_at_date:
                        row.bought_at = bought_at_date
                    elif existing_bought_at:
                        pass  # keep existing
                    updated += 1
                else:
                    new_row = Holding(
                        ticker=ticker,
                        name=parsed["name"],
                        quantity=parsed["quantity"],
                        avg_price=parsed["avg_price"],
                        currency=parsed["currency"],
                        note=parsed["note"],
                        bought_at=bought_at_date or date.today(),
                    )
                    db.merge(new_row)
                    existing_tickers.add(ticker)
                    imported += 1

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        logger.info(f"CSV import: imported={imported}, updated={updated}, skipped={len(errors)}")

        # Backfill metadata for newly imported holdings in background
        if imported > 0:
            import threading

            def _backfill_csv_imports():
                db2 = SessionLocal()
                try:
                    null_rows = db2.query(Holding).filter(Holding.sector.is_(None)).all()
                    for row in null_rows:
                        meta = self._fetch_static_metadata(row.ticker)
                        row.sector = meta.get("sector")
                        row.industry = meta.get("industry")
                        row.country = meta.get("country")
                        row.exchange = meta.get("exchange")
                    if null_rows:
                        db2.commit()
                        logger.info(f"Backfilled metadata for {len(null_rows)} CSV-imported holdings")
                except Exception as e:
                    db2.rollback()
                    logger.warning(f"CSV import metadata backfill failed: {e}")
                finally:
                    db2.close()

            threading.Thread(target=_backfill_csv_imports, daemon=True).start()

        return {
            "imported": imported,
            "updated": updated,
            "skipped": len(errors),
            "errors": errors,
        }

    def export_to_csv(self) -> str:
        """
        Export all holdings as CSV string.

        Returns:
            CSV string with header and data rows
        """
        db = SessionLocal()
        try:
            rows = db.query(Holding).all()
            holdings_dicts = [self._row_to_dict(r) for r in rows]
        finally:
            db.close()

        output = io.StringIO()
        columns = ["ticker", "quantity", "avg_price", "name", "currency", "note", "bought_at"]
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()

        for holding in holdings_dicts:
            row = {col: holding.get(col, "") for col in columns}
            if row["note"] is None:
                row["note"] = ""
            if isinstance(row["bought_at"], date):
                row["bought_at"] = row["bought_at"].isoformat()
            writer.writerow(row)

        return output.getvalue()

    def record_sell(self, data: SellRecordCreate) -> TradeResponse:
        """Record a manual sell and update the holding accordingly."""
        db = SessionLocal()
        try:
            holding = db.get(Holding, data.ticker)
            if not holding:
                raise ValueError(f"Holding not found: {data.ticker}")
            if data.quantity > holding.quantity:
                raise ValueError(
                    f"Sell quantity ({data.quantity}) exceeds holding ({holding.quantity})"
                )

            avg_price = holding.avg_price
            total_cost = data.fee + data.tax
            realized_pnl = (data.price - avg_price) * data.quantity - total_cost

            trade = Trade(
                ticker=data.ticker,
                name=holding.name,
                trade_type="SELL",
                quantity=data.quantity,
                price=data.price,
                fee=data.fee,
                tax=data.tax,
                realized_pnl=realized_pnl,
                avg_price_at_trade=avg_price,
                currency=holding.currency,
                note=data.note,
                traded_at=data.traded_at,
            )
            db.add(trade)

            remaining = holding.quantity - data.quantity
            if remaining == 0:
                db.delete(holding)
                logger.info(f"Sold all of {data.ticker} — holding removed")
            else:
                holding.quantity = remaining
                logger.info(
                    f"Partial sell {data.ticker}: {data.quantity} shares, "
                    f"{remaining} remaining"
                )

            db.commit()
            db.refresh(trade)

            return TradeResponse(
                id=trade.id,
                ticker=trade.ticker,
                name=trade.name,
                trade_type=trade.trade_type,
                quantity=trade.quantity,
                price=trade.price,
                fee=trade.fee or 0,
                tax=trade.tax or 0,
                realized_pnl=trade.realized_pnl,
                avg_price_at_trade=trade.avg_price_at_trade,
                currency=trade.currency,
                note=trade.note,
                traded_at=trade.traded_at,
                created_at=trade.created_at,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_trade_history(
        self, ticker: Optional[str] = None
    ) -> TradeHistoryResponse:
        """Get trade history, optionally filtered by ticker."""
        db = SessionLocal()
        try:
            query = db.query(Trade).order_by(Trade.traded_at.desc(), Trade.id.desc())
            if ticker:
                query = query.filter(Trade.ticker == ticker)
            rows = query.all()

            # Fallback: fill name from Holding for legacy rows missing name
            nameless = [r.ticker for r in rows if not r.name]
            name_map: Dict[str, str] = {}
            if nameless:
                holdings = db.query(Holding.ticker, Holding.name).filter(
                    Holding.ticker.in_(list(set(nameless)))
                ).all()
                name_map = {h.ticker: h.name for h in holdings if h.name}
        finally:
            db.close()

        trades = [
            TradeResponse(
                id=r.id,
                ticker=r.ticker,
                name=r.name or name_map.get(r.ticker),
                trade_type=r.trade_type,
                quantity=r.quantity,
                price=r.price,
                fee=r.fee or 0,
                tax=r.tax or 0,
                realized_pnl=r.realized_pnl,
                avg_price_at_trade=r.avg_price_at_trade,
                currency=r.currency,
                note=r.note,
                traded_at=r.traded_at,
                created_at=r.created_at,
            )
            for r in rows
        ]
        total_pnl = sum(t.realized_pnl or 0 for t in trades)
        return TradeHistoryResponse(
            trades=trades,
            total_realized_pnl=total_pnl,
            trade_count=len(trades),
        )

    def get_sell_signals(
        self,
        stop_loss_pct: float = None,
        take_profit_pct: float = None
    ) -> List[SellSignal]:
        """
        Get sell signals by evaluating per-holding sell rules.

        Holdings with DB-persisted rules are evaluated against those rules.
        Holdings without rules fall back to global thresholds.

        Args:
            stop_loss_pct: Fallback stop loss threshold percentage (default: -10%)
            take_profit_pct: Fallback take profit threshold percentage (default: +20%)

        Returns:
            List of SellSignal objects
        """
        from api.services.sell_rule_service import get_sell_rule_service

        stop_loss = stop_loss_pct if stop_loss_pct is not None else self.STOP_LOSS_PCT
        take_profit = take_profit_pct if take_profit_pct is not None else self.TAKE_PROFIT_PCT

        signals = []
        holdings = self.get_all_holdings(with_prices=True)

        # Evaluate DB-persisted rules (read-only: no state mutation from GET)
        svc = get_sell_rule_service()
        rule_results = svc.evaluate_all(persist=False)
        # Use DB to determine which tickers have rules (includes already-triggered)
        tickers_with_rules = svc.get_tickers_with_rules()

        for res in rule_results:
            if not res.triggered:
                continue
            # Find matching holding for metadata
            h = next((h for h in holdings if h.ticker == res.ticker), None)
            if not h or h.current_price is None:
                continue
            signals.append(SellSignal(
                ticker=res.ticker,
                name=h.name or h.ticker,
                signal_type=res.rule_type,
                reason=res.reason or f"{res.rule_type} triggered",
                current_price=h.current_price,
                avg_price=h.avg_price,
                pnl_pct=h.pnl_pct or 0.0,
                currency=h.currency,
                rule_id=res.rule_id,
            ))

        # Fallback: global thresholds for holdings without any DB rules
        for h in holdings:
            if h.ticker in tickers_with_rules:
                continue
            if h.pnl_pct is None or h.current_price is None:
                continue

            if h.pnl_pct <= stop_loss:
                signals.append(SellSignal(
                    ticker=h.ticker,
                    name=h.name or h.ticker,
                    signal_type="stop_loss",
                    reason=f"Loss exceeded {stop_loss}% threshold (current: {h.pnl_pct:.1f}%)",
                    current_price=h.current_price,
                    trigger_price=h.avg_price * (1 + stop_loss / 100),
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct,
                    currency=h.currency,
                ))
            elif h.pnl_pct >= take_profit:
                signals.append(SellSignal(
                    ticker=h.ticker,
                    name=h.name or h.ticker,
                    signal_type="take_profit",
                    reason=f"Profit reached {take_profit}% target (current: {h.pnl_pct:.1f}%)",
                    current_price=h.current_price,
                    trigger_price=h.avg_price * (1 + take_profit / 100),
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct,
                    currency=h.currency,
                ))

        return signals


# Singleton instance
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """
    Get or create the portfolio service singleton.

    Returns:
        PortfolioService instance
    """
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service
