"""
Screening router.

Provides endpoints for stock screening operations.
"""

import json
import logging
import queue
import threading
import time
from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.schemas.screening import (
    ScreeningRequest,
    ScreeningResponse,
    ScreeningResultItem,
    ScreeningProgressEvent,
    PresetInfo,
    UniverseInfo,
    SingleStockRequest,
    find_invalid_universes,
    format_invalid_universe_error,
)
from api.services.screening_service import get_screening_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screening", tags=["Screening"])


@router.get(
    "/presets",
    response_model=List[PresetInfo],
    summary="Get Available Presets",
    description="Get list of available screening presets with their descriptions and conditions.",
)
def get_presets() -> List[PresetInfo]:
    """
    Get available screening presets.

    Returns a list of all available presets with their names,
    descriptions, and the conditions they contain.

    Returns:
        List of PresetInfo objects
    """
    service = get_screening_service()
    return service.get_available_presets()


@router.get(
    "/universes",
    response_model=List[UniverseInfo],
    summary="Get Available Universes",
    description="Get list of available stock universes (KOSPI, KOSDAQ, SP500, etc.).",
)
def get_universes() -> List[UniverseInfo]:
    """
    Get available stock universes.

    Returns a list of all available universes with their names,
    descriptions, and approximate stock counts.

    Returns:
        List of UniverseInfo objects
    """
    service = get_screening_service()
    return service.get_available_universes()


@router.post(
    "/run",
    response_model=ScreeningResponse,
    summary="Run Screening",
    description="Run stock screening with the specified preset and universe. "
                "This operation may take several minutes depending on the universe size.",
)
def run_screening(request: ScreeningRequest) -> ScreeningResponse:
    """
    Run stock screening.

    Executes screening on the specified universe using the given preset.
    Returns all stocks that match all conditions in the preset.

    Note: This is a synchronous operation that may take several minutes
    for large universes (e.g., KOSPI with 900+ stocks).

    Args:
        request: ScreeningRequest with preset, universe, and optional params

    Returns:
        ScreeningResponse with matched stocks

    Raises:
        HTTPException: If preset or universe is invalid
    """
    service = get_screening_service()

    invalid_universes = find_invalid_universes(request.universes)
    if invalid_universes:
        raise HTTPException(
            status_code=400,
            detail=format_invalid_universe_error(invalid_universes),
        )

    try:
        result = service.run_screening(
            preset=request.preset,
            universe=request.universe,
            universes=request.universes,
            params=request.params
        )

        return ScreeningResponse(
            results=result["results"],
            total_count=result["total_count"],
            matched_count=result["matched_count"],
            universe=request.universe,
            universes=request.universes,
        )

    except ValueError as e:
        logger.warning(f"Screening request failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Screening error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Screening failed: {str(e)}"
        )


