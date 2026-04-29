"""
Kiwoom trading router.

Provides endpoints for Kiwoom OpenAPI+ integration including
connection status, order management, and condition search.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from brokers.kiwoom.safety import SafetyViolation

from api.schemas.kiwoom import (
    KiwoomAmendRequest,
    KiwoomConditionMatch,
    KiwoomConditionMatchesResponse,
    KiwoomConditionStartRequest,
    KiwoomConditionsResponse,
    KiwoomConditionStopRequest,
    KiwoomConnectionStatus,
    KiwoomKillSwitchResponse,
    KiwoomOrder,
    KiwoomOrderRequest,
    KiwoomOrdersResponse,
)
from api.services.kiwoom_service import KiwoomService
from api.services.ws_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/kiwoom",
    tags=["Kiwoom Trading"],
    responses={
        503: {"description": "Kiwoom connection unavailable"},
        500: {"description": "Internal server error"},
    },
)

# Service instance (singleton)
_service = KiwoomService.get_instance()


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


@router.get(
    "/connection/status",
    response_model=KiwoomConnectionStatus,
    summary="Get Connection Status",
    description="Retrieve current Kiwoom connection status.",
)
def get_connection_status() -> KiwoomConnectionStatus:
    """
    Get Kiwoom connection status.

    Returns:
        KiwoomConnectionStatus with connection state, accounts, and user info.
    """
    try:
        result = _service.get_connection_status()
        return KiwoomConnectionStatus(**result)
    except Exception as exc:
        logger.exception("Failed to get connection status")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@router.post(
    "/orders",
    response_model=KiwoomOrder,
    summary="Place Order",
    description="Submit a new buy or sell order.",
    status_code=201,
)
def place_order(request: KiwoomOrderRequest) -> KiwoomOrder:
    """
    Place a new order.

    Args:
        request: Order placement request body.

    Returns:
        KiwoomOrder with the created order snapshot.

    Raises:
        HTTPException: 400 for validation errors, 409 for safety violations,
                       503 if not connected.
    """
    try:
        result = _service.place_order(
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            price=request.price,
        )
        return KiwoomOrder(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        msg = str(exc)
        if "no accounts" in msg.lower():
            raise HTTPException(status_code=503, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc
    except SafetyViolation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to place order")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/orders",
    response_model=KiwoomOrdersResponse,
    summary="List Orders",
    description="Retrieve all tracked orders.",
)
def get_orders() -> KiwoomOrdersResponse:
    """
    List all tracked orders.

    Returns:
        KiwoomOrdersResponse with list of order snapshots.
    """
    try:
        orders = _service.get_orders()
        return KiwoomOrdersResponse(orders=orders)
    except Exception as exc:
        logger.exception("Failed to get orders")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/orders/{order_id}/cancel",
    status_code=204,
    summary="Cancel Order",
    description="Cancel an open order by its ID.",
)
def cancel_order(order_id: str) -> None:
    """
    Cancel an open order.

    Args:
        order_id: Order identifier.

    Raises:
        HTTPException: 404 if order not found, 409 for safety violations.
    """
    try:
        _service.cancel_order(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except SafetyViolation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to cancel order %s", order_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/orders/{order_id}/amend",
    status_code=204,
    summary="Amend Order",
    description="Modify quantity and/or price of an open order.",
)
def amend_order(order_id: str, request: KiwoomAmendRequest) -> None:
    """
    Amend (modify) an open order.

    Args:
        order_id: Order identifier.
        request: Amendment request with optional quantity and/or price.

    Raises:
        HTTPException: 404 if order not found, 400 for validation errors.
    """
    try:
        _service.amend_order(
            order_id=order_id,
            quantity=request.quantity,
            price=request.price,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except SafetyViolation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to amend order %s", order_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/orders/kill-switch",
    response_model=KiwoomKillSwitchResponse,
    summary="Activate Kill Switch",
    description="Emergency stop: cancel all open orders and block new ones.",
)
def activate_kill_switch() -> KiwoomKillSwitchResponse:
    """
    Activate the emergency kill switch.

    Cancels all open orders and prevents new order submissions.

    Returns:
        KiwoomKillSwitchResponse with activation status and cancelled count.
    """
    try:
        result = _service.activate_kill_switch()
        return KiwoomKillSwitchResponse(**result)
    except Exception as exc:
        logger.exception("Failed to activate kill switch")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------


@router.get(
    "/conditions",
    response_model=KiwoomConditionsResponse,
    summary="List Conditions",
    description="Retrieve available Kiwoom conditions.",
)
def get_conditions() -> KiwoomConditionsResponse:
    """
    List available Kiwoom conditions.

    Returns:
        KiwoomConditionsResponse with list of condition definitions.
    """
    try:
        conditions = _service.get_conditions()
        return KiwoomConditionsResponse(conditions=conditions)
    except Exception as exc:
        logger.exception("Failed to get conditions")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/conditions/start",
    summary="Start Condition Monitoring",
    description="Start realtime monitoring for a condition.",
    status_code=200,
)
def start_condition(request: KiwoomConditionStartRequest) -> dict:
    """
    Start realtime condition monitoring.

    Args:
        request: Condition start request with index and name.

    Returns:
        dict with condition_index, condition_name, and screen_no.

    Raises:
        HTTPException: 400 for validation errors, 409 if limit reached.
    """
    try:
        result = _service.start_condition(
            index=request.condition_index,
            name=request.condition_name,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        msg = str(exc)
        if "limit" in msg.lower():
            raise HTTPException(status_code=409, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc
    except Exception as exc:
        logger.exception("Failed to start condition monitoring")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/conditions/stop",
    summary="Stop Condition Monitoring",
    description="Stop realtime monitoring for a condition.",
    status_code=200,
)
def stop_condition(request: KiwoomConditionStopRequest) -> dict:
    """
    Stop realtime condition monitoring.

    Args:
        request: Condition stop request with index and name.

    Returns:
        dict with condition_index, condition_name, and stopped flag.
    """
    try:
        result = _service.stop_condition(
            index=request.condition_index,
            name=request.condition_name,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to stop condition monitoring")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/conditions/matches",
    response_model=KiwoomConditionMatchesResponse,
    summary="Get Condition Matches",
    description="Retrieve stocks currently matching a monitored condition.",
)
def get_condition_matches(
    condition_index: int = Query(..., ge=0, description="Condition index"),
    condition_name: str = Query(..., min_length=1, description="Condition name"),
) -> KiwoomConditionMatchesResponse:
    """
    Get stocks matching a monitored condition.

    Args:
        condition_index: Condition index (query parameter).
        condition_name: Condition name (query parameter).

    Returns:
        KiwoomConditionMatchesResponse with list of matching stocks.
    """
    try:
        matches = _service.get_condition_matches(
            index=condition_index,
            name=condition_name,
        )
        return KiwoomConditionMatchesResponse(matches=matches)
    except Exception as exc:
        logger.exception("Failed to get condition matches")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

# Connection managers -- one per event stream
_order_ws_manager = ConnectionManager()
_condition_ws_manager = ConnectionManager()


def _setup_ws_bridges() -> None:
    """Wire kiwoom observer callbacks to WebSocket broadcast.

    Kiwoom callbacks fire from synchronous code, so the bridge functions
    obtain the running asyncio event loop and schedule the broadcast as
    a coroutine (``ensure_future``).  If no loop is available the event
    is silently dropped -- this only happens during shutdown.
    """
    import asyncio

    service = KiwoomService.get_instance()

    def _on_chejan(payload: dict) -> None:
        """Bridge ChejanHandler events to the order WebSocket stream."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_order_ws_manager.broadcast(payload))
        except RuntimeError:
            pass

    def _on_condition(payload: dict) -> None:
        """Bridge ConditionSearchManager events to the condition WebSocket stream."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_condition_ws_manager.broadcast(payload))
        except RuntimeError:
            pass

    service._chejan.add_observer(_on_chejan)
    service._condition_manager.add_observer(_on_condition)
    logger.info("WebSocket bridges registered for chejan and condition events")


# Initialise bridges eagerly.  If the service is not yet available (e.g.
# unit tests importing the module in isolation) the failure is non-fatal.
try:
    _setup_ws_bridges()
except Exception:
    logger.warning(
        "Failed to setup WebSocket bridges (service may not be initialised)"
    )


@router.websocket("/orders/ws")
async def orders_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time order/fill updates.

    Clients receive JSON messages pushed by the ChejanHandler observer
    whenever an order status or balance event occurs.  The client may
    send ``"ping"`` at any time and will receive ``"pong"`` in return.
    """
    await _order_ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        _order_ws_manager.disconnect(websocket)
    except Exception:
        _order_ws_manager.disconnect(websocket)


@router.websocket("/conditions/ws")
async def conditions_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time condition match updates.

    Clients receive JSON messages pushed by the ConditionSearchManager
    observer whenever a stock enters or leaves a monitored condition.
    The client may send ``"ping"`` at any time and will receive
    ``"pong"`` in return.
    """
    await _condition_ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        _condition_ws_manager.disconnect(websocket)
    except Exception:
        _condition_ws_manager.disconnect(websocket)
