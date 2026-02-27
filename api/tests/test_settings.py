"""Tests for settings router."""

from types import SimpleNamespace
from unittest.mock import patch

from brokers.base import ConnectionState
from brokers.exceptions import BrokerConnectionError


def test_list_settings_brokers_returns_statuses(client):
    status = SimpleNamespace(
        broker="kiwoom",
        status=ConnectionState.CONNECTED,
        is_paper_trading=True,
        accounts=["12345678"],
        updated_at="2026-02-26T00:00:00Z",
    )

    with patch("api.routers.settings._service.list_brokers", return_value=["kiwoom"]):
        with patch("api.routers.settings._service.get_connection_status", return_value=status):
            response = client.get("/api/settings/brokers")

    assert response.status_code == 200
    data = response.json()
    assert "brokers" in data
    assert len(data["brokers"]) == 1
    assert data["brokers"][0]["broker"] == "kiwoom"
    assert data["brokers"][0]["status"] == "connected"


def test_list_settings_brokers_marks_unavailable_on_connection_error(client):
    with patch("api.routers.settings._service.list_brokers", return_value=["tiger"]):
        with patch(
            "api.routers.settings._service.get_connection_status",
            side_effect=BrokerConnectionError("down"),
        ):
            response = client.get("/api/settings/brokers")

    assert response.status_code == 200
    data = response.json()
    assert data["brokers"][0]["broker"] == "tiger"
    assert data["brokers"][0]["status"] == "unavailable"


def test_get_tiger_settings(client):
    view = SimpleNamespace(
        tiger_id="demo-id",
        account="1234567890",
        license="TBNZ",
        sandbox=True,
        has_private_key=True,
        updated_at="2026-02-27T00:00:00Z",
    )
    with patch("api.routers.settings._settings_service.get_tiger_settings", return_value=view):
        response = client.get("/api/settings/brokers/tiger")

    assert response.status_code == 200
    data = response.json()
    assert data["tiger_id"] == "demo-id"
    assert data["has_private_key"] is True


def test_put_tiger_settings(client):
    view = SimpleNamespace(
        tiger_id="demo-id",
        account="1234567890",
        license="TBNZ",
        sandbox=False,
        has_private_key=True,
        updated_at="2026-02-27T00:00:00Z",
    )
    with patch("api.routers.settings._settings_service.save_tiger_settings", return_value=view):
        response = client.put(
            "/api/settings/brokers/tiger",
            json={
                "tiger_id": "demo-id",
                "account": "1234567890",
                "private_key": "pem",
                "license": "TBNZ",
                "sandbox": False,
            },
        )

    assert response.status_code == 200
    assert response.json()["account"] == "1234567890"


def test_test_tiger_connection(client):
    status = SimpleNamespace(
        broker="tiger",
        status=ConnectionState.CONNECTED,
        is_paper_trading=False,
        accounts=["1234567890"],
        updated_at="2026-02-27T00:00:00Z",
    )
    with patch("api.routers.settings._settings_service.apply_tiger_settings_to_runtime"):
        with patch("api.routers.settings._service.get_connection_status", return_value=status):
            response = client.post("/api/settings/brokers/tiger/test")

    assert response.status_code == 200
    data = response.json()
    assert data["broker"] == "tiger"
    assert data["status"] == "connected"