@router.post(
    "/run/stream",
    summary="Run Screening with SSE progress",
    description="Run stock screening and stream progress events via SSE.",
)
def run_screening_stream(request: ScreeningRequest):
    """Run screening with progress events."""
    service = get_screening_service()

    invalid_universes = find_invalid_universes(request.universes)
    if invalid_universes:
        raise HTTPException(
            status_code=400,
            detail=format_invalid_universe_error(invalid_universes),
        )

    progress_queue: queue.Queue = queue.Queue(maxsize=100)
    cancel_event = threading.Event()

    def _progress_cb(processed: int, total: int, matched: int) -> None:
        if cancel_event.is_set():
            return
        interval = max(1, -(-total // 50))
        if processed % interval != 0 and processed != total:
            return
        try:
            progress_queue.put_nowait(
                ScreeningProgressEvent(
                    processed_tickers=processed,
                    total_tickers=total,
                    matched_count=matched,
                    progress_pct=round(processed / total * 100, 1) if total else 0.0,
                    status="running",
                )
            )
        except queue.Full:
            pass

    def _run() -> None:
        try:
            result = service.run_screening(
                preset=request.preset,
                universe=request.universe,
                universes=request.universes,
                params=request.params,
                progress_callback=_progress_cb,
            )
            if cancel_event.is_set():
                return
            progress_queue.put(
                ScreeningProgressEvent(
                    processed_tickers=result["total_count"],
                    total_tickers=result["total_count"],
                    matched_count=result["matched_count"],
                    progress_pct=100.0,
                    status="done",
                ),
                timeout=5,
            )
            if cancel_event.is_set():
                return
            progress_queue.put(result, timeout=5)
        except ValueError as e:
            if cancel_event.is_set():
                return
            try:
                progress_queue.put(
                    ScreeningProgressEvent(status="error", message=str(e)),
                    timeout=5,
                )
            except queue.Full:
                pass
        except Exception:
            logger.error("Screening stream error", exc_info=True)
            if cancel_event.is_set():
                return
            try:
                progress_queue.put(
                    ScreeningProgressEvent(
                        status="error",
                        message="Screening failed. Check server logs for details.",
                    ),
                    timeout=5,
                )
            except queue.Full:
                pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    def event_stream():
        start = time.monotonic()
        max_duration = 600
        try:
            while True:
                if time.monotonic() - start > max_duration:
                    yield f"event: error\ndata: {json.dumps({'status': 'error', 'message': 'Maximum duration exceeded'})}\n\n"
                    break
                try:
                    item = progress_queue.get(timeout=5)
                except queue.Empty:
                    yield ": heartbeat\n\n"
                    continue

                if isinstance(item, ScreeningProgressEvent):
                    yield f"event: progress\ndata: {item.model_dump_json()}\n\n"
                    if item.status in ("done", "error"):
                        if item.status == "done":
                            final_result = None
                            for _ in range(6):
                                if time.monotonic() - start > max_duration:
                                    yield f"event: error\ndata: {json.dumps({'status': 'error', 'message': 'Maximum duration exceeded'})}\n\n"
                                    return
                                try:
                                    maybe_result = progress_queue.get(timeout=5)
                                    if isinstance(maybe_result, ScreeningProgressEvent):
                                        yield f"event: progress\ndata: {maybe_result.model_dump_json()}\n\n"
                                        continue
                                    final_result = maybe_result
                                    break
                                except queue.Empty:
                                    yield ": heartbeat\n\n"
                            if final_result is not None:
                                response = ScreeningResponse(
                                    results=final_result["results"],
                                    total_count=final_result["total_count"],
                                    matched_count=final_result["matched_count"],
                                    universe=request.universe,
                                    universes=request.universes,
                                )
                                yield f"event: result\ndata: {response.model_dump_json()}\n\n"
                        break
                else:
                    response = ScreeningResponse(
                        results=item["results"],
                        total_count=item["total_count"],
                        matched_count=item["matched_count"],
                        universe=request.universe,
                        universes=request.universes,
                    )
                    yield f"event: result\ndata: {response.model_dump_json()}\n\n"
                    break
        finally:
            cancel_event.set()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/stock/{ticker}",
    response_model=ScreeningResultItem,
    summary="Check Single Stock",
    description="Check a single stock against screening conditions.",
)
def check_single_stock(
    ticker: str,
    preset: str = Query(
        default="accumulation_basic",
        description="Preset name for screening conditions"
    ),
) -> ScreeningResultItem:
    """
    Check a single stock against screening conditions.

    Evaluates the specified stock against the given preset conditions
    and returns detailed results for each condition.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, 005930.KS)
        preset: Preset name (default: accumulation_basic)

    Returns:
        ScreeningResultItem with evaluation results

    Raises:
        HTTPException: If ticker or preset is invalid
    """
    service = get_screening_service()

    try:
        result = service.check_single_stock(
            ticker=ticker,
            preset=preset,
            params=None
        )
        return result

    except ValueError as e:
        logger.warning(f"Single stock check failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Single stock check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Stock check failed: {str(e)}"
        )


@router.post(
    "/stock/{ticker}",
    response_model=ScreeningResultItem,
    summary="Check Single Stock with Params",
    description="Check a single stock against screening conditions with custom parameters.",
)
def check_single_stock_with_params(
    ticker: str,
    request: SingleStockRequest,
) -> ScreeningResultItem:
    """
    Check a single stock with custom parameters.

    Evaluates the specified stock against the given preset conditions
    with optional parameter overrides.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, 005930.KS)
        request: SingleStockRequest with preset and optional params

    Returns:
        ScreeningResultItem with evaluation results

    Raises:
        HTTPException: If ticker or preset is invalid
    """
    service = get_screening_service()

    try:
        result = service.check_single_stock(
            ticker=ticker,
            preset=request.preset,
            params=request.params
        )
        return result

    except ValueError as e:
        logger.warning(f"Single stock check failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Single stock check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Stock check failed: {str(e)}"
        )
