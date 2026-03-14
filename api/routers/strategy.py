"""
Strategy Router.

Endpoints for the visual strategy builder.
"""

import json
import logging
import queue
import threading
import time

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.schemas.strategy_chat import (
    StrategyChatRequest,
    ValidatePayloadRequest,
    ValidatePayloadResponse,
)
from api.schemas.strategy_backtest_result import (
    StrategyBacktestResultResponse,
    StrategyBacktestResultsListResponse,
)
from api.schemas.strategy_validation import (
    StrategyValidateRequest,
    StrategyValidateResponse,
)
from api.schemas.strategy_comparison import (
    LeaderboardResponse,
    StrategyCompareRequest,
    StrategyCompareResponse,
)
from api.schemas.pine_script import (
    PineScriptExportRequest,
    PineScriptExportResponse,
)
from api.schemas.strategy_webhook import (
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdateRequest,
)
from api.schemas.strategy_alert import (
    AlertConfigResponse,
    AlertConfigUpsertRequest,
    AlertHistoryResponse,
)
from api.schemas.strategy import (
    ConditionsListResponse,
    SavedStrategiesListResponse,
    SavedStrategyResponse,
    SectorInfo,
    SectorListResponse,
    StrategyExecuteRequest,
    StrategyExecuteResponse,
    StrategyProgressEvent,
    StrategySaveRequest,
    StrategyStatusUpdateRequest,
    StrategyUpdateRequest,
)
from api.schemas.screening import (
    find_invalid_universes,
    format_invalid_universe_error,
)
from api.services.strategy_save_service import get_strategy_save_service
from api.services.strategy_service import (
    enrich_fundamentals,
    execute_strategy,
    execute_strategy_with_progress,
    get_available_conditions,
)
from screener.sector_fetcher import get_sector_fetcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategy", tags=["Strategy"])


@router.get(
    "/conditions",
    response_model=ConditionsListResponse,
    summary="Get available conditions",
    description="Return all available condition types with their parameter schemas.",
)
async def list_conditions() -> ConditionsListResponse:
    """Return available condition types for the node palette."""
    conditions = get_available_conditions()
    conditions.sort(key=lambda c: (not c.recommended, c.order, c.key))
    categories = sorted(set(c.category for c in conditions))
    return ConditionsListResponse(conditions=conditions, categories=categories)


@router.get(
    "/saved",
    response_model=SavedStrategiesListResponse,
    summary="List saved strategies",
    description="Return all saved strategy graphs.",
)
async def list_saved_strategies() -> SavedStrategiesListResponse:
    """List all saved strategies."""
    service = get_strategy_save_service()
    strategies = service.list_strategies()
    return SavedStrategiesListResponse(
        strategies=strategies,
        total_count=len(strategies),
    )


@router.post(
    "/saved",
    response_model=SavedStrategyResponse,
    status_code=201,
    summary="Save strategy",
    description="Save a new strategy graph.",
)
async def save_strategy(data: StrategySaveRequest) -> SavedStrategyResponse:
    """Save a new strategy graph."""
    service = get_strategy_save_service()
    try:
        return service.save_strategy(data)
    except Exception as e:
        logger.error(f"Failed to save strategy: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save strategy: {str(e)}",
        )


@router.get(
    "/saved/{strategy_id}",
    response_model=SavedStrategyResponse,
    summary="Get saved strategy",
    description="Get one saved strategy by ID.",
)
async def get_saved_strategy(strategy_id: str) -> SavedStrategyResponse:
    """Get one saved strategy."""
    service = get_strategy_save_service()
    try:
        strategy = service.get_strategy(strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        return strategy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get strategy: {str(e)}",
        )


@router.put(
    "/saved/{strategy_id}",
    response_model=SavedStrategyResponse,
    summary="Update saved strategy",
    description="Update an existing saved strategy.",
)
async def update_saved_strategy(
    strategy_id: str,
    data: StrategyUpdateRequest,
) -> SavedStrategyResponse:
    """Update one saved strategy."""
    service = get_strategy_save_service()
    try:
        strategy = service.update_strategy(strategy_id, data)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        return strategy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update strategy: {str(e)}",
        )


