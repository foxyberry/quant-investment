"""Settings router."""

from __future__ import annotations

from fastapi import APIRouter

from brokers.base import ConnectionState
from brokers.exceptions import BrokerConnectionError

from api.schemas.broker import BrokerConnectionResponse, BrokerSettingsResponse
from api.services.broker_service import BrokerService

router = APIRouter(prefix="/api/settings", tags=["Settings"])

_service = BrokerService()


@router.get(
    "/brokers",
    response_model=BrokerSettingsResponse,
    summary="List broker statuses for settings",
    description="Return connection status snapshots for all registered brokers.",
)
def list_settings_brokers() -> BrokerSettingsResponse:
    brokers: list[BrokerConnectionResponse] = []
    for name in _service.list_brokers():
        try:
            status = _service.get_connection_status(name)
            brokers.append(
                BrokerConnectionResponse(
                    broker=status.broker,
                    status=status.status,
                    is_paper_trading=status.is_paper_trading,
                    accounts=status.accounts,
                    updated_at=status.updated_at,
                )
            )
        except BrokerConnectionError:
            brokers.append(
                BrokerConnectionResponse(
                    broker=name,
                    status=ConnectionState.UNAVAILABLE,
                    is_paper_trading=None,
                    accounts=[],
                    updated_at=None,
                )
            )
        except Exception:
            brokers.append(
                BrokerConnectionResponse(
                    broker=name,
                    status=ConnectionState.UNAVAILABLE,
                    is_paper_trading=None,
                    accounts=[],
                    updated_at=None,
                )
            )
    return BrokerSettingsResponse(brokers=brokers)
