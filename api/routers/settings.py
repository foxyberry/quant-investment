"""Settings router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from brokers.base import ConnectionState
from brokers.exceptions import BrokerConnectionError

from api.schemas.broker import (
    BrokerConnectionResponse,
    BrokerSettingsResponse,
    IBKRSettingsRequest,
    IBKRSettingsResponse,
    TigerSettingsRequest,
    TigerSettingsResponse,
)
from api.schemas.telegram import (
    TelegramSettingsRequest,
    TelegramSettingsResponse,
    TelegramTestResponse,
)
from api.schemas.slack import (
    SlackSettingsRequest,
    SlackSettingsResponse,
    SlackTestResponse,
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


# -- IBKR settings ----------------------------------------------------------


@router.get(
    "/brokers/ibkr",
    response_model=IBKRSettingsResponse,
    summary="Get IBKR broker settings",
)
def get_ibkr_settings() -> IBKRSettingsResponse:
    view = _settings_service.get_ibkr_settings()
    return IBKRSettingsResponse(
        gateway_url=view.gateway_url,
        account_id=view.account_id,
        updated_at=view.updated_at,
    )


@router.put(
    "/brokers/ibkr",
    response_model=IBKRSettingsResponse,
    summary="Save IBKR broker settings",
)
def save_ibkr_settings(request: IBKRSettingsRequest) -> IBKRSettingsResponse:
    try:
        view = _settings_service.save_ibkr_settings(request.model_dump())
        return IBKRSettingsResponse(
            gateway_url=view.gateway_url,
            account_id=view.account_id,
            updated_at=view.updated_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/brokers/ibkr/test",
    response_model=BrokerConnectionResponse,
    summary="Test IBKR broker connection",
)
def test_ibkr_connection() -> BrokerConnectionResponse:
    try:
        _settings_service.apply_ibkr_settings_to_runtime()
        status = _service.get_connection_status("ibkr")
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


# -- Telegram settings -------------------------------------------------------


@router.get(
    "/telegram",
    response_model=TelegramSettingsResponse,
    summary="Get Telegram notification settings",
)
def get_telegram_settings() -> TelegramSettingsResponse:
    view = _settings_service.get_telegram_settings()
    return TelegramSettingsResponse(
        has_bot_token=view.has_bot_token,
        chat_id=view.chat_id,
        enabled=view.enabled,
        updated_at=view.updated_at,
    )


@router.put(
    "/telegram",
    response_model=TelegramSettingsResponse,
    summary="Save Telegram notification settings",
)
def save_telegram_settings(request: TelegramSettingsRequest) -> TelegramSettingsResponse:
    try:
        view = _settings_service.save_telegram_settings(request.model_dump())
        return TelegramSettingsResponse(
            has_bot_token=view.has_bot_token,
            chat_id=view.chat_id,
            enabled=view.enabled,
            updated_at=view.updated_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/telegram/test",
    response_model=TelegramTestResponse,
    summary="Send test Telegram notification",
)
def test_telegram_notification() -> TelegramTestResponse:
    view = _settings_service.get_telegram_settings()
    if not view.has_bot_token or not view.chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram settings are not configured. Save bot_token and chat_id first.",
        )

    import json as _json

    from api.database import SessionLocal as _SessionLocal
    from api.models.broker_credential import BrokerCredential as _BC

    db = _SessionLocal()
    try:
        row = db.get(_BC, "telegram")
        if not row:
            raise HTTPException(status_code=400, detail="Telegram settings not found")
        data = _json.loads(row.config_json)
        encrypted_token = data.get("bot_token_encrypted", "")
    finally:
        db.close()

    if not encrypted_token:
        raise HTTPException(
            status_code=400,
            detail="Bot token is missing. Please save your bot token first.",
        )

    try:
        ok = _settings_service.send_telegram_message(view.chat_id, encrypted_token)
    except RuntimeError as exc:
        msg = str(exc)
        if "decrypt" in msg.lower():
            msg = "Encryption key mismatch. Please re-save your bot token."
        return TelegramTestResponse(success=False, message=msg)
    if ok:
        return TelegramTestResponse(success=True, message="Test message sent successfully")
    return TelegramTestResponse(
        success=False,
        message="Failed to send test message. Check your bot token and chat ID.",
    )


# ------------------------------------------------------------------
# Slack notification settings
# ------------------------------------------------------------------

@router.get(
    "/slack",
    response_model=SlackSettingsResponse,
    summary="Get Slack notification settings",
)
def get_slack_settings() -> SlackSettingsResponse:
    view = _settings_service.get_slack_settings()
    return SlackSettingsResponse(
        has_webhook_url=view.has_webhook_url,
        channel_name=view.channel_name,
        enabled=view.enabled,
        updated_at=view.updated_at,
    )


@router.put(
    "/slack",
    response_model=SlackSettingsResponse,
    summary="Save Slack notification settings",
)
def save_slack_settings(request: SlackSettingsRequest) -> SlackSettingsResponse:
    try:
        view = _settings_service.save_slack_settings(request.model_dump())
        return SlackSettingsResponse(
            has_webhook_url=view.has_webhook_url,
            channel_name=view.channel_name,
            enabled=view.enabled,
            updated_at=view.updated_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/slack/test",
    response_model=SlackTestResponse,
    summary="Send test Slack notification",
)
def test_slack_notification() -> SlackTestResponse:
    ok = _settings_service.send_slack_test()
    if ok:
        return SlackTestResponse(success=True, message="Test message sent to Slack")
    return SlackTestResponse(success=False, message="Failed to send. Check webhook URL.")
