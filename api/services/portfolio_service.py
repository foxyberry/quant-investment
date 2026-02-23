"""
Portfolio Service.

Business logic for portfolio management operations.
Provides CRUD operations for holdings and P&L calculations.
"""

import csv
import io
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from api.database import SessionLocal
from api.models.portfolio import Holding
from api.schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioSummary,
    SellSignal,
)
from api.services.exchange_rate_service import ExchangeRateService, get_exchange_rate_service

# Import data cache for current price retrieval
from utils.data_cache import OHLCVCache, get_cache

logger = logging.getLogger(__name__)


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

    def __init__(self):
        self._lock = threading.RLock()
        self._cache = get_cache()
        self._fx: ExchangeRateService = get_exchange_rate_service()
        self._price_cache: Dict[str, float] = {}
        self._price_cache_time: float = 0.0

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
        }

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
                return float(data["close"].iloc[-1])
        except Exception as e:
            logger.warning(f"Failed to get current price for {ticker}: {e}")
        return None

    def _get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple tickers.

        Uses a short-lived in-memory cache (PRICE_CACHE_TTL seconds)
        to deduplicate concurrent requests from the same page load.
        Fetches prices in parallel using ThreadPoolExecutor.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to current price
        """
        if not tickers:
            return {}

        with self._lock:
            now = time.monotonic()

            # Return cached prices if still fresh and all requested tickers are present
            if (now - self._price_cache_time < self.PRICE_CACHE_TTL
                    and all(t in self._price_cache for t in tickers)):
                return {t: self._price_cache[t] for t in tickers}

            prices: Dict[str, float] = {}

            # Prefer OHLCVCache batch path to avoid N independent yfinance calls.
            if hasattr(self._cache, "get_latest_prices"):
                try:
                    prices = self._cache.get_latest_prices(tickers, days=5)
                except Exception as e:
                    logger.warning(f"Batch price fetch failed; fallback to per-ticker: {e}")

            # Fallback: per-ticker parallel fetch for any missing tickers.
            missing_tickers = [t for t in tickers if t not in prices]
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
                                prices[ticker] = price
                        except Exception as e:
                            logger.warning(f"Failed to fetch price for {ticker}: {e}")

            # Update cache
            self._price_cache = prices
            self._price_cache_time = time.monotonic()
            return prices

    def _holding_to_response(
        self,
        holding: Dict[str, Any],
        current_price: Optional[float] = None
    ) -> HoldingResponse:
        """
        Convert holding dict to HoldingResponse with P&L.

        Args:
            holding: Holding data dict
            current_price: Current market price (optional)

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
            market_value = quantity * current_price
            pnl = market_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

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
            market_value=market_value,
            cost_basis=cost_basis,
            pnl=pnl,
            pnl_pct=pnl_pct,
            currency=holding.get("currency", "KRW"),
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

        prices = {}
        if with_prices and holdings_dicts:
            tickers = [h["ticker"] for h in holdings_dicts]
            prices = self._get_current_prices(tickers)

        return [
            self._holding_to_response(h, prices.get(h["ticker"]))
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
        if with_price:
            current_price = self._get_current_price(ticker)

        return self._holding_to_response(holding, current_price)

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
                existing = Holding(
                    ticker=ticker,
                    name=data.name or ticker,
                    quantity=data.quantity,
                    avg_price=data.avg_price,
                    currency=data.currency,
                    note=data.note,
                    bought_at=date.today(),
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
        return self._holding_to_response(holding, current_price)

    def update_holding(self, ticker: str, data: HoldingUpdate) -> Optional[HoldingResponse]:
        """
        Update an existing holding.

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

            if data.quantity is not None:
                row.quantity = data.quantity
            if data.avg_price is not None:
                row.avg_price = data.avg_price
            if data.name is not None:
                row.name = data.name
            if data.note is not None:
                row.note = data.note

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
        total_pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0

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

    def get_sell_signals(
        self,
        stop_loss_pct: float = None,
        take_profit_pct: float = None
    ) -> List[SellSignal]:
        """
        Get sell signals based on P&L thresholds.

        Args:
            stop_loss_pct: Stop loss threshold percentage (default: -10%)
            take_profit_pct: Take profit threshold percentage (default: +20%)

        Returns:
            List of SellSignal objects
        """
        stop_loss = stop_loss_pct if stop_loss_pct is not None else self.STOP_LOSS_PCT
        take_profit = take_profit_pct if take_profit_pct is not None else self.TAKE_PROFIT_PCT

        signals = []
        holdings = self.get_all_holdings(with_prices=True)

        for h in holdings:
            if h.pnl_pct is None or h.current_price is None:
                continue

            signal = None

            # Check stop loss
            if h.pnl_pct <= stop_loss:
                signal = SellSignal(
                    ticker=h.ticker,
                    name=h.name or h.ticker,
                    signal_type="stop_loss",
                    reason=f"Loss exceeded {stop_loss}% threshold (current: {h.pnl_pct:.1f}%)",
                    current_price=h.current_price,
                    trigger_price=h.avg_price * (1 + stop_loss / 100),
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct,
                    currency=h.currency,
                )

            # Check take profit
            elif h.pnl_pct >= take_profit:
                signal = SellSignal(
                    ticker=h.ticker,
                    name=h.name or h.ticker,
                    signal_type="take_profit",
                    reason=f"Profit reached {take_profit}% target (current: {h.pnl_pct:.1f}%)",
                    current_price=h.current_price,
                    trigger_price=h.avg_price * (1 + take_profit / 100),
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct,
                    currency=h.currency,
                )

            if signal:
                signals.append(signal)

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
