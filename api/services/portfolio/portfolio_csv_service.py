"""CSV import/export helpers for PortfolioCoreService."""

from __future__ import annotations

import csv
import io
import logging
import threading
from datetime import date
from typing import Any, Dict

from api.database import SessionLocal
from api.models.portfolio import Holding

logger = logging.getLogger(__name__)


def import_from_csv(service, csv_content: str, mode: str = "merge") -> Dict[str, Any]:
    errors = []
    imported = 0
    updated = 0

    reader = csv.DictReader(io.StringIO(csv_content))
    fieldnames = reader.fieldnames or []
    lower_fields = [field.strip().lower() for field in fieldnames]

    required = {"ticker", "quantity", "avg_price"}
    if not required.issubset(set(lower_fields)):
        missing = required - set(lower_fields)
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    field_map = {lower: original for original, lower in zip(fieldnames, lower_fields)}
    valid_rows = []
    for row_num, row in enumerate(reader, start=2):
        ticker_val = row.get(field_map["ticker"], "").strip()
        qty_val = row.get(field_map["quantity"], "").strip()
        price_val = row.get(field_map["avg_price"], "").strip()

        if not ticker_val:
            errors.append({"row": row_num, "ticker": None, "reason": "Empty ticker"})
            continue

        ticker_val = ticker_val.upper()
        ticker_error = service._validate_ticker(ticker_val)
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

        valid_rows.append({
            "ticker": ticker_val,
            "quantity": quantity,
            "avg_price": avg_price,
            "name": row.get(field_map.get("name", ""), "").strip() or ticker_val,
            "currency": row.get(field_map.get("currency", ""), "").strip() or "KRW",
            "note": row.get(field_map.get("note", ""), "").strip() or None,
            "bought_at": row.get(field_map.get("bought_at", ""), "").strip() or None,
        })

    db = SessionLocal()
    try:
        if mode == "replace":
            db.query(Holding).delete()

        existing_tickers = {row[0] for row in db.query(Holding.ticker).all()}
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
                if bought_at_date:
                    row.bought_at = bought_at_date
                elif existing_bought_at:
                    pass
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

    logger.info("CSV import: imported=%d, updated=%d, skipped=%d", imported, updated, len(errors))

    if imported > 0:
        def _backfill_csv_imports() -> None:
            db2 = SessionLocal()
            try:
                null_rows = db2.query(Holding).filter(Holding.sector.is_(None)).all()
                for row in null_rows:
                    meta = service._fetch_static_metadata(row.ticker)
                    row.sector = meta.get("sector")
                    row.industry = meta.get("industry")
                    row.country = meta.get("country")
                    row.exchange = meta.get("exchange")
                if null_rows:
                    db2.commit()
                    logger.info("Backfilled metadata for %d CSV-imported holdings", len(null_rows))
            except Exception as exc:
                db2.rollback()
                logger.warning("CSV import metadata backfill failed: %s", exc)
            finally:
                db2.close()

        threading.Thread(target=_backfill_csv_imports, daemon=True).start()

    return {
        "imported": imported,
        "updated": updated,
        "skipped": len(errors),
        "errors": errors,
    }


def export_to_csv(service) -> str:
    db = SessionLocal()
    try:
        rows = db.query(Holding).all()
        holdings_dicts = [service._row_to_dict(row) for row in rows]
    finally:
        db.close()

    output = io.StringIO()
    columns = ["ticker", "quantity", "avg_price", "name", "currency", "note", "bought_at"]
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()

    for holding in holdings_dicts:
        row = {column: holding.get(column, "") for column in columns}
        if row["note"] is None:
            row["note"] = ""
        if isinstance(row["bought_at"], date):
            row["bought_at"] = row["bought_at"].isoformat()
        writer.writerow(row)

    return output.getvalue()
