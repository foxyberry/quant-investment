"""
Unified broker router.

Provides broker-agnostic endpoints for order management, connection
status, and kill-switch activation.  Works with any adapter registered
in the :class:`BrokerRegistry` (kiwoom, ibkr, tiger, ...).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from brokers.base import AmendRequest, OrderRequest
from brokers.exceptions import (
    BrokerConnectionError,
    BrokerSafetyError,
    BrokerValidationError,
    OrderNotFoundError,
)

from api.schemas.broker import (
    BrokerAmendRequest,
    BrokerConnectionResponse,
    BrokerKillSwitchResponse,
    BrokerListResponse,
    BrokerOrderRequest,
    BrokerOrderResponse,
)
from api.services.broker_service import BrokerService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/brokers",
    tags=["Unified Broker"],
    responses={
        404: {"description": "Broker or order not found"},
        503: {"description": "Broker connection unavailable"},
    },
)

_service = BrokerService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_adapter_or_404(broker: str):
    """Validate that *broker* is registered; raise 404 otherwise."""
    try:
        return _service.get_adapter(broker)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Broker '{broker}' is not registered",
        )


# ---------------------------------------------------------------------------
# Broker list
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=BrokerListResponse,
    summary="List Brokers",
    description="Return all registered broker names.",
)
def list_brokers() -> BrokerListResponse:
    return BrokerListResponse(brokers=_service.list_brokers())


# ---------------------------------------------------------------------------
# Connection status
# ---------------------------------------------------------------------------


@router.get(
    "/{broker}/status",
    response_model=BrokerConnectionResponse,
    summary="Get Connection Status",
    description="Return the connection status for a specific broker.",
)
def get_connection_status(broker: str) -> BrokerConnectionResponse:
    _get_adapter_or_404(broker)
    try:
        status = _service.get_connection_status(broker)
        return BrokerConnectionResponse(
            broker=status.broker,
            status=status.status,
            is_paper_trading=status.is_paper_trading,
            accounts=status.accounts,
            updated_at=status.updated_at,
        )
    except BrokerConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get connection status for %s", broker)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@router.post(
    "/{broker}/orders",
    response_model=BrokerOrderResponse,
    summary="Place Order",
    description="Submit a new order through the specified broker.",
    status_code=201,
)
def place_order(
    broker: str, request: BrokerOrderRequest
) -> BrokerOrderResponse:
    _get_adapter_or_404(broker)
    try:
        order_request = OrderRequest(
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            price=request.price,
            account_id=request.account_id,
        )
        snapshot = _service.place_order(broker, order_request)
        return BrokerOrderResponse(**snapshot.model_dump())
    except (BrokerValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BrokerConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BrokerSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to place order on %s", broker)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get(
    "/{broker}/orders",
    response_model=list[BrokerOrderResponse],
    summary="List Orders",
    description="Retrieve all tracked orders for the specified broker.",
)
def get_orders(broker: str) -> list[BrokerOrderResponse]:
    _get_adapter_or_404(broker)
    try:
        snapshots = _service.get_orders(broker)
        return [BrokerOrderResponse(**s.model_dump()) for s in snapshots]
    except BrokerConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get orders for %s", broker)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.delete(
    "/{broker}/orders/{order_id}",
    status_code=204,
    summary="Cancel Order",
    description="Cancel an open order by its ID.",
)
def cancel_order(broker: str, order_id: str) -> None:
    _get_adapter_or_404(broker)
    try:
        _service.cancel_order(broker, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BrokerConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BrokerSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to cancel order %s on %s", order_id, broker)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.patch(
    "/{broker}/orders/{order_id}",
    status_code=204,
    summary="Amend Order",
    description="Modify quantity and/or price of an open order.",
)
def amend_order(
    broker: str, order_id: str, request: BrokerAmendRequest
) -> None:
    _get_adapter_or_404(broker)
    try:
        amend_req = AmendRequest(
            quantity=request.quantity,
            price=request.price,
        )
        _service.amend_order(broker, order_id, amend_req)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (BrokerValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BrokerConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BrokerSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to amend order %s on %s", order_id, broker)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------


@router.post(
    "/{broker}/kill-switch",
    response_model=BrokerKillSwitchResponse,
    summary="Activate Kill Switch",
    description="Emergency stop: cancel all open orders and block new ones.",
)
def activate_kill_switch(broker: str) -> BrokerKillSwitchResponse:
    _get_adapter_or_404(broker)
    try:
        result = _service.activate_kill_switch(broker)
        return BrokerKillSwitchResponse(
            activated=result.activated,
            cancelled_orders=result.cancelled_orders,
        )
    except BrokerConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to activate kill switch on %s", broker)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
