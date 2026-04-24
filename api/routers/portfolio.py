"""
Portfolio router.

Provides endpoints for portfolio management operations.
"""

import io
import logging
import asyncio
import time
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from api.schemas.portfolio import (
    AdditionalPurchaseRequest,
    ApplyPresetToHolding,
    ArchiveCreate,
    ArchiveDetailResponse,
    ArchiveSummary,
    BulkApplyPresetRequest,
    BulkApplyPresetResponse,
    CsvImportResponse,
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioSummary,
    PortfolioResponse,
    SavePresetFromHolding,
    SellSignal,
    SellSignalsResponse,
    SellRuleCreate,
    SellRuleUpdate,
    SellRuleResponse,
    SellRuleEvaluateResponse,
    SellRulePresetCreate,
    SellRulePresetUpdate,
    SellRulePresetResponse,
    SellRecordCreate,
    TradeResponse,
    TradeHistoryResponse,
)
from api.services.portfolio_service import get_portfolio_service

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "data" / "templates"
MAX_UPLOAD_SIZE = 1_048_576  # 1 MB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])
WS_PUSH_INTERVAL_SECONDS = 10
WS_SNAPSHOT_TTL_SECONDS = 3
_ws_snapshot_lock = asyncio.Lock()
_ws_snapshot_cache: dict | None = None
_ws_snapshot_ts: float = 0.0


def _parse_ticker_query(raw: str | None) -> List[str]:
    """Parse comma-separated ticker query into deduplicated list."""
    if not raw:
        return []
    seen: set[str] = set()
    tickers: List[str] = []
    for token in raw.split(","):
        ticker = token.strip().upper()
        if ticker and ticker not in seen:
            seen.add(ticker)
            tickers.append(ticker)
    return tickers


async def _get_ws_snapshot(service) -> dict:
    """
    Return a shared realtime snapshot for websocket clients.

    Snapshot work (holdings + price fetch) is computed once per TTL window and
    then reused across concurrent websocket clients.
    """
    global _ws_snapshot_cache, _ws_snapshot_ts

    now = time.monotonic()
    if _ws_snapshot_cache is not None and now - _ws_snapshot_ts < WS_SNAPSHOT_TTL_SECONDS:
        return _ws_snapshot_cache

    async with _ws_snapshot_lock:
        # Double-check after lock acquisition.
        now = time.monotonic()
        if _ws_snapshot_cache is not None and now - _ws_snapshot_ts < WS_SNAPSHOT_TTL_SECONDS:
            return _ws_snapshot_cache

        holdings = await asyncio.to_thread(service.get_all_holdings, False)
        currency_by_ticker = {h.ticker.upper(): h.currency for h in holdings if h.ticker}
        tickers = list(currency_by_ticker.keys())
        prices = await asyncio.to_thread(service._get_current_prices, tickers) if tickers else {}

        updates_by_ticker = {
            ticker: {
                "ticker": ticker,
                "current_price": float(price),
                "currency": currency_by_ticker.get(ticker.upper()),
            }
            for ticker, price in prices.items()
            if price is not None
        }

        _ws_snapshot_cache = {
            "updates_by_ticker": updates_by_ticker,
        }
        _ws_snapshot_ts = now
        return _ws_snapshot_cache


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
        summary = service.build_summary(holdings)

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


