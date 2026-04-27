"""
Portfolio Base Service.

Provides initialization, cache setup, threading infrastructure,
and shared static helper methods used by all portfolio sub-services.
"""

import logging
import math
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from api.database import SessionLocal
from api.models.portfolio import Holding
from api.services.exchange_rate_service import ExchangeRateService, get_exchange_rate_service
from utils.data_cache import get_cache
from utils.ttl_cache import TTLCache

logger = logging.getLogger(__name__)

# Timeout for each enrichment future in get_all_holdings (seconds).
ENRICHMENT_TIMEOUT_SECONDS = 30


class PresetNotFoundError(Exception):
    """Raised when a sell rule preset does not exist."""


class PresetInactiveError(Exception):
    """Raised when a sell rule preset is deactivated."""


class PortfolioBaseService:
    """
    Base class for all portfolio sub-services.

    Owns the thread pool, TTL caches, and shared static helpers.
    Not intended to be instantiated directly.
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
    EXECUTOR_MAX_WORKERS = 8
    _shared_executor: Optional[ThreadPoolExecutor] = None
    _executor_lock = threading.Lock()

    _KR_CODE_PATTERN = re.compile(r'^[0-9A-Z]{6}$')

    @classmethod
    def _validate_ticker(cls, ticker: str) -> str | None:
        """Return an error message if ticker format is invalid, else None.

        Korean stock codes (6 alphanumeric chars) must include .KS or .KQ suffix.
        US tickers (letters only) are accepted as-is.
        """
        if "." in ticker:
            suffix = ticker.rsplit(".", 1)[-1].upper()
            if suffix not in ("KS", "KQ", "KL"):
                return f"알 수 없는 거래소 suffix: .{suffix} (한국: .KS / .KQ, 미국: suffix 없음)"
            return None

        if cls._KR_CODE_PATTERN.match(ticker):
            return (
                f"한국 종목은 거래소 suffix가 필요합니다: {ticker}.KS (KOSPI) 또는 {ticker}.KQ (KOSDAQ)"
            )

        return None  # US ticker (letters), leave as-is

    def __init__(self):
        self._cache = get_cache()
        self._fx: ExchangeRateService = get_exchange_rate_service()
        self._price_cache: TTLCache[float] = TTLCache(self.PRICE_CACHE_TTL, max_size=512)
        self._sector_cache: TTLCache[Optional[str]] = TTLCache(self.SECTOR_CACHE_TTL, max_size=512)
        self._change_cache: TTLCache[Optional[float]] = TTLCache(self.CHANGE_CACHE_TTL, max_size=512)
        if self.__class__._shared_executor is None:
            with self.__class__._executor_lock:
                if self.__class__._shared_executor is None:
                    self.__class__._shared_executor = ThreadPoolExecutor(
                        max_workers=self.EXECUTOR_MAX_WORKERS
                    )
        self._executor = self.__class__._shared_executor
        self._backfill_null_sectors()

    def _backfill_null_sectors(self):
        """Backfill sector/industry/country/exchange for holdings with null sector (runs once at init)."""
        import threading

        def _do_backfill():
            # Phase 1: read ticker list (short DB session)
            db = SessionLocal()
            try:
                tickers = [r.ticker for r in db.query(Holding.ticker).filter(Holding.sector.is_(None)).all()]
            finally:
                db.close()

            if not tickers:
                return

            # Phase 2: fetch metadata outside DB session (network I/O)
            meta_map = {}
            for ticker in tickers:
                meta = self._fetch_static_metadata(ticker)
                if meta.get("sector"):
                    meta_map[ticker] = meta

            if not meta_map:
                return

            # Phase 3: batch update (short DB session)
            db = SessionLocal()
            try:
                for ticker, meta in meta_map.items():
                    row = db.query(Holding).filter(Holding.ticker == ticker).first()
                    if row and row.sector is None:
                        row.sector = meta["sector"]
                        row.industry = meta.get("industry") or row.industry
                        row.country = meta.get("country") or row.country
                        row.exchange = meta.get("exchange") or row.exchange
                db.commit()
                logger.info(f"Backfilled sector metadata for {len(meta_map)}/{len(tickers)} holdings")
            except Exception as e:
                db.rollback()
                logger.warning(f"Sector backfill failed: {e}")
            finally:
                db.close()

        threading.Thread(target=_do_backfill, daemon=True).start()

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
            logger.warning(
                "Missing exchange rate for %s→%s (amount=%.2f); returning unconverted",
                from_currency, base, amount,
            )
            return amount
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

