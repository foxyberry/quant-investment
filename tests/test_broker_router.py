"""Unit tests for the unified broker router (``api/routers/broker.py``).

All adapter interactions are mocked -- no live broker connection is needed.
The ``api.routers.kiwoom`` module initialises ``KiwoomService`` and
WebSocket bridges at import time, which would fail in test environments.
We patch those before ``api.main`` (and thus the kiwoom router) is imported.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from brokers.base import (
    ConnectionState,
    ConnectionStatus,
    KillSwitchResult,
    OrderSide,
    OrderSnapshot,
    OrderStatus,
    OrderType,
)
from brokers.exceptions import (
    BrokerConnectionError,
    BrokerSafetyError,
    BrokerValidationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_service():
    """Patch ``BrokerService`` at module level in the broker router.

    The broker router creates ``_service = BrokerService()`` at import time,
    so we must patch the *instance* methods used by the route handlers.  We
    achieve this by patching the class in ``api.routers.broker`` before
    the test runs, and then replace the module-level ``_service`` object.
    """
    mock_svc = MagicMock()
    with patch("api.routers.broker._service", mock_svc):
        yield mock_svc


@pytest.fixture()
def client(mock_service):
    """Return a ``TestClient`` wired to the real FastAPI app.

    The kiwoom router performs eager initialisation at import time
    (``KiwoomService.get_instance()`` and ``_setup_ws_bridges``).  We
    patch those *before* importing ``api.main`` to prevent ImportError
    on platforms without the Kiwoom COM library.
    """
    # We need to patch the kiwoom service singleton that runs at import
    # time.  Since api.main imports api.routers.kiwoom (directly *and*
    # via the __init__), we patch right on the service module.
    with (
        patch(
            "api.services.kiwoom_service.KiwoomService.get_instance",
            return_value=MagicMock(),
        ),
        patch("api.services.kiwoom_service.KiwoomConnection", MagicMock()),
        patch("api.services.kiwoom_service.KiwoomOrderManager", MagicMock()),
        patch("api.services.kiwoom_service.ChejanHandler", MagicMock()),
        patch("api.services.kiwoom_service.ConditionSearchManager", MagicMock()),
        patch("api.services.kiwoom_service.KiwoomSafetyManager", MagicMock()),
        patch("api.services.kiwoom_service.AuditLogger", MagicMock()),
    ):
        from fastapi.testclient import TestClient

        from api.main import app

        yield TestClient(app)


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------


def _sample_order_snapshot(**overrides) -> OrderSnapshot:
    """Return a realistic ``OrderSnapshot`` with optional field overrides."""
    defaults = dict(
        order_id="ORD-001",
        broker="tiger",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=100,
        filled_quantity=0,
        unfilled_quantity=100,
        order_type=OrderType.MARKET,
        price=None,
        filled_price=None,
        status=OrderStatus.RECEIVED,
        created_at="2026-02-25T10:00:00Z",
        updated_at=None,
    )
    defaults.update(overrides)
    return OrderSnapshot(**defaults)


def _sample_connection_status(**overrides) -> ConnectionStatus:
    defaults = dict(
        broker="tiger",
        status=ConnectionState.CONNECTED,
        is_paper_trading=True,
        accounts=["ACCT-1"],
        updated_at="2026-02-25T10:00:00Z",
    )
    defaults.update(overrides)
    return ConnectionStatus(**defaults)


# =========================================================================
# 1. GET /api/brokers/ -- list brokers
# =========================================================================


class TestListBrokers:
    def test_list_brokers(self, client, mock_service) -> None:
        mock_service.list_brokers.return_value = ["ibkr", "kiwoom", "tiger"]

        resp = client.get("/api/brokers/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["brokers"] == ["ibkr", "kiwoom", "tiger"]

    def test_list_brokers_empty(self, client, mock_service) -> None:
        mock_service.list_brokers.return_value = []

        resp = client.get("/api/brokers/")
        assert resp.status_code == 200
        assert resp.json()["brokers"] == []


# =========================================================================
# 2. GET /api/brokers/{broker}/status -- connection status
# =========================================================================


class TestConnectionStatus:
    def test_connection_status(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.get_connection_status.return_value = _sample_connection_status()

        resp = client.get("/api/brokers/tiger/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["broker"] == "tiger"
        assert body["status"] == "connected"
        assert body["is_paper_trading"] is True
        assert body["accounts"] == ["ACCT-1"]

    def test_connection_error_503(self, client, mock_service) -> None:
        """Adapter raises BrokerConnectionError => 503."""
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.get_connection_status.side_effect = BrokerConnectionError(
            "Gateway unreachable"
        )

        resp = client.get("/api/brokers/tiger/status")
        assert resp.status_code == 503
        assert "Gateway unreachable" in resp.json()["detail"]


# =========================================================================
# 3. POST /api/brokers/{broker}/orders -- place order
# =========================================================================


class TestPlaceOrder:
    def test_place_market_order(self, client, mock_service) -> None:
        snapshot = _sample_order_snapshot()
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.place_order.return_value = snapshot

        resp = client.post(
            "/api/brokers/tiger/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 100,
                "order_type": "MARKET",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["order_id"] == "ORD-001"
        assert body["broker"] == "tiger"
        assert body["ticker"] == "AAPL"
        assert body["side"] == "BUY"
        assert body["quantity"] == 100
        assert body["order_type"] == "MARKET"
        assert body["status"] == "RECEIVED"

    def test_place_limit_order(self, client, mock_service) -> None:
        snapshot = _sample_order_snapshot(
            order_type=OrderType.LIMIT,
            price=150.50,
            status=OrderStatus.CONFIRMED,
        )
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.place_order.return_value = snapshot

        resp = client.post(
            "/api/brokers/tiger/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 50,
                "order_type": "LIMIT",
                "price": 150.50,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["order_type"] == "LIMIT"
        assert body["price"] == 150.50
        assert body["status"] == "CONFIRMED"

    def test_place_order_with_account_id(self, client, mock_service) -> None:
        snapshot = _sample_order_snapshot()
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.place_order.return_value = snapshot

        resp = client.post(
            "/api/brokers/tiger/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "order_type": "MARKET",
                "account_id": "ACCT-1",
            },
        )
        assert resp.status_code == 201

    def test_place_order_safety_error_409(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.place_order.side_effect = BrokerSafetyError(
            "Kill switch is active"
        )

        resp = client.post(
            "/api/brokers/tiger/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 100,
                "order_type": "MARKET",
            },
        )
        assert resp.status_code == 409
        assert "Kill switch" in resp.json()["detail"]

    def test_place_order_connection_error_503(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.place_order.side_effect = BrokerConnectionError(
            "Broker unreachable"
        )

        resp = client.post(
            "/api/brokers/tiger/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 100,
                "order_type": "MARKET",
            },
        )
        assert resp.status_code == 503

    def test_place_order_validation_error_400(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.place_order.side_effect = BrokerValidationError(
            "Insufficient funds"
        )

        resp = client.post(
            "/api/brokers/tiger/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 100,
                "order_type": "MARKET",
            },
        )
        assert resp.status_code == 400
        assert "Insufficient funds" in resp.json()["detail"]


# =========================================================================
# 4. GET /api/brokers/{broker}/orders -- list orders
# =========================================================================


class TestGetOrders:
    def test_get_orders(self, client, mock_service) -> None:
        snapshots = [
            _sample_order_snapshot(order_id="ORD-001"),
            _sample_order_snapshot(
                order_id="ORD-002",
                ticker="TSLA",
                side=OrderSide.SELL,
                status=OrderStatus.FILLED,
                filled_quantity=50,
                unfilled_quantity=0,
                filled_price=200.0,
            ),
        ]
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.get_orders.return_value = snapshots

        resp = client.get("/api/brokers/tiger/orders")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["order_id"] == "ORD-001"
        assert body[1]["order_id"] == "ORD-002"
        assert body[1]["ticker"] == "TSLA"
        assert body[1]["side"] == "SELL"
        assert body[1]["status"] == "FILLED"

    def test_get_orders_empty(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.get_orders.return_value = []

        resp = client.get("/api/brokers/tiger/orders")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_orders_connection_error_503(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.get_orders.side_effect = BrokerConnectionError("offline")

        resp = client.get("/api/brokers/tiger/orders")
        assert resp.status_code == 503


# =========================================================================
# 5. DELETE /api/brokers/{broker}/orders/{order_id} -- cancel order
# =========================================================================


class TestCancelOrder:
    def test_cancel_order(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.cancel_order.return_value = None

        resp = client.delete("/api/brokers/tiger/orders/123")
        assert resp.status_code == 204
        mock_service.cancel_order.assert_called_once_with("tiger", "123")

    def test_cancel_order_not_found(self, client, mock_service) -> None:
        from brokers.exceptions import OrderNotFoundError

        mock_service.get_adapter.return_value = MagicMock()
        mock_service.cancel_order.side_effect = OrderNotFoundError("Order 123 not found")

        resp = client.delete("/api/brokers/tiger/orders/123")
        assert resp.status_code == 404

    def test_cancel_order_safety_error_409(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.cancel_order.side_effect = BrokerSafetyError("Cannot cancel")

        resp = client.delete("/api/brokers/tiger/orders/123")
        assert resp.status_code == 409


# =========================================================================
# 6. PATCH /api/brokers/{broker}/orders/{order_id} -- amend order
# =========================================================================


class TestAmendOrder:
    def test_amend_order(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.amend_order.return_value = None

        resp = client.patch(
            "/api/brokers/tiger/orders/123",
            json={"quantity": 200},
        )
        assert resp.status_code == 204
        mock_service.amend_order.assert_called_once()
        call_args = mock_service.amend_order.call_args
        assert call_args[0][0] == "tiger"
        assert call_args[0][1] == "123"
        # Third arg is the AmendRequest
        amend_req = call_args[0][2]
        assert amend_req.quantity == 200

    def test_amend_order_price_only(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.amend_order.return_value = None

        resp = client.patch(
            "/api/brokers/tiger/orders/123",
            json={"price": 155.0},
        )
        assert resp.status_code == 204

    def test_amend_order_both_fields(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.amend_order.return_value = None

        resp = client.patch(
            "/api/brokers/tiger/orders/123",
            json={"quantity": 50, "price": 160.0},
        )
        assert resp.status_code == 204

    def test_validation_error_400_no_fields(self, client, mock_service) -> None:
        """Amend with no fields triggers ValueError from AmendRequest validator."""
        mock_service.get_adapter.return_value = MagicMock()
        # The AmendRequest model_validator raises ValueError when both
        # quantity and price are None.  The router catches (ValueError, BrokerValidationError) => 400.
        mock_service.amend_order.side_effect = ValueError(
            "at least one of quantity or price must be provided"
        )

        resp = client.patch(
            "/api/brokers/tiger/orders/123",
            json={},
        )
        assert resp.status_code == 400
        assert "at least one" in resp.json()["detail"]

    def test_amend_order_not_found(self, client, mock_service) -> None:
        from brokers.exceptions import OrderNotFoundError

        mock_service.get_adapter.return_value = MagicMock()
        mock_service.amend_order.side_effect = OrderNotFoundError("not found")

        resp = client.patch(
            "/api/brokers/tiger/orders/999",
            json={"quantity": 50},
        )
        assert resp.status_code == 404

    def test_amend_order_safety_error_409(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.amend_order.side_effect = BrokerSafetyError("blocked")

        resp = client.patch(
            "/api/brokers/tiger/orders/123",
            json={"quantity": 50},
        )
        assert resp.status_code == 409


# =========================================================================
# 7. POST /api/brokers/{broker}/kill-switch
# =========================================================================


class TestKillSwitch:
    def test_kill_switch(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.activate_kill_switch.return_value = KillSwitchResult(
            activated=True, cancelled_orders=3
        )

        resp = client.post("/api/brokers/tiger/kill-switch")
        assert resp.status_code == 200
        body = resp.json()
        assert body["activated"] is True
        assert body["cancelled_orders"] == 3

    def test_kill_switch_no_open_orders(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.activate_kill_switch.return_value = KillSwitchResult(
            activated=True, cancelled_orders=0
        )

        resp = client.post("/api/brokers/tiger/kill-switch")
        assert resp.status_code == 200
        assert resp.json()["cancelled_orders"] == 0

    def test_kill_switch_connection_error_503(self, client, mock_service) -> None:
        mock_service.get_adapter.return_value = MagicMock()
        mock_service.activate_kill_switch.side_effect = BrokerConnectionError(
            "offline"
        )

        resp = client.post("/api/brokers/tiger/kill-switch")
        assert resp.status_code == 503


# =========================================================================
# 8. Unknown broker => 404
# =========================================================================


class TestUnknownBroker:
    def test_unknown_broker_status_404(self, client, mock_service) -> None:
        mock_service.get_adapter.side_effect = KeyError("unknown")

        resp = client.get("/api/brokers/unknown/status")
        assert resp.status_code == 404
        assert "not registered" in resp.json()["detail"]

    def test_unknown_broker_orders_404(self, client, mock_service) -> None:
        mock_service.get_adapter.side_effect = KeyError("unknown")

        resp = client.get("/api/brokers/unknown/orders")
        assert resp.status_code == 404

    def test_unknown_broker_place_order_404(self, client, mock_service) -> None:
        mock_service.get_adapter.side_effect = KeyError("unknown")

        resp = client.post(
            "/api/brokers/unknown/orders",
            json={
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 1,
                "order_type": "MARKET",
            },
        )
        assert resp.status_code == 404

    def test_unknown_broker_cancel_404(self, client, mock_service) -> None:
        mock_service.get_adapter.side_effect = KeyError("unknown")

        resp = client.delete("/api/brokers/unknown/orders/123")
        assert resp.status_code == 404

    def test_unknown_broker_amend_404(self, client, mock_service) -> None:
        mock_service.get_adapter.side_effect = KeyError("unknown")

        resp = client.patch(
            "/api/brokers/unknown/orders/123",
            json={"quantity": 10},
        )
        assert resp.status_code == 404

    def test_unknown_broker_kill_switch_404(self, client, mock_service) -> None:
        mock_service.get_adapter.side_effect = KeyError("unknown")

        resp = client.post("/api/brokers/unknown/kill-switch")
        assert resp.status_code == 404