@router.post(
    "/holdings/import",
    response_model=CsvImportResponse,
    summary="Import Holdings from CSV",
    description="Bulk import holdings from a CSV file.",
)
async def import_holdings(
    file: UploadFile,
    mode: str = Form("merge"),
) -> CsvImportResponse:
    """
    Import holdings from a CSV file.

    Args:
        file: CSV file with ticker, quantity, avg_price columns
        mode: "merge" to upsert or "replace" to clear first

    Returns:
        CsvImportResponse with import counts and errors
    """
    if mode not in ("merge", "replace"):
        raise HTTPException(status_code=422, detail=f"Invalid mode: {mode}. Use 'merge' or 'replace'.")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 1 MB)")

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8")

    service = get_portfolio_service()

    try:
        result = service.import_from_csv(content, mode=mode)
        return CsvImportResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to import CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get(
    "/holdings/export",
    summary="Export Holdings as CSV",
    description="Download all holdings as a CSV file.",
)
async def export_holdings():
    """
    Export all holdings as CSV download.

    Returns:
        StreamingResponse with CSV content
    """
    service = get_portfolio_service()

    try:
        csv_str = service.export_to_csv()
        # Prepend UTF-8 BOM for Excel Korean support
        bom = b"\xef\xbb\xbf"
        output = io.BytesIO(bom + csv_str.encode("utf-8"))
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=portfolio_holdings.csv"
            },
        )
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get(
    "/holdings/template",
    summary="Download CSV Template",
    description="Download a CSV template for portfolio import.",
)
async def get_template(
    minimal: bool = Query(default=False, description="Return minimal template (required columns only)"),
):
    """
    Download a CSV template file.

    Args:
        minimal: If True, return template with required columns only

    Returns:
        StreamingResponse with template CSV
    """
    filename = "portfolio_template_minimal.csv" if minimal else "portfolio_template.csv"
    template_path = TEMPLATE_DIR / filename

    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template file not found")

    content = template_path.read_bytes()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
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


@router.post(
    "/holdings/{ticker}/add-purchase",
    response_model=HoldingResponse,
    summary="Add Purchase",
    description="Record an additional purchase for an existing holding. Recalculates average price.",
)
async def add_purchase(ticker: str, data: AdditionalPurchaseRequest) -> HoldingResponse:
    """
    Record an additional purchase (averaging down/up).

    Adds shares to the existing position, recalculates the weighted
    average price, and records a BUY trade in the trade history.

    Args:
        ticker: Stock ticker symbol
        data: AdditionalPurchaseRequest with quantity and price

    Returns:
        Updated HoldingResponse with recalculated averages

    Raises:
        HTTPException: If holding not found
    """
    service = get_portfolio_service()

    try:
        holding = service.add_purchase(ticker, data)
        if holding is None:
            raise HTTPException(
                status_code=404,
                detail=f"Holding not found: {ticker}"
            )
        return holding

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add purchase for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add purchase: {str(e)}"
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
async def get_summary(
    base_currency: Optional[str] = Query(
        default=None,
        min_length=3,
        max_length=3,
        description="Convert summary totals into this base currency (e.g., USD, KRW, SGD)",
    ),
) -> PortfolioSummary:
    """
    Get portfolio summary.

    Returns aggregated metrics including total investment,
    market value, and P&L.

    Returns:
        PortfolioSummary with aggregated metrics
    """
    service = get_portfolio_service()

    try:
        return service.get_summary(base_currency=base_currency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
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


# ── Sell Rule Presets ──────────────────────────────────────────────


@router.get(
    "/sell-rule-presets",
    response_model=List[SellRulePresetResponse],
    summary="List Sell Rule Presets",
)
async def list_sell_rule_presets() -> List[SellRulePresetResponse]:
    service = get_portfolio_service()
    return service.list_sell_rule_presets()


@router.post(
    "/sell-rule-presets",
    response_model=SellRulePresetResponse,
    status_code=201,
    summary="Create Sell Rule Preset",
)
async def create_sell_rule_preset(data: SellRulePresetCreate) -> SellRulePresetResponse:
    service = get_portfolio_service()
    try:
        return service.create_sell_rule_preset(data)
    except ValueError as e:
        msg = str(e)
        status = 409 if "already exists" in msg.lower() else 422
        raise HTTPException(status_code=status, detail=msg)


@router.put(
    "/sell-rule-presets/{preset_id}",
    response_model=SellRulePresetResponse,
    summary="Update Sell Rule Preset",
)
async def update_sell_rule_preset(preset_id: int, data: SellRulePresetUpdate) -> SellRulePresetResponse:
    service = get_portfolio_service()
    try:
        return service.update_sell_rule_preset(preset_id, data)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        if "already exists" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=422, detail=msg)


@router.delete(
    "/sell-rule-presets/{preset_id}",
    status_code=204,
    summary="Delete Sell Rule Preset",
)
async def delete_sell_rule_preset(preset_id: int) -> None:
    service = get_portfolio_service()
    if not service.delete_sell_rule_preset(preset_id):
        raise HTTPException(status_code=404, detail=f"Preset not found: {preset_id}")


