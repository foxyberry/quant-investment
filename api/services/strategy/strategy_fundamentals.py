"""
Strategy Fundamentals.

Fetches and enriches PER/PBR/dividend_yield for strategy result items.
Supports both KR (pykrx) and US (yfinance) tickers with best-effort caching.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from api.schemas.strategy import StrategyResultItem
from utils.fundamental_cache import FundamentalCache
from api.services.strategy.strategy_core_service import (
    _to_optional_float,
    _is_korean_ticker,
    _extract_krx_code,
)

logger = logging.getLogger(__name__)

FUNDAMENTAL_TTL_SECONDS = 24 * 60 * 60
_fundamental_cache = FundamentalCache()


def _normalize_dividend_yield(value: Any) -> Optional[float]:
    """Normalize dividend yield to percentage points (e.g., 3.2 for 3.2%)."""
    dividend_yield = _to_optional_float(value)
    if dividend_yield is None:
        return None
    # yfinance uses decimal (0.03 = 3%); pykrx uses percent directly.
    if 0 <= dividend_yield <= 1:
        return dividend_yield * 100.0
    return dividend_yield


def _fetch_kr_fundamentals(tickers: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
    """Fetch KR fundamentals in bulk via pykrx (best effort)."""
    fundamentals: Dict[str, Dict[str, Optional[float]]] = {}
    missing_tickers: List[str] = []

    for ticker in tickers:
        cached = _fundamental_cache.get("fundamental_kr", ticker, FUNDAMENTAL_TTL_SECONDS)
        if cached is not None:
            fundamentals[ticker] = {
                "per": cached.get("per"),
                "pbr": cached.get("pbr"),
                "dividend_yield": cached.get("dividend_yield"),
            }
        else:
            missing_tickers.append(ticker)

    if not missing_tickers:
        return fundamentals

    try:
        from pykrx import stock as pykrx_stock
    except ImportError:
        return fundamentals

    by_market: Dict[str, Dict[str, str]] = {"KOSPI": {}, "KOSDAQ": {}}
    for ticker in missing_tickers:
        if ticker.endswith(".KS"):
            by_market["KOSPI"][_extract_krx_code(ticker)] = ticker
        elif ticker.endswith(".KQ"):
            by_market["KOSDAQ"][_extract_krx_code(ticker)] = ticker

    for market, code_to_ticker in by_market.items():
        if not code_to_ticker:
            continue

        df = None
        for days_back in range(0, 11):
            date_str = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
            try:
                candidate = pykrx_stock.get_market_fundamental_by_ticker(
                    date=date_str, market=market,
                )
                if candidate is not None and not candidate.empty:
                    df = candidate
                    break
            except Exception:
                continue

        if df is None or df.empty:
            continue

        for code, full_ticker in code_to_ticker.items():
            if code not in df.index:
                continue
            row = df.loc[code]
            parsed = {
                "per": _to_optional_float(row.get("PER")),
                "pbr": _to_optional_float(row.get("PBR")),
                "dividend_yield": _to_optional_float(row.get("DIV")),
            }
            fundamentals[full_ticker] = parsed
            _fundamental_cache.set("fundamental_kr", full_ticker, parsed)

    return fundamentals


def _fetch_us_fundamentals(tickers: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
    """Fetch US fundamentals via yfinance info (best effort)."""
    if not tickers:
        return {}

    fundamentals: Dict[str, Dict[str, Optional[float]]] = {}
    missing_tickers: List[str] = []

    for ticker in tickers:
        cached = _fundamental_cache.get("fundamental_us", ticker, FUNDAMENTAL_TTL_SECONDS)
        if cached is not None:
            fundamentals[ticker] = {
                "per": cached.get("per"),
                "pbr": cached.get("pbr"),
                "dividend_yield": cached.get("dividend_yield"),
            }
        else:
            missing_tickers.append(ticker)

    if not missing_tickers:
        return fundamentals

    try:
        import yfinance as yf
    except ImportError:
        return fundamentals

    try:
        tickers_obj = yf.Tickers(" ".join(missing_tickers))
    except Exception:
        tickers_obj = None

    def _is_success_payload(payload: Dict[str, Optional[float]]) -> bool:
        return any(v is not None for v in payload.values())

    def _fetch_one(ticker: str) -> tuple[Dict[str, Optional[float]], bool]:
        try:
            info: Dict[str, Any] = {}
            if tickers_obj is not None:
                ticker_obj = tickers_obj.tickers.get(ticker)
                if ticker_obj is not None:
                    info = ticker_obj.info or {}
            if not info:
                info = yf.Ticker(ticker).info or {}

            payload = {
                "per": _to_optional_float(info.get("trailingPE")),
                "pbr": _to_optional_float(info.get("priceToBook")),
                "dividend_yield": _normalize_dividend_yield(info.get("dividendYield")),
            }
            return payload, _is_success_payload(payload)
        except Exception:
            return {"per": None, "pbr": None, "dividend_yield": None}, False

    max_workers = min(8, len(missing_tickers))
    if max_workers <= 1:
        ticker = missing_tickers[0]
        fetched, success = _fetch_one(ticker)
        fundamentals[ticker] = fetched
        if success:
            _fundamental_cache.set("fundamental_us", ticker, fetched)
        return fundamentals

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_fetch_one, t): t for t in missing_tickers}
        try:
            for future in as_completed(future_map, timeout=10):
                ticker = future_map[future]
                try:
                    fetched, success = future.result(timeout=5)
                    fundamentals[ticker] = fetched
                    if success:
                        _fundamental_cache.set("fundamental_us", ticker, fetched)
                except Exception:
                    fundamentals[ticker] = {"per": None, "pbr": None, "dividend_yield": None}
        except TimeoutError:
            logger.warning("US fundamentals fetch timed out; filling remaining with None")
            for future, ticker in future_map.items():
                if ticker not in fundamentals:
                    future.cancel()
                    fundamentals[ticker] = {"per": None, "pbr": None, "dividend_yield": None}

    return fundamentals


def enrich_fundamentals(items: List[StrategyResultItem]) -> None:
    """Fill PER/PBR/dividend_yield for strategy result items (best effort)."""
    if not items:
        return

    unique_tickers = sorted({item.ticker for item in items if item.ticker})
    if not unique_tickers:
        return

    kr_tickers = [t for t in unique_tickers if _is_korean_ticker(t)]
    us_tickers = [t for t in unique_tickers if not _is_korean_ticker(t)]

    fundamentals: Dict[str, Dict[str, Optional[float]]] = {}
    try:
        fundamentals.update(_fetch_kr_fundamentals(kr_tickers))
    except Exception as e:
        logger.warning("Failed to fetch KR fundamentals: %s", e)

    try:
        fundamentals.update(_fetch_us_fundamentals(us_tickers))
    except Exception as e:
        logger.warning("Failed to fetch US fundamentals: %s", e)

    for item in items:
        data = fundamentals.get(item.ticker, {})
        item.per = data.get("per")
        item.pbr = data.get("pbr")
        item.dividend_yield = data.get("dividend_yield")
