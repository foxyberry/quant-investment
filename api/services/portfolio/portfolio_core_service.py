"""
Portfolio Core Service.

Handles holdings CRUD operations, P&L response building,
portfolio summary, CSV import/export, and cache invalidation.

Inherits price enrichment from PortfolioPriceService.
"""

import csv
import io
import logging
import threading
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from api.database import SessionLocal
from api.models.portfolio import Holding, SellRule, Trade
from api.models.portfolio_alert import PortfolioAlertHistory
from api.schemas.portfolio import (
    AdditionalPurchaseRequest,
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioSummary,
)
from api.services.portfolio.portfolio_price_service import PortfolioPriceService

logger = logging.getLogger(__name__)

# Re-export exceptions and constants so callers can import from here.
from api.services.portfolio.portfolio_base_service import (
    PresetNotFoundError,
    PresetInactiveError,
    ENRICHMENT_TIMEOUT_SECONDS,
)


class PortfolioCoreService(PortfolioPriceService):
    """
    Holdings CRUD, P&L calculations, summary, and CSV import/export.

    Price and sector enrichment is inherited from PortfolioPriceService.
    """

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

            # Prices first (warms the OHLCV parquet cache), then changes.
            # Running them in parallel caused a race: _get_daily_changes would
            # read the cache before _get_current_prices had finished writing it,
            # resulting in null change_pct for most holdings.
            prices = self._get_current_prices(tickers)
            try:
                changes = self._get_daily_changes(tickers)
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
                    name=data.name or meta.get("name") or ticker,
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
        return self.build_summary(holdings, base_currency=base_currency)

    def build_summary(
        self,
        holdings: List[HoldingResponse],
        base_currency: Optional[str] = None,
    ) -> PortfolioSummary:
        """
        Build portfolio summary from a pre-fetched holdings list.

        Useful when callers already loaded holdings with prices and want to
        avoid a second fetch cycle.
        """
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

            ticker_val = ticker_val.upper()
            ticker_error = self._validate_ticker(ticker_val)
            if ticker_error:
                errors.append({"row": row_num, "ticker": ticker_val, "reason": ticker_error})
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
                # A replace import establishes a new portfolio snapshot.
                # Old alert history would refer to the previous holdings set and
                # becomes misleading for both UI history and daily dedup.
                db.query(PortfolioAlertHistory).delete(synchronize_session=False)
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

    def force_refresh_prices(self, tickers: List[str]) -> None:
        """
        Force-fetch fresh prices from source (yfinance/pykrx), bypassing all caches.

        Clears the in-memory TTL caches and also invalidates the OHLCVCache
        in-memory metadata so that the next get() call re-fetches parquet from
        the network even if the parquet file was written today.
        """
        from concurrent.futures import as_completed
        if not tickers:
            return

        self._price_cache.clear()
        self._change_cache.clear()

        # Invalidate OHLCVCache in-memory metadata so _is_cache_fresh() re-reads
        # from disk and force_refresh=True actually hits the network.
        with self._cache._meta_lock:
            self._cache._latest_date_cache.clear()

        # Parallel force-refresh: writes fresh data to parquet for each ticker
        futures = {
            self._executor.submit(self._cache.get, ticker, 5, True): ticker
            for ticker in tickers
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.warning(f"Force refresh failed for {ticker}: {e}")

    def delete_all_holdings(self) -> None:
        """Remove all holdings and their associated sell rules."""
        db = SessionLocal()
        try:
            # Clearing holdings invalidates portfolio-scoped alert history.
            db.query(PortfolioAlertHistory).delete(synchronize_session=False)
            db.query(SellRule).delete(synchronize_session=False)
            db.query(Holding).delete(synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # Archive methods live in portfolio_archive_service.PortfolioArchiveService.