@router.post(
    "/holdings/{ticker}/sell-rules/from-preset",
    response_model=List[SellRuleResponse],
    status_code=201,
    summary="Apply Preset to Holding",
)
async def apply_preset_to_holding(ticker: str, data: ApplyPresetToHolding) -> List[SellRuleResponse]:
    service = get_portfolio_service()
    try:
        return service.apply_preset_to_holding(ticker, data.preset_id)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        if "already applied" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        if "inactive" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=422, detail=msg)


@router.post(
    "/sell-rule-presets/{preset_id}/bulk-apply",
    response_model=BulkApplyPresetResponse,
    summary="Bulk Apply Preset to Multiple Holdings",
)
async def bulk_apply_preset(preset_id: int, data: BulkApplyPresetRequest) -> BulkApplyPresetResponse:
    from api.services.portfolio_service import PresetNotFoundError, PresetInactiveError
    service = get_portfolio_service()
    try:
        return service.bulk_apply_preset(preset_id, data.tickers)
    except PresetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PresetInactiveError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/holdings/{ticker}/sell-rules/save-as-preset",
    response_model=SellRulePresetResponse,
    status_code=201,
    summary="Save Holding Rules as Preset",
)
async def save_preset_from_holding(ticker: str, data: SavePresetFromHolding) -> SellRulePresetResponse:
    service = get_portfolio_service()
    try:
        return service.save_preset_from_holding(ticker, data.name, data.description)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        if "already exists" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        if "no sell rules" in msg.lower():
            raise HTTPException(status_code=422, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


# ── Sell Rules CRUD + Evaluate ──────────────────────────────────────


@router.get(
    "/holdings/{ticker}/sell-rules",
    response_model=List[SellRuleResponse],
    summary="List Sell Rules",
    description="Get all sell rules for a holding.",
)
async def list_sell_rules(ticker: str) -> List[SellRuleResponse]:
    service = get_portfolio_service()
    return service.get_sell_rules(ticker)


@router.post(
    "/holdings/{ticker}/sell-rules",
    response_model=SellRuleResponse,
    status_code=201,
    summary="Create Sell Rule",
    description="Add a sell rule to a holding.",
)
async def create_sell_rule(ticker: str, data: SellRuleCreate) -> SellRuleResponse:
    service = get_portfolio_service()
    try:
        return service.create_sell_rule(ticker, data)
    except ValueError as e:
        msg = str(e)
        status = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=status, detail=msg)


@router.put(
    "/sell-rules/{rule_id}",
    response_model=SellRuleResponse,
    summary="Update Sell Rule",
    description="Update a sell rule's params or active status.",
)
async def update_sell_rule(rule_id: int, data: SellRuleUpdate) -> SellRuleResponse:
    service = get_portfolio_service()
    try:
        return service.update_sell_rule(rule_id, data)
    except ValueError as e:
        msg = str(e)
        status = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=status, detail=msg)


@router.delete(
    "/sell-rules/{rule_id}",
    status_code=204,
    summary="Delete Sell Rule",
    description="Remove a sell rule.",
)
async def delete_sell_rule(rule_id: int) -> None:
    service = get_portfolio_service()
    if not service.delete_sell_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Sell rule not found: {rule_id}")


@router.post(
    "/sell-rules/evaluate",
    response_model=SellRuleEvaluateResponse,
    summary="Evaluate Sell Rules",
    description="Evaluate all active sell rules against current market data.",
)
async def evaluate_sell_rules(
    ticker: Optional[str] = Query(default=None, description="Evaluate rules for this ticker only"),
) -> SellRuleEvaluateResponse:
    service = get_portfolio_service()
    try:
        return service.evaluate_sell_rules(ticker=ticker)
    except Exception as e:
        logger.error(f"Failed to evaluate sell rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to evaluate sell rules: {str(e)}")


# ── Realtime websocket ─────────────────────────────────────────────


