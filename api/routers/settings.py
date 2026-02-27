"""Settings router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from brokers.base import ConnectionState
from brokers.exceptions import BrokerConnectionError

from api.schemas.broker import (
    BrokerConnectionResponse,
    BrokerSettingsResponse,
    TigerSettingsRequest,
    TigerSettingsResponse,
)
from api.services.broker_service import BrokerService
from api.services.broker_settings_service import get_broker_settings_service

router = APIRouter(prefix="/api/settings", tags=["Settings"])

_service = BrokerService()
_settings_service = get_broker_settings_service()


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


@router.get(
    "/brokers/tiger",
    response_model=TigerSettingsResponse,
    summary="Get Tiger broker settings",
)
def get_tiger_settings() -> TigerSettingsResponse:
    view = _settings_service.get_tiger_settings()
    return TigerSettingsResponse(
        tiger_id=view.tiger_id,
        account=view.account,
        license=view.license,
        sandbox=view.sandbox,
        has_private_key=view.has_private_key,
        updated_at=view.updated_at,
    )


@router.put(
    "/brokers/tiger",
    response_model=TigerSettingsResponse,
    summary="Save Tiger broker settings",
)
def save_tiger_settings(request: TigerSettingsRequest) -> TigerSettingsResponse:
    try:
        view = _settings_service.save_tiger_settings(request.model_dump())
        return TigerSettingsResponse(
            tiger_id=view.tiger_id,
            account=view.account,
            license=view.license,
            sandbox=view.sandbox,
            has_private_key=view.has_private_key,
            updated_at=view.updated_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/brokers/tiger/test",
    response_model=BrokerConnectionResponse,
    summary="Test Tiger broker connection",
)
def test_tiger_connection() -> BrokerConnectionResponse:
    try:
        _settings_service.apply_tiger_settings_to_runtime()
        status = _service.get_connection_status("tiger")
        return BrokerConnectionResponse(
            broker=status.broker,
            status=status.status,
            is_paper_trading=status.is_paper_trading,
            accounts=status.accounts,
            updated_at=status.updated_at,
        )
    except BrokerConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
