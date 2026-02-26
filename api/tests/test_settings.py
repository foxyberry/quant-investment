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
