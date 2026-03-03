"""
Watchlist router.

Provides endpoints for watchlist management and buy signal evaluation.
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from api.schemas.watchlist import (
    BuyRuleCreate,
    BuyRuleResponse,
    BuyRuleUpdate,
    BuySignalsResponse,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistItemUpdate,
)
from api.services.watchlist_service import get_watchlist_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


# ── WatchlistItem endpoints ────────────────────────────────────────


@router.get(
    "/items",
    response_model=List[WatchlistItemResponse],
    summary="List Watchlist Items",
)
async def list_items(with_prices: bool = True) -> List[WatchlistItemResponse]:
    """Get all watchlist items with optional current prices."""
    service = get_watchlist_service()
    try:
        return service.get_all_items(with_prices=with_prices)
    except Exception as e:
        logger.error("Failed to list watchlist items: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/items/{item_id}",
    response_model=WatchlistItemResponse,
    summary="Get Watchlist Item",
)
async def get_item(item_id: int) -> WatchlistItemResponse:
    """Get a single watchlist item by ID."""
    service = get_watchlist_service()
    try:
        item = service.get_item(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Watchlist item {item_id} not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get watchlist item %d: %s", item_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/items",
    response_model=WatchlistItemResponse,
    status_code=201,
    summary="Add Watchlist Item",
)
async def create_item(data: WatchlistItemCreate) -> WatchlistItemResponse:
    """Add a new ticker to the watchlist."""
    service = get_watchlist_service()
    try:
        return service.create_item(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Failed to create watchlist item: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/items/{item_id}",
    response_model=WatchlistItemResponse,
    summary="Update Watchlist Item",
)
async def update_item(item_id: int, data: WatchlistItemUpdate) -> WatchlistItemResponse:
    """Update a watchlist item."""
    service = get_watchlist_service()
    try:
        item = service.update_item(item_id, data)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Watchlist item {item_id} not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update watchlist item %d: %s", item_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/items/{item_id}",
    status_code=204,
    summary="Remove Watchlist Item",
)
async def delete_item(item_id: int) -> None:
    """Remove a watchlist item and all its buy rules."""
    service = get_watchlist_service()
    try:
        success = service.delete_item(item_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Watchlist item {item_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete watchlist item %d: %s", item_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── BuyRule endpoints ──────────────────────────────────────────────


@router.get(
    "/items/{item_id}/buy-rules",
    response_model=List[BuyRuleResponse],
    summary="List Buy Rules",
)
async def list_buy_rules(item_id: int) -> List[BuyRuleResponse]:
    """Get all buy rules for a watchlist item."""
    service = get_watchlist_service()
    try:
        return service.get_rules_for_item(item_id)
    except Exception as e:
        logger.error("Failed to list buy rules for item %d: %s", item_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/items/{item_id}/buy-rules",
    response_model=BuyRuleResponse,
    status_code=201,
    summary="Create Buy Rule",
)
async def create_buy_rule(item_id: int, data: BuyRuleCreate) -> BuyRuleResponse:
    """Add a buy rule to a watchlist item."""
    service = get_watchlist_service()
    try:
        return service.create_rule(item_id, data)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)
    except Exception as e:
        logger.error("Failed to create buy rule for item %d: %s", item_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/buy-rules/{rule_id}",
    response_model=BuyRuleResponse,
    summary="Update Buy Rule",
)
async def update_buy_rule(rule_id: int, data: BuyRuleUpdate) -> BuyRuleResponse:
    """Update a buy rule."""
    service = get_watchlist_service()
    try:
        rule = service.update_rule(rule_id, data)
        if rule is None:
            raise HTTPException(status_code=404, detail=f"Buy rule {rule_id} not found")
        return rule
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Failed to update buy rule %d: %s", rule_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/buy-rules/{rule_id}",
    status_code=204,
    summary="Delete Buy Rule",
)
async def delete_buy_rule(rule_id: int) -> None:
    """Delete a buy rule."""
    service = get_watchlist_service()
    try:
        success = service.delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Buy rule {rule_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete buy rule %d: %s", rule_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Buy Signal Evaluation ─────────────────────────────────────────


@router.get(
    "/buy-signals",
    response_model=BuySignalsResponse,
    summary="Get Buy Signals",
)
async def get_buy_signals() -> BuySignalsResponse:
    """Evaluate all active buy rules and return triggered signals."""
    service = get_watchlist_service()
    try:
        signals = service.evaluate_buy_signals()
        return BuySignalsResponse(
            signals=signals,
            checked_at=datetime.now(),
        )
    except Exception as e:
        logger.error("Failed to evaluate buy signals: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