@router.websocket("/realtime/ws")
async def portfolio_realtime_websocket(websocket: WebSocket) -> None:
    """Stream periodic portfolio price updates for selected tickers."""
    await websocket.accept()
    service = get_portfolio_service()
    subscribed = _parse_ticker_query(websocket.query_params.get("tickers"))

    try:
        while True:
            snapshot = await _get_ws_snapshot(service)
            updates_by_ticker = snapshot.get("updates_by_ticker", {})
            tickers = subscribed or list(updates_by_ticker.keys())
            if not tickers:
                await websocket.send_json({"updates": []})
                await asyncio.sleep(WS_PUSH_INTERVAL_SECONDS)
                continue

            updates = [
                updates_by_ticker[ticker]
                for ticker in tickers
                if ticker in updates_by_ticker
            ]

            await websocket.send_json({"updates": updates})
            await asyncio.sleep(WS_PUSH_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        logger.info("Portfolio realtime websocket disconnected")
    except Exception as e:
        logger.warning("Portfolio realtime websocket terminated: %s", e)


# ── Trade (sell recording + history) ──────────────────────────────


@router.post(
    "/trades",
    response_model=TradeResponse,
    status_code=201,
    summary="Record a Sell Trade",
)
async def record_sell(data: SellRecordCreate) -> TradeResponse:
    service = get_portfolio_service()
    try:
        return service.record_sell(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to record sell: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record sell: {str(e)}")


@router.get(
    "/trades",
    response_model=TradeHistoryResponse,
    summary="Get Trade History",
)
async def get_trade_history(
    ticker: Optional[str] = Query(default=None, description="Filter by ticker"),
) -> TradeHistoryResponse:
    service = get_portfolio_service()
    try:
        return service.get_trade_history(ticker=ticker)
    except Exception as e:
        logger.error(f"Failed to get trade history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get trade history: {str(e)}")


# ── Bulk delete ───────────────────────────────────────────────────


@router.delete(
    "/holdings",
    status_code=204,
    summary="Delete All Holdings",
    description="Remove all holdings and their sell rules.",
)
async def delete_all_holdings() -> None:
    service = get_portfolio_service()
    try:
        service.delete_all_holdings()
    except Exception as e:
        logger.error(f"Failed to delete all holdings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete all holdings: {str(e)}")


# ── Cache ─────────────────────────────────────────────────────────


@router.post(
    "/cache/clear",
    status_code=204,
    summary="Force Refresh Prices",
    description=(
        "Force-fetch fresh prices from yfinance/pykrx for all held tickers, "
        "bypassing both the in-memory TTL cache and the on-disk parquet cache."
    ),
)
async def clear_price_cache() -> None:
    service = get_portfolio_service()
    holdings = service.get_all_holdings(with_prices=False)
    tickers = [h.ticker for h in holdings]
    await asyncio.to_thread(service.force_refresh_prices, tickers)


# ── Portfolio Archives ─────────────────────────────────────────────


@router.post(
    "/archives",
    response_model=ArchiveDetailResponse,
    status_code=201,
    summary="Create Portfolio Archive",
    description="Snapshot current holdings into a named archive for later comparison.",
)
async def create_archive(data: ArchiveCreate) -> ArchiveDetailResponse:
    service = get_portfolio_service()
    try:
        return service.create_archive(data)
    except Exception as e:
        logger.error(f"Failed to create archive: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create archive: {str(e)}")


@router.get(
    "/archives",
    response_model=List[ArchiveSummary],
    summary="List Portfolio Archives",
    description="Return all portfolio archives ordered by most recent first.",
)
async def list_archives() -> List[ArchiveSummary]:
    service = get_portfolio_service()
    try:
        return service.list_archives()
    except Exception as e:
        logger.error(f"Failed to list archives: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list archives: {str(e)}")


@router.get(
    "/archives/{archive_id}",
    response_model=ArchiveDetailResponse,
    summary="Get Portfolio Archive",
    description="Return a single archive with all holdings. Pass with_prices=true to include current prices and P&L.",
)
async def get_archive(
    archive_id: int,
    with_prices: bool = Query(
        default=False,
        description="Fetch live prices and compute pnl_pct for each item",
    ),
) -> ArchiveDetailResponse:
    service = get_portfolio_service()
    try:
        result = service.get_archive(archive_id, with_prices=with_prices)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Archive not found: {archive_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get archive {archive_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get archive: {str(e)}")


@router.delete(
    "/archives/{archive_id}",
    status_code=204,
    summary="Delete Portfolio Archive",
    description="Delete an archive and all its items.",
)
async def delete_archive(archive_id: int) -> None:
    service = get_portfolio_service()
    try:
        success = service.delete_archive(archive_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Archive not found: {archive_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete archive {archive_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete archive: {str(e)}")
