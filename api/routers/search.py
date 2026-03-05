"""
Search router.

Provides endpoint for searching tickers by name or symbol.
"""

import logging
import re
from typing import List, Optional

import yfinance as yf
from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.schemas.analysis import SearchResult
from api.services.korean_search_service import get_korean_search_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Search"],
)

_KOREAN_RE = re.compile(r"[\uAC00-\uD7AF]")
_KR_CODE_RE = re.compile(r"^\d{6}$")


def _contains_korean(text: str) -> bool:
    return bool(_KOREAN_RE.search(text))


def _is_korean_code(text: str) -> bool:
    return bool(_KR_CODE_RE.match(text.strip()))


@router.get(
    "/search",
    response_model=List[SearchResult],
    summary="Search Tickers",
    description="Search for stock tickers by name or symbol.",
)
async def search_tickers(
    q: str = Query(
        ...,
        min_length=1,
        description="Search query (ticker symbol or company name)"
    ),
) -> List[SearchResult]:
    """
    Search for tickers matching the query.

    Searches by ticker symbol prefix and company name substring.
    Korean queries (hangul or 6-digit code) use local CSV data;
    other queries use yfinance.
    Returns up to 20 results.

    Args:
        q: Search query string

    Returns:
        List of matching SearchResult objects
    """
    if _contains_korean(q):
        return _search_korean(q)

    if _is_korean_code(q):
        results = _search_korean(q)
        if results:
            return results
        # Fallback to yfinance if code not found in local data
        return _search_yfinance(q)

    return _search_yfinance(q)


def _search_korean(q: str) -> List[SearchResult]:
    """Search Korean stocks from local CSV data."""
    service = get_korean_search_service()
    entries = service.search(q, limit=20)

    results: List[SearchResult] = []
    for entry in entries:
        display = f"{entry.name} ({entry.sector})" if entry.sector else entry.name
        results.append(SearchResult(ticker=entry.symbol, name=display))

    return results


def _search_yfinance(q: str) -> List[SearchResult]:
    """Search using yfinance API (existing behavior)."""
    results: List[SearchResult] = []
    query_upper = q.upper()

    # Try direct ticker lookup first
    try:
        ticker_obj = yf.Ticker(query_upper)
        info = ticker_obj.info
        if info and info.get("regularMarketPrice") is not None:
            name = info.get("shortName") or info.get("longName") or query_upper
            results.append(SearchResult(ticker=query_upper, name=name))
    except Exception:
        pass

    # Search using yfinance Search class
    try:
        search_obj = yf.Search(q, max_results=20)
        quotes = search_obj.quotes if hasattr(search_obj, "quotes") else []
        seen_tickers = {r.ticker for r in results}

        for item in quotes:
            symbol = item.get("symbol", "")
            name = item.get("shortname") or item.get("longname") or symbol
            if symbol and symbol not in seen_tickers:
                results.append(SearchResult(ticker=symbol, name=name))
                seen_tickers.add(symbol)
    except Exception as e:
        logger.warning(f"yfinance search failed: {e}")

    return results[:20]


class TickerPrice(BaseModel):
    ticker: str
    price: Optional[float] = None


@router.get(
    "/price/{ticker}",
    response_model=TickerPrice,
    summary="Get Current Price",
    description="Get current price for a single ticker.",
)
async def get_ticker_price(ticker: str) -> TickerPrice:
    """Get current price from OHLCV cache or yfinance."""
    try:
        from utils.data_cache import get_cache
        cache = get_cache()
        data = cache.get(ticker, days=5, force_refresh=False)
        if data is not None and not data.empty:
            valid = data["close"].dropna()
            if not valid.empty:
                return TickerPrice(ticker=ticker, price=float(valid.iloc[-1]))
    except Exception as e:
        logger.warning(f"Cache price lookup failed for {ticker}: {e}")

    # Fallback: yfinance
    try:
        info = yf.Ticker(ticker).fast_info
        price = getattr(info, "last_price", None)
        if price is not None:
            return TickerPrice(ticker=ticker, price=float(price))
    except Exception:
        pass

    return TickerPrice(ticker=ticker, price=None)
