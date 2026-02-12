"""
Search router.

Provides endpoint for searching tickers by name or symbol.
"""

import logging
from typing import List

import yfinance as yf
from fastapi import APIRouter, Query

from api.schemas.analysis import SearchResult

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Search"],
)


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
    Returns up to 20 results.

    Args:
        q: Search query string

    Returns:
        List of matching SearchResult objects
    """
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

    # Search using yfinance search
    try:
        search_results = yf.search(q, max_results=20)
        quotes = search_results.get("quotes", [])
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
