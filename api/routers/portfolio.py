"""
Portfolio router.

Provides endpoints for portfolio management operations.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioSummary,
    PortfolioResponse,
    SellSignal,
    SellSignalsResponse,
)
from api.services.portfolio_service import get_portfolio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


@router.get(
    "",
    response_model=PortfolioResponse,
    summary="Get Full Portfolio",
    description="Get all holdings with current prices and portfolio summary.",
)
async def get_portfolio() -> PortfolioResponse:
    """
    Get full portfolio with holdings and summary.

    Returns all holdings with current market prices,
    P&L calculations, and aggregated portfolio summary.

    Returns:
        PortfolioResponse with holdings and summary
    """
    service = get_portfolio_service()

    try:
        holdings = service.get_all_holdings(with_prices=True)
        summary = service.get_summary()

        return PortfolioResponse(
            holdings=holdings,
            summary=summary
        )

    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get portfolio: {str(e)}"
        )


@router.get(
    "/holdings",
    response_model=List[HoldingResponse],
    summary="Get Holdings",
    description="Get all holdings with current prices and P&L.",
)
async def get_holdings(
    with_prices: bool = Query(
        default=True,
        description="Include current market prices (may slow response)"
    ),
) -> List[HoldingResponse]:
    """
    Get all holdings.

    Returns list of all holdings with optional current prices
    and P&L calculations.

    Args:
        with_prices: Whether to include current market prices

    Returns:
        List of HoldingResponse objects
    """
    service = get_portfolio_service()

    try:
        return service.get_all_holdings(with_prices=with_prices)

    except Exception as e:
        logger.error(f"Failed to get holdings: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get holdings: {str(e)}"
        )


@router.post(
    "/holdings",
    response_model=HoldingResponse,
    status_code=201,
    summary="Add Holding",
    description="Add a new holding or add to existing position.",
)
async def add_holding(data: HoldingCreate) -> HoldingResponse:
    """
    Add a new holding.

    If the ticker already exists, adds to the existing position
    and recalculates the average price.

    Args:
        data: HoldingCreate with holding details

    Returns:
        Created/updated HoldingResponse
    """
    service = get_portfolio_service()

    try:
        return service.add_holding(data)

    except Exception as e:
        logger.error(f"Failed to add holding: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add holding: {str(e)}"
        )


@router.get(
    "/holdings/{ticker}",
    response_model=HoldingResponse,
    summary="Get Single Holding",
    description="Get a single holding by ticker symbol.",
)
async def get_holding(ticker: str) -> HoldingResponse:
    """
    Get a single holding by ticker.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, 005930.KS)

    Returns:
        HoldingResponse with current price and P&L

    Raises:
        HTTPException: If holding not found
    """
    service = get_portfolio_service()

    try:
        holding = service.get_holding(ticker, with_price=True)
        if holding is None:
            raise HTTPException(
                status_code=404,
                detail=f"Holding not found: {ticker}"
            )
        return holding

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get holding {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get holding: {str(e)}"
        )


@router.put(
    "/holdings/{ticker}",
    response_model=HoldingResponse,
    summary="Update Holding",
    description="Update an existing holding's details.",
)
async def update_holding(ticker: str, data: HoldingUpdate) -> HoldingResponse:
    """
    Update an existing holding.

    Only provided fields will be updated.

    Args:
        ticker: Stock ticker symbol
        data: HoldingUpdate with fields to update

    Returns:
        Updated HoldingResponse

    Raises:
        HTTPException: If holding not found
    """
    service = get_portfolio_service()

    try:
        holding = service.update_holding(ticker, data)
        if holding is None:
            raise HTTPException(
                status_code=404,
                detail=f"Holding not found: {ticker}"
            )
        return holding

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update holding {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update holding: {str(e)}"
        )


@router.delete(
    "/holdings/{ticker}",
    status_code=204,
    summary="Remove Holding",
    description="Remove a holding from the portfolio.",
)
async def remove_holding(ticker: str) -> None:
    """
    Remove a holding.

    Args:
        ticker: Stock ticker symbol

    Raises:
        HTTPException: If holding not found
    """
    service = get_portfolio_service()

    try:
        success = service.remove_holding(ticker)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Holding not found: {ticker}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove holding {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove holding: {str(e)}"
        )


@router.get(
    "/summary",
    response_model=PortfolioSummary,
    summary="Get Portfolio Summary",
    description="Get aggregated portfolio summary with total P&L.",
)
async def get_summary() -> PortfolioSummary:
    """
    Get portfolio summary.

    Returns aggregated metrics including total investment,
    market value, and P&L.

    Returns:
        PortfolioSummary with aggregated metrics
    """
    service = get_portfolio_service()

    try:
        return service.get_summary()

    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.get(
    "/sell-signals",
    response_model=SellSignalsResponse,
    summary="Get Sell Signals",
    description="Get sell signals based on stop loss and take profit thresholds.",
)
async def get_sell_signals(
    stop_loss_pct: Optional[float] = Query(
        default=None,
        description="Stop loss threshold percentage (default: -10%)",
        le=0,
        examples=[-10.0, -15.0, -20.0]
    ),
    take_profit_pct: Optional[float] = Query(
        default=None,
        description="Take profit threshold percentage (default: +20%)",
        ge=0,
        examples=[15.0, 20.0, 30.0]
    ),
) -> SellSignalsResponse:
    """
    Get sell signals based on P&L thresholds.

    Checks all holdings against stop loss and take profit thresholds.
    Returns signals for holdings that have breached the thresholds.

    Args:
        stop_loss_pct: Stop loss threshold (negative, e.g., -10)
        take_profit_pct: Take profit threshold (positive, e.g., 20)

    Returns:
        SellSignalsResponse with list of signals
    """
    service = get_portfolio_service()

    try:
        from datetime import datetime

        signals = service.get_sell_signals(
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )

        return SellSignalsResponse(
            signals=signals,
            checked_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"Failed to get sell signals: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sell signals: {str(e)}"
        )
