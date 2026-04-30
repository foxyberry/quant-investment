"""Maintenance helpers for PortfolioCoreService."""

from __future__ import annotations

import logging
from typing import List

from api.database import SessionLocal
from api.models.portfolio import Holding, SellRule

logger = logging.getLogger(__name__)


def force_refresh_prices(service, tickers: List[str]) -> None:
    from concurrent.futures import as_completed

    if not tickers:
        return

    service._price_cache.clear()
    service._change_cache.clear()

    with service._cache._meta_lock:
        service._cache._latest_date_cache.clear()

    futures = {
        service._executor.submit(service._cache.get, ticker, 5, True): ticker
        for ticker in tickers
    }
    for future in as_completed(futures):
        ticker = futures[future]
        try:
            future.result()
        except Exception as exc:
            logger.warning("Force refresh failed for %s: %s", ticker, exc)


def delete_all_holdings(_service) -> None:
    db = SessionLocal()
    try:
        db.query(SellRule).delete(synchronize_session=False)
        db.query(Holding).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