@router.patch(
    "/saved/{strategy_id}/status",
    response_model=SavedStrategyResponse,
    summary="Update strategy status",
    description="Update the lifecycle status of a saved strategy (draft → backtested → validated → production → retired).",
)
async def update_strategy_status(
    strategy_id: str,
    data: StrategyStatusUpdateRequest,
) -> SavedStrategyResponse:
    """Update strategy lifecycle status."""
    service = get_strategy_save_service()
    try:
        strategy = service.update_status(strategy_id, data.status)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        return strategy
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update strategy status {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to update strategy status. Check server logs.",
        )


@router.post(
    "/saved/{strategy_id}/validate",
    response_model=StrategyValidateResponse,
    summary="Validate strategy indicators",
    description="Run cross-validation on a strategy's indicators. "
    "If all checks pass and strategy is 'backtested', promotes to 'validated'.",
)
async def validate_strategy(
    strategy_id: str,
    data: StrategyValidateRequest = StrategyValidateRequest(),
) -> StrategyValidateResponse:
    """Run cross-validation on a strategy's indicators and optionally promote."""
    from api.services.strategy_validation_service import validate_strategy as _validate

    try:
        return _validate(
            strategy_id=strategy_id,
            ticker=data.ticker,
            period=data.period,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Strategy validation failed for {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Strategy validation failed. Check server logs.",
        )


@router.post(
    "/compare",
    response_model=StrategyCompareResponse,
    summary="Compare strategies",
    description="Compare 2-4 strategies side by side using their latest backtest metrics.",
)
async def compare_strategies(data: StrategyCompareRequest) -> StrategyCompareResponse:
    """Compare multiple strategies using their latest backtest results."""
    from api.services.strategy_comparison_service import compare_strategies as _compare

    try:
        return _compare(data.strategy_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Strategy comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Strategy comparison failed.")


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    summary="Strategy leaderboard",
    description="Ranked list of strategies by backtest performance metrics.",
)
async def strategy_leaderboard(
    sort_by: str = "sharpe_ratio",
    order: str = "desc",
    status: str | None = None,
    limit: int = 20,
) -> LeaderboardResponse:
    """Get strategy leaderboard ranked by performance."""
    from api.services.strategy_comparison_service import get_leaderboard

    try:
        return get_leaderboard(sort_by=sort_by, order=order, status=status, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Leaderboard failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Leaderboard failed.")


@router.post(
    "/export/pine-script",
    response_model=PineScriptExportResponse,
    summary="Export strategy as Pine Script v5",
    description="Transpile a strategy graph into TradingView Pine Script v5 code.",
)
async def export_pine_script(data: PineScriptExportRequest) -> PineScriptExportResponse:
    """Export a strategy graph as Pine Script v5."""
    from api.services.pine_script_exporter import export_pine_script as _export

    try:
        pine_code = _export(
            graph=data.graph,
            strategy_name=data.strategy_name,
            take_profit=data.take_profit,
            stop_loss=data.stop_loss,
        )
        # Extract used/skipped conditions
        nodes = data.graph.get("nodes", [])
        used, skipped = [], []
        from api.services.pine_script_exporter import _PINE_COMPILERS
        for node in nodes:
            nd = node.get("data", {})
            if nd.get("node_type") != "condition":
                continue
            ct = nd.get("condition_type", "")
            if ct in _PINE_COMPILERS:
                used.append(ct)
            else:
                skipped.append(ct)
        return PineScriptExportResponse(
            pine_script=pine_code,
            strategy_name=data.strategy_name,
            conditions_used=used,
            conditions_skipped=skipped,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pine Script export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pine Script export failed.")


@router.get(
    "/saved/{strategy_id}/backtest-results",
    response_model=StrategyBacktestResultsListResponse,
    summary="List backtest results for a strategy",
    description="Return all backtest results for a saved strategy, most recent first.",
)
async def list_backtest_results(strategy_id: str) -> StrategyBacktestResultsListResponse:
    """List all backtest results for a strategy."""
    from api.services.strategy_backtest_result_service import get_results

    results = get_results(strategy_id)
    return StrategyBacktestResultsListResponse(
        strategy_id=strategy_id,
        results=results,
        total_count=len(results),
    )


@router.get(
    "/saved/{strategy_id}/backtest-results/latest",
    response_model=StrategyBacktestResultResponse,
    summary="Get latest backtest result",
    description="Return the most recent backtest result for a saved strategy.",
)
async def get_latest_backtest_result(strategy_id: str) -> StrategyBacktestResultResponse:
    """Get the latest backtest result for a strategy."""
    from api.services.strategy_backtest_result_service import get_latest

    result = get_latest(strategy_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No backtest results found for strategy: {strategy_id}",
        )
    return result


@router.delete(
    "/saved/{strategy_id}",
    status_code=204,
    summary="Delete saved strategy",
    description="Delete a saved strategy.",
)
async def delete_saved_strategy(strategy_id: str) -> None:
    """Delete one saved strategy."""
    service = get_strategy_save_service()
    try:
        success = service.delete_strategy(strategy_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete strategy: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Webhook CRUD
# ---------------------------------------------------------------------------

@router.get(
    "/saved/{strategy_id}/webhooks",
    response_model=WebhookListResponse,
    summary="List webhooks for a strategy",
)
async def list_webhooks(strategy_id: str) -> WebhookListResponse:
    """List all webhook configurations for a strategy."""
    from api.services.strategy_webhook_service import list_webhooks as _list
    return _list(strategy_id)


@router.post(
    "/saved/{strategy_id}/webhooks",
    response_model=WebhookResponse,
    status_code=201,
    summary="Create webhook",
)
async def create_webhook(strategy_id: str, data: WebhookCreateRequest) -> WebhookResponse:
    """Create a new webhook for a strategy."""
    from api.services.strategy_webhook_service import create_webhook as _create
    try:
        return _create(strategy_id, data)
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create webhook.")


@router.put(
    "/saved/{strategy_id}/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update webhook",
)
async def update_webhook(
    strategy_id: str, webhook_id: int, data: WebhookUpdateRequest
) -> WebhookResponse:
    """Update a webhook configuration."""
    from api.services.strategy_webhook_service import update_webhook as _update
    result = _update(strategy_id, webhook_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return result


@router.delete(
    "/saved/{strategy_id}/webhooks/{webhook_id}",
    status_code=204,
    summary="Delete webhook",
)
async def delete_webhook(strategy_id: str, webhook_id: int) -> None:
    """Delete a webhook."""
    from api.services.strategy_webhook_service import delete_webhook as _delete
    if not _delete(strategy_id, webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")


# ---------------------------------------------------------------------------
# Alert Configuration & History
# ---------------------------------------------------------------------------

@router.get(
    "/saved/{strategy_id}/alerts/config",
    response_model=AlertConfigResponse,
    summary="Get alert configuration",
)
async def get_alert_config(strategy_id: str) -> AlertConfigResponse:
    """Get live signal alert configuration for a strategy."""
    from api.services.strategy_alert_service import get_alert_config as _get
    result = _get(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Alert config not found")
    return result


@router.put(
    "/saved/{strategy_id}/alerts/config",
    response_model=AlertConfigResponse,
    summary="Create or update alert configuration",
)
async def upsert_alert_config(
    strategy_id: str, data: AlertConfigUpsertRequest
) -> AlertConfigResponse:
    """Create or update live signal alert configuration."""
    from api.services.strategy_alert_service import upsert_alert_config as _upsert
    try:
        return _upsert(strategy_id, data)
    except Exception as e:
        logger.error(f"Failed to upsert alert config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update alert config.")


@router.delete(
    "/saved/{strategy_id}/alerts/config",
    status_code=204,
    summary="Delete alert configuration",
)
async def delete_alert_config(strategy_id: str) -> None:
    """Delete alert configuration for a strategy."""
    from api.services.strategy_alert_service import delete_alert_config as _delete
    if not _delete(strategy_id):
        raise HTTPException(status_code=404, detail="Alert config not found")


@router.get(
    "/saved/{strategy_id}/alerts/history",
    response_model=AlertHistoryResponse,
    summary="Get alert history",
)
async def get_alert_history(
    strategy_id: str, limit: int = Query(50, ge=1, le=200)
) -> AlertHistoryResponse:
    """Get fired alert history for a strategy."""
    from api.services.strategy_alert_service import get_alert_history as _history
    return _history(strategy_id, limit=limit)


@router.get(
    "/sectors",
    response_model=SectorListResponse,
    summary="Get available sectors",
    description="Return all available sectors for a given market with stock counts.",
)
async def list_sectors(market: str = "KOSPI") -> SectorListResponse:
    """Return available sectors for the node palette."""
    market_upper = market.upper()
    if market_upper not in ("KOSPI", "KOSDAQ"):
        raise HTTPException(
            status_code=400,
            detail=f"Sector listing is only supported for KOSPI and KOSDAQ, got: {market}",
        )
    try:
        fetcher = get_sector_fetcher()
        sector_counts = fetcher.get_sector_counts(market_upper)
        sectors = [
            SectorInfo(name=name, stock_count=count)
            for name, count in sorted(sector_counts.items())
        ]
        return SectorListResponse(
            market=market_upper,
            sectors=sectors,
            total_sectors=len(sectors),
        )
    except Exception as e:
        logger.exception("Failed to fetch sectors for %s", market)
        raise HTTPException(status_code=500, detail="Failed to fetch sector data")


@router.post(
    "/run",
    response_model=StrategyExecuteResponse,
    summary="Execute visual strategy",
    description="Execute a visual strategy graph and return screening results.",
)
async def run_strategy(request: StrategyExecuteRequest) -> StrategyExecuteResponse:
    """Execute a visual strategy graph."""
    candidate_universes = list(request.universe_overrides)
    if not candidate_universes:
        for node in request.graph.nodes:
            if node.data.node_type == "universe":
                candidate_universes.extend(node.data.universes or ([node.data.universe] if node.data.universe else []))
                break
    invalid_universes = find_invalid_universes(candidate_universes)
    if invalid_universes:
        raise HTTPException(status_code=400, detail=format_invalid_universe_error(invalid_universes))

    try:
        result = execute_strategy(
            graph=request.graph,
            universe_override=request.universe_override,
            universe_overrides=request.universe_overrides,
            portfolio_construction=request.portfolio_construction,
            ranking_config=request.ranking_config,
        )
        response_universes = result.get("universes") or request.universe_overrides or [result["universe"]]
        return StrategyExecuteResponse(**result, universes=response_universes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Strategy execution failed")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.post(
    "/run/stream",
    summary="Execute visual strategy with SSE progress",
    description="Execute a visual strategy graph and stream progress events via SSE.",
)
async def run_strategy_stream(request: StrategyExecuteRequest):
    """Execute a visual strategy graph with streaming progress events."""
    candidate_universes = list(request.universe_overrides)
    if not candidate_universes:
        for node in request.graph.nodes:
            if node.data.node_type == "universe":
                candidate_universes.extend(node.data.universes or ([node.data.universe] if node.data.universe else []))
                break
    invalid_universes = find_invalid_universes(candidate_universes)
    if invalid_universes:
        raise HTTPException(status_code=400, detail=format_invalid_universe_error(invalid_universes))

    progress_queue: queue.Queue = queue.Queue(maxsize=100)
    cancel_event = threading.Event()

    def _progress_cb(processed: int, total: int, matched: int) -> None:
        if cancel_event.is_set():
            return
        # Throttle: emit at most ~50 progress events
        interval = max(1, -(-total // 50))  # ceil division
        if processed % interval != 0 and processed != total:
            return
        try:
            progress_queue.put_nowait(
                StrategyProgressEvent(
                    processed_tickers=processed,
                    total_tickers=total,
                    matched_count=matched,
                    progress_pct=round(processed / total * 100, 1) if total else 0,
                    status="running",
                )
            )
        except queue.Full:
            pass

    def _run():
        try:
            # Skip enrichment here — do it after sending 'done' so the
            # client sees progress reach 100% without waiting for API calls.
            result = execute_strategy_with_progress(
                graph=request.graph,
                universe_override=request.universe_override,
                universe_overrides=request.universe_overrides,
                portfolio_construction=request.portfolio_construction,
                ranking_config=request.ranking_config,
                progress_callback=_progress_cb,
                skip_enrich=True,
            )
            result["universes"] = result.get("universes") or request.universe_overrides or [result["universe"]]
            if cancel_event.is_set():
                return
            screened = result.get("screened_count", result["total_count"])
            try:
                progress_queue.put(
                    StrategyProgressEvent(
                        processed_tickers=screened,
                        total_tickers=screened,
                        matched_count=result["matched_count"],
                        progress_pct=100.0,
                        status="done",
                    ),
                    timeout=5,
                )
            except queue.Full:
                return
            if cancel_event.is_set():
                return
            # Enrich fundamentals (PER/PBR) after 'done' event is sent.
            # Failure is non-fatal — return results without PER/PBR.
            try:
                enrich_fundamentals(result["results"])
            except Exception:
                logger.warning("Enrichment failed; returning results without fundamentals")
            if cancel_event.is_set():
                return
            try:
                progress_queue.put(result, timeout=5)
            except queue.Full:
                pass
        except Exception as e:
            logger.exception("Strategy streaming execution failed")
            if cancel_event.is_set():
                return
            try:
                progress_queue.put(
                    StrategyProgressEvent(
                        status="error",
                        message="Strategy execution failed. Check server logs for details.",
                    ),
                    timeout=5,
                )
            except queue.Full:
                pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    def event_stream():
        start = time.monotonic()
        max_duration = 600  # 10 minutes absolute limit
        try:
            while True:
                if time.monotonic() - start > max_duration:
                    yield f"event: error\ndata: {json.dumps({'status': 'error', 'message': 'Maximum duration exceeded'})}\n\n"
                    break
                try:
                    item = progress_queue.get(timeout=5)
                except queue.Empty:
                    # Heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
                    continue

                if isinstance(item, StrategyProgressEvent):
                    yield f"event: progress\ndata: {item.model_dump_json()}\n\n"
                    if item.status in ("done", "error"):
                        if item.status == "done":
                            # Wait for enriched result with heartbeats
                            final = None
                            for _ in range(6):  # 6 x 5s = 30s max
                                try:
                                    final = progress_queue.get(timeout=5)
                                    break
                                except queue.Empty:
                                    yield ": heartbeat\n\n"
                            if final is not None:
                                resp = StrategyExecuteResponse(**final)
                                yield f"event: result\ndata: {resp.model_dump_json()}\n\n"
                        break
                elif isinstance(item, dict):
                    resp = StrategyExecuteResponse(**item)
                    yield f"event: result\ndata: {resp.model_dump_json()}\n\n"
                    break
        finally:
            cancel_event.set()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/chat",
    summary="Chat with strategy assistant",
    description="Send a message to the AI strategy assistant. Returns SSE stream.",
)
async def strategy_chat(request: StrategyChatRequest):
    """Stream AI chat responses for strategy building assistance."""
    from api.services.strategy_chat_service import get_strategy_chat_service

    service = get_strategy_chat_service()
    if not service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Strategy chat not available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.",
        )

    def event_stream():
        from api.services.strategy_chat_service import parse_structured_payload
        from api.services.strategy_node_mapper import map_suggestions_to_nodes

        try:
            full_text = ""
            for chunk in service.stream_chat(
                [{"role": m.role, "content": m.content} for m in request.messages],
                request.graph,
                locale=request.locale,
            ):
                full_text += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            clean_text, payload = parse_structured_payload(full_text)
            if payload:
                node_mappings = []
                if payload.get("suggestions"):
                    try:
                        node_mappings = map_suggestions_to_nodes(payload["suggestions"])
                    except Exception:
                        logger.warning("Failed to map suggestions to nodes")
                yield f"data: {json.dumps({'type': 'structured_payload', 'payload': payload, 'clean_text': clean_text, 'node_mappings': node_mappings})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.exception("Strategy chat failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred while processing your request.'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/chat/validate",
    response_model=ValidatePayloadResponse,
    summary="Validate assistant suggestions",
    description="Validate condition suggestions from the AI assistant against the registry.",
)
async def validate_chat_payload(
    request: ValidatePayloadRequest,
) -> ValidatePayloadResponse:
    """Validate structured suggestions against condition registry."""
    from api.services.strategy_chat_service import validate_suggestions

    results = validate_suggestions(
        [s.model_dump() for s in request.suggestions]
    )
    return ValidatePayloadResponse(
        results=results,
        all_valid=all(r["valid"] for r in results),
    )
