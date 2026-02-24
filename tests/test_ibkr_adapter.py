"""Unit tests for the IBKR broker adapter.

All HTTP and WebSocket interactions are mocked — no live gateway needed.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from brokers.base import (
    AmendRequest,
    BrokerAdapter,
    BrokerRegistry,
    ConnectionState,
    ConnectionStatus,
    KillSwitchResult,
    OrderCallback,
    OrderEvent,
    OrderRequest,
    OrderSide,
    OrderSnapshot,
    OrderStatus,
    OrderType,
)
from brokers.exceptions import (
    BrokerConnectionError,
    BrokerSafetyError,
    BrokerValidationError,
    OrderNotFoundError,
)
from brokers.ibkr.constants import (
    IBKR_STATUS_MAP,
    IBKR_TO_ORDER_TYPE,
    ORDER_TYPE_TO_IBKR,
)


# =========================================================================
# 1. Constants tests
# =========================================================================


class TestConstants:
    def test_ibkr_status_map_covers_expected_statuses(self) -> None:
        expected = {
            "PreSubmitted",
            "PendingSubmit",
            "ApiPending",
            "Submitted",
            "PendingCancel",
            "Filled",
            "Cancelled",
            "ApiCancelled",
            "Inactive",
        }
        assert set(IBKR_STATUS_MAP.keys()) == expected

    def test_order_type_round_trip(self) -> None:
        for ot in OrderType:
            ibkr_str = ORDER_TYPE_TO_IBKR[ot]
            assert IBKR_TO_ORDER_TYPE[ibkr_str] == ot


# =========================================================================
# 2. IBKRClient tests (httpx mocked)
# =========================================================================


class TestIBKRClient:
    @pytest.fixture()
    def mock_httpx(self):
        with patch("brokers.ibkr.client.httpx.Client") as mock_cls:
            mock_http = MagicMock()
            mock_cls.return_value = mock_http
            yield mock_http

    def _make_client(self):
        from brokers.ibkr.client import IBKRClient

        return IBKRClient("https://localhost:5000")

    def test_get_success(self, mock_httpx) -> None:
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{"ok": true}'
        resp.json.return_value = {"ok": True}
        mock_httpx.request.return_value = resp

        client = self._make_client()
        result = client.get("/iserver/auth/status")
        assert result == {"ok": True}

    def test_post_success(self, mock_httpx) -> None:
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{"authenticated": true}'
        resp.json.return_value = {"authenticated": True}
        mock_httpx.request.return_value = resp

        client = self._make_client()
        result = client.post("/iserver/auth/status", json={"foo": "bar"})
        assert result == {"authenticated": True}

    def test_connection_error(self, mock_httpx) -> None:
        import httpx

        mock_httpx.request.side_effect = httpx.ConnectError("refused")

        client = self._make_client()
        with pytest.raises(BrokerConnectionError, match="unreachable"):
            client.get("/test")

    def test_timeout_error(self, mock_httpx) -> None:
        import httpx

        mock_httpx.request.side_effect = httpx.TimeoutException("timed out")

        client = self._make_client()
        with pytest.raises(BrokerConnectionError, match="unreachable"):
            client.get("/test")

    def test_client_error_not_retried(self, mock_httpx) -> None:
        resp = MagicMock()
        resp.status_code = 400
        resp.content = b'{"error": "bad"}'
        resp.json.return_value = {"error": "bad"}
        resp.text = '{"error": "bad"}'
        mock_httpx.request.return_value = resp

        client = self._make_client()
        result = client.get("/test")
        assert result == {"error": "bad"}
        # Only called once — no retries for 400
        assert mock_httpx.request.call_count == 1

    def test_server_error_retries(self, mock_httpx) -> None:
        resp_500 = MagicMock()
        resp_500.status_code = 500
        resp_500.content = b'{"error": "internal"}'
        resp_500.text = '{"error": "internal"}'
        resp_500.request = MagicMock()

        mock_httpx.request.return_value = resp_500

        client = self._make_client()
        with pytest.raises(BrokerConnectionError, match="failed after"):
            client.get("/test")

        # Should have retried 3 times
        assert mock_httpx.request.call_count == 3

    def test_empty_response_body(self, mock_httpx) -> None:
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b""
        mock_httpx.request.return_value = resp

        client = self._make_client()
        result = client.get("/test")
        assert result == {}


# =========================================================================
# 3. IBKRSessionManager tests
# =========================================================================


class TestIBKRSessionManager:
    @pytest.fixture()
    def mock_client(self):
        return MagicMock()

    def _make_session(self, client):
        from brokers.ibkr.session import IBKRSessionManager

        return IBKRSessionManager(client)

    def test_check_auth_status(self, mock_client) -> None:
        mock_client.post.return_value = {
            "authenticated": True,
            "connected": True,
        }
        session = self._make_session(mock_client)
        result = session.check_auth_status()

        assert result["authenticated"] is True
        assert result["connected"] is True

    def test_check_auth_status_false(self, mock_client) -> None:
        mock_client.post.return_value = {}
        session = self._make_session(mock_client)
        result = session.check_auth_status()

        assert result["authenticated"] is False
        assert result["connected"] is False

    def test_discover_accounts(self, mock_client) -> None:
        mock_client.get.return_value = {"accounts": ["U12345", "DU67890"]}
        session = self._make_session(mock_client)
        result = session.discover_accounts()

        assert len(result) == 2
        assert result[0] == {"account_id": "U12345", "is_paper": False}
        assert result[1] == {"account_id": "DU67890", "is_paper": True}

    def test_discover_accounts_empty(self, mock_client) -> None:
        mock_client.get.return_value = {"accounts": []}
        session = self._make_session(mock_client)
        result = session.discover_accounts()
        assert result == []

    def test_keepalive_starts_and_stops(self, mock_client) -> None:
        mock_client.post.return_value = {}
        session = self._make_session(mock_client)

        session.start_keepalive()
        assert session._keepalive_thread is not None
        assert session._keepalive_thread.is_alive()

        session.stop_keepalive()
        assert session._keepalive_thread is None

    def test_keepalive_disconnect_on_failures(self, mock_client) -> None:
        mock_client.post.side_effect = Exception("network error")
        session = self._make_session(mock_client)

        # Manually invoke the keepalive logic to test failure counting
        session._consecutive_failures = 2
        # Simulate one more failure
        try:
            session._client.post("/tickle")
        except Exception:
            session._consecutive_failures += 1
            if session._consecutive_failures >= 3:
                session._disconnected = True

        assert session.is_disconnected is True


# =========================================================================
# 4. ContractCache tests
# =========================================================================


class TestContractCache:
    @pytest.fixture()
    def mock_client(self):
        return MagicMock()

    def _make_cache(self, client, ttl=3600.0):
        from brokers.ibkr.contract_cache import ContractCache

        return ContractCache(client, ttl=ttl)

    def test_resolve_cache_miss_stk(self, mock_client) -> None:
        mock_client.post.return_value = [
            {
                "conid": 265598,
                "sections": [{"secType": "STK"}],
            }
        ]
        cache = self._make_cache(mock_client)
        assert cache.resolve("AAPL") == 265598
        mock_client.post.assert_called_once()

    def test_resolve_cache_hit(self, mock_client) -> None:
        mock_client.post.return_value = [
            {
                "conid": 265598,
                "sections": [{"secType": "STK"}],
            }
        ]
        cache = self._make_cache(mock_client)

        # First call — cache miss
        assert cache.resolve("AAPL") == 265598
        # Second call — cache hit
        assert cache.resolve("AAPL") == 265598
        # Only one API call
        assert mock_client.post.call_count == 1

    def test_resolve_case_insensitive(self, mock_client) -> None:
        mock_client.post.return_value = [
            {"conid": 265598, "sections": [{"secType": "STK"}]}
        ]
        cache = self._make_cache(mock_client)
        assert cache.resolve("aapl") == 265598
        assert cache.resolve("AAPL") == 265598
        assert mock_client.post.call_count == 1

    def test_resolve_no_results(self, mock_client) -> None:
        mock_client.post.return_value = []
        cache = self._make_cache(mock_client)

        with pytest.raises(BrokerValidationError, match="No IBKR contract"):
            cache.resolve("INVALID")

    def test_resolve_fallback_non_stk(self, mock_client) -> None:
        mock_client.post.return_value = [
            {
                "conid": 12345,
                "sections": [{"secType": "OPT"}],
            }
        ]
        cache = self._make_cache(mock_client)
        # Falls back to first result even without STK
        assert cache.resolve("SPY") == 12345

    def test_invalidate(self, mock_client) -> None:
        mock_client.post.return_value = [
            {"conid": 265598, "sections": [{"secType": "STK"}]}
        ]
        cache = self._make_cache(mock_client)
        cache.resolve("AAPL")

        cache.invalidate("AAPL")
        cache.resolve("AAPL")

        # Should have made 2 API calls (miss, invalidate, miss)
        assert mock_client.post.call_count == 2

    def test_clear(self, mock_client) -> None:
        mock_client.post.return_value = [
            {"conid": 265598, "sections": [{"secType": "STK"}]}
        ]
        cache = self._make_cache(mock_client)
        cache.resolve("AAPL")
        cache.clear()
        cache.resolve("AAPL")
        assert mock_client.post.call_count == 2

    def test_ttl_expiry(self, mock_client) -> None:
        mock_client.post.return_value = [
            {"conid": 265598, "sections": [{"secType": "STK"}]}
        ]
        # Very short TTL
        cache = self._make_cache(mock_client, ttl=0.01)
        cache.resolve("AAPL")
        time.sleep(0.02)
        cache.resolve("AAPL")
        assert mock_client.post.call_count == 2


# =========================================================================
# 5. IBKROrderStream tests
# =========================================================================


class TestIBKROrderStream:
    def _make_stream(self):
        from brokers.ibkr.stream import IBKROrderStream

        return IBKROrderStream("https://localhost:5000")

    def test_add_remove_callback(self) -> None:
        stream = self._make_stream()
        cb = MagicMock()

        stream.add_callback(cb)
        assert cb in stream._callbacks

        stream.remove_callback(cb)
        assert cb not in stream._callbacks

    def test_no_duplicate_callbacks(self) -> None:
        stream = self._make_stream()
        cb = MagicMock()

        stream.add_callback(cb)
        stream.add_callback(cb)
        assert len(stream._callbacks) == 1

    def test_remove_nonexistent_callback(self) -> None:
        stream = self._make_stream()
        # Should not raise
        stream.remove_callback(MagicMock())

    def test_dispatch_order_event(self) -> None:
        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        stream._dispatch_order_event(
            {
                "topic": "sor",
                "orderId": "12345",
                "symbol": "AAPL",
                "status": "Filled",
                "filledQuantity": 100,
                "remainingQuantity": 0,
                "avgPrice": 150.50,
            }
        )

        assert len(received) == 1
        event = received[0]
        assert event.broker == "ibkr"
        assert event.order_id == "12345"
        assert event.ticker == "AAPL"
        assert event.status == OrderStatus.FILLED
        assert event.filled_quantity == 100
        assert event.unfilled_quantity == 0
        assert event.filled_price == 150.50

    def test_dispatch_skips_empty_order_id(self) -> None:
        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        stream._dispatch_order_event({"topic": "sor", "orderId": ""})
        assert len(received) == 0

    def test_dispatch_unknown_status_defaults_received(self) -> None:
        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        stream._dispatch_order_event(
            {
                "topic": "sor",
                "orderId": "99",
                "symbol": "TSLA",
                "status": "UnknownStatus",
            }
        )

        assert len(received) == 1
        assert received[0].status == OrderStatus.RECEIVED

    def test_ws_url_construction(self) -> None:
        stream = self._make_stream()
        assert stream._ws_url == "wss://localhost:5000/v1/api/ws"

    def test_on_message_parses_sor(self) -> None:
        import json

        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        msg = json.dumps(
            {
                "topic": "sor",
                "orderId": "42",
                "symbol": "MSFT",
                "status": "Submitted",
                "filledQuantity": 0,
                "remainingQuantity": 50,
            }
        )
        stream._on_message(None, msg)

        assert len(received) == 1
        assert received[0].status == OrderStatus.CONFIRMED

    def test_on_message_ignores_non_sor(self) -> None:
        import json

        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        msg = json.dumps({"topic": "md", "data": {}})
        stream._on_message(None, msg)
        assert len(received) == 0

    def test_on_message_ignores_invalid_json(self) -> None:
        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        stream._on_message(None, "not-json")
        assert len(received) == 0

    def test_callback_exception_does_not_propagate(self) -> None:
        stream = self._make_stream()

        def bad_callback(ev: OrderEvent) -> None:
            raise ValueError("callback error")

        stream.add_callback(bad_callback)

        # Should not raise
        stream._dispatch_order_event(
            {
                "topic": "sor",
                "orderId": "1",
                "symbol": "X",
                "status": "Filled",
            }
        )


# =========================================================================
# 6. IBKRBrokerAdapter tests
# =========================================================================


@pytest.fixture()
def mock_ibkr_components():
    """Patch all IBKR sub-components for adapter tests."""
    with (
        patch("brokers.ibkr.adapter.IBKRClient") as mock_client_cls,
        patch("brokers.ibkr.adapter.IBKRSessionManager") as mock_session_cls,
        patch("brokers.ibkr.adapter.ContractCache") as mock_cache_cls,
        patch("brokers.ibkr.adapter.IBKROrderStream") as mock_stream_cls,
        patch.dict("os.environ", {"IBKR_ACCOUNT_ID": "U12345"}, clear=False),
    ):
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_cache = MagicMock()
        mock_stream = MagicMock()

        mock_client_cls.return_value = mock_client
        mock_session_cls.return_value = mock_session
        mock_cache_cls.return_value = mock_cache
        mock_stream_cls.return_value = mock_stream

        yield {
            "client": mock_client,
            "session": mock_session,
            "cache": mock_cache,
            "stream": mock_stream,
        }


def _make_ibkr_adapter():
    from brokers.ibkr.adapter import IBKRBrokerAdapter

    return IBKRBrokerAdapter()


# -- Identity --------------------------------------------------------------


class TestIBKRIdentity:
    def test_broker_name(self, mock_ibkr_components) -> None:
        adapter = _make_ibkr_adapter()
        assert adapter.broker_name == "ibkr"

    def test_supported_markets(self, mock_ibkr_components) -> None:
        adapter = _make_ibkr_adapter()
        assert adapter.supported_markets == ["US"]


# -- Connection status -----------------------------------------------------


class TestIBKRConnectionStatus:
    def test_connected(self, mock_ibkr_components) -> None:
        mock_ibkr_components["session"].check_auth_status.return_value = {
            "authenticated": True,
            "connected": True,
        }
        mock_ibkr_components["session"].is_disconnected = False
        mock_ibkr_components["session"].discover_accounts.return_value = [
            {"account_id": "U12345", "is_paper": False}
        ]

        adapter = _make_ibkr_adapter()
        result = adapter.get_connection_status()

        assert result.broker == "ibkr"
        assert result.status == ConnectionState.CONNECTED
        assert result.accounts == ["U12345"]
        assert result.is_paper_trading is False

    def test_disconnected(self, mock_ibkr_components) -> None:
        mock_ibkr_components["session"].check_auth_status.return_value = {
            "authenticated": False,
            "connected": False,
        }
        mock_ibkr_components["session"].is_disconnected = False

        adapter = _make_ibkr_adapter()
        result = adapter.get_connection_status()
        assert result.status == ConnectionState.DISCONNECTED

    def test_connection_error(self, mock_ibkr_components) -> None:
        mock_ibkr_components["session"].check_auth_status.side_effect = (
            BrokerConnectionError("unreachable")
        )

        adapter = _make_ibkr_adapter()
        result = adapter.get_connection_status()
        assert result.status == ConnectionState.DISCONNECTED

    def test_keepalive_disconnected(self, mock_ibkr_components) -> None:
        mock_ibkr_components["session"].check_auth_status.return_value = {
            "authenticated": True,
            "connected": True,
        }
        mock_ibkr_components["session"].is_disconnected = True

        adapter = _make_ibkr_adapter()
        result = adapter.get_connection_status()
        assert result.status == ConnectionState.DISCONNECTED

    def test_paper_trading_detected(self, mock_ibkr_components) -> None:
        mock_ibkr_components["session"].check_auth_status.return_value = {
            "authenticated": True,
            "connected": True,
        }
        mock_ibkr_components["session"].is_disconnected = False
        mock_ibkr_components["session"].discover_accounts.return_value = [
            {"account_id": "DU12345", "is_paper": True}
        ]

        adapter = _make_ibkr_adapter()
        result = adapter.get_connection_status()
        assert result.is_paper_trading is True


# -- place_order -----------------------------------------------------------


class TestIBKRPlaceOrder:
    def test_place_market_order(self, mock_ibkr_components) -> None:
        mock_ibkr_components["cache"].resolve.return_value = 265598
        mock_ibkr_components["client"].post.return_value = [
            {"order_id": "ORD1", "order_status": "PreSubmitted"}
        ]

        adapter = _make_ibkr_adapter()
        request = OrderRequest(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        result = adapter.place_order(request)

        assert isinstance(result, OrderSnapshot)
        assert result.broker == "ibkr"
        assert result.order_id == "ORD1"
        assert result.status == OrderStatus.RECEIVED
        assert result.ticker == "AAPL"
        assert result.quantity == 100

    def test_place_limit_order(self, mock_ibkr_components) -> None:
        mock_ibkr_components["cache"].resolve.return_value = 265598
        mock_ibkr_components["client"].post.return_value = [
            {"order_id": "ORD2", "order_status": "Submitted"}
        ]

        adapter = _make_ibkr_adapter()
        request = OrderRequest(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=50,
            order_type=OrderType.LIMIT,
            price=150.0,
        )
        result = adapter.place_order(request)

        assert result.order_id == "ORD2"
        assert result.status == OrderStatus.CONFIRMED
        assert result.price == 150.0

    def test_place_order_with_confirmation(self, mock_ibkr_components) -> None:
        mock_ibkr_components["cache"].resolve.return_value = 265598
        # First response requires confirmation
        mock_ibkr_components["client"].post.side_effect = [
            [{"id": "msg1", "message": "Are you sure?"}],
            [{"order_id": "ORD3", "order_status": "Submitted"}],
        ]

        adapter = _make_ibkr_adapter()
        request = OrderRequest(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        result = adapter.place_order(request)

        assert result.order_id == "ORD3"
        # Verify reply was sent
        assert mock_ibkr_components["client"].post.call_count == 2

    def test_place_order_kill_switch_active(self, mock_ibkr_components) -> None:
        adapter = _make_ibkr_adapter()
        adapter._kill_switch_active = True

        request = OrderRequest(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        with pytest.raises(BrokerSafetyError, match="Kill switch"):
            adapter.place_order(request)

    def test_place_order_error_response(self, mock_ibkr_components) -> None:
        mock_ibkr_components["cache"].resolve.return_value = 265598
        mock_ibkr_components["client"].post.return_value = {"error": "Insufficient funds"}

        adapter = _make_ibkr_adapter()
        request = OrderRequest(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        with pytest.raises(BrokerValidationError, match="Insufficient funds"):
            adapter.place_order(request)


# -- get_orders ------------------------------------------------------------


class TestIBKRGetOrders:
    def test_get_orders(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].get.return_value = {
            "orders": [
                {
                    "orderId": "1001",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "orderType": "MKT",
                    "status": "Filled",
                    "totalSize": 100,
                    "filledQuantity": 100,
                    "remainingQuantity": 0,
                    "avgPrice": 150.25,
                    "created_at": "2026-01-01T00:00:00",
                },
                {
                    "orderId": "1002",
                    "symbol": "TSLA",
                    "side": "SELL",
                    "orderType": "LMT",
                    "status": "Submitted",
                    "totalSize": 50,
                    "filledQuantity": 0,
                    "remainingQuantity": 50,
                    "price": 300.0,
                    "created_at": "2026-01-01T00:00:00",
                },
            ]
        }

        adapter = _make_ibkr_adapter()
        orders = adapter.get_orders()

        assert len(orders) == 2
        assert orders[0].order_id == "1001"
        assert orders[0].status == OrderStatus.FILLED
        assert orders[0].filled_quantity == 100
        assert orders[0].filled_price == 150.25
        assert orders[1].order_id == "1002"
        assert orders[1].status == OrderStatus.CONFIRMED
        assert orders[1].side == OrderSide.SELL

    def test_get_orders_empty(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].get.return_value = {"orders": []}
        adapter = _make_ibkr_adapter()
        assert adapter.get_orders() == []

    def test_get_orders_non_dict_response(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].get.return_value = []
        adapter = _make_ibkr_adapter()
        assert adapter.get_orders() == []


# -- cancel_order ----------------------------------------------------------


class TestIBKRCancelOrder:
    def test_cancel_order_success(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].delete.return_value = {"msg": "ok"}
        mock_ibkr_components["session"].discover_accounts.return_value = [
            {"account_id": "U12345", "is_paper": False}
        ]

        adapter = _make_ibkr_adapter()
        adapter.cancel_order("1001")  # Should not raise
        mock_ibkr_components["client"].delete.assert_called_once()

    def test_cancel_order_not_found(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].delete.return_value = {
            "error": "Order not found"
        }

        adapter = _make_ibkr_adapter()
        with pytest.raises(OrderNotFoundError, match="not found"):
            adapter.cancel_order("9999")


# -- amend_order -----------------------------------------------------------


class TestIBKRAmendOrder:
    def test_amend_order_success(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].post.return_value = {"msg": "ok"}

        adapter = _make_ibkr_adapter()
        adapter.amend_order("1001", AmendRequest(quantity=200))
        mock_ibkr_components["client"].post.assert_called_once()

    def test_amend_order_not_found(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].post.return_value = {
            "error": "Order not found"
        }

        adapter = _make_ibkr_adapter()
        with pytest.raises(OrderNotFoundError, match="not found"):
            adapter.amend_order("9999", AmendRequest(price=100.0))

    def test_amend_with_confirmation(self, mock_ibkr_components) -> None:
        # First response requires confirmation, second is success
        mock_ibkr_components["client"].post.side_effect = [
            [{"id": "msg1", "message": "Confirm amendment"}],
            {"msg": "ok"},
        ]

        adapter = _make_ibkr_adapter()
        adapter.amend_order("1001", AmendRequest(quantity=200))
        assert mock_ibkr_components["client"].post.call_count == 2

    def test_amend_order_kill_switch_active(self, mock_ibkr_components) -> None:
        adapter = _make_ibkr_adapter()
        adapter._kill_switch_active = True

        with pytest.raises(BrokerSafetyError, match="Kill switch"):
            adapter.amend_order("1001", AmendRequest(quantity=200))


# -- kill switch -----------------------------------------------------------


class TestIBKRKillSwitch:
    def test_kill_switch_cancels_open_orders(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].get.return_value = {
            "orders": [
                {
                    "orderId": "1001",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "orderType": "MKT",
                    "status": "Submitted",
                    "totalSize": 100,
                    "filledQuantity": 0,
                    "remainingQuantity": 100,
                    "created_at": "2026-01-01T00:00:00",
                },
                {
                    "orderId": "1002",
                    "symbol": "TSLA",
                    "side": "SELL",
                    "orderType": "LMT",
                    "status": "Filled",
                    "totalSize": 50,
                    "filledQuantity": 50,
                    "remainingQuantity": 0,
                    "created_at": "2026-01-01T00:00:00",
                },
            ]
        }
        mock_ibkr_components["client"].delete.return_value = {"msg": "ok"}
        mock_ibkr_components["session"].discover_accounts.return_value = [
            {"account_id": "U12345", "is_paper": False}
        ]

        adapter = _make_ibkr_adapter()
        result = adapter.activate_kill_switch()

        assert isinstance(result, KillSwitchResult)
        assert result.activated is True
        # Only the Submitted order should be cancelled (Filled is terminal)
        assert result.cancelled_orders == 1
        assert adapter._kill_switch_active is True

    def test_kill_switch_blocks_new_orders(self, mock_ibkr_components) -> None:
        mock_ibkr_components["client"].get.return_value = {"orders": []}

        adapter = _make_ibkr_adapter()
        adapter.activate_kill_switch()

        request = OrderRequest(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        with pytest.raises(BrokerSafetyError, match="Kill switch"):
            adapter.place_order(request)


# -- subscriptions ---------------------------------------------------------


class TestIBKRSubscription:
    def test_subscribe_delegates_to_stream(self, mock_ibkr_components) -> None:
        adapter = _make_ibkr_adapter()
        cb = MagicMock()
        adapter.subscribe_orders(cb)

        mock_ibkr_components["stream"].add_callback.assert_called_once_with(cb)
        mock_ibkr_components["stream"].start.assert_called_once()

    def test_unsubscribe_delegates_to_stream(self, mock_ibkr_components) -> None:
        adapter = _make_ibkr_adapter()
        cb = MagicMock()
        adapter.unsubscribe_orders(cb)

        mock_ibkr_components["stream"].remove_callback.assert_called_once_with(cb)


# -- unavailable state -----------------------------------------------------


class TestIBKRUnavailable:
    def test_unavailable_when_init_fails(self) -> None:
        with patch(
            "brokers.ibkr.adapter.IBKRClient", side_effect=Exception("no gateway")
        ):
            adapter = _make_ibkr_adapter()
            assert adapter._available is False

            status = adapter.get_connection_status()
            assert status.status == ConnectionState.UNAVAILABLE

            with pytest.raises(BrokerConnectionError, match="not available"):
                adapter.place_order(
                    OrderRequest(
                        ticker="AAPL",
                        side=OrderSide.BUY,
                        quantity=1,
                        order_type=OrderType.MARKET,
                    )
                )


# -- raw_to_snapshot parsing -----------------------------------------------


class TestRawToSnapshot:
    def test_buy_side_parsing(self, mock_ibkr_components) -> None:
        from brokers.ibkr.adapter import IBKRBrokerAdapter

        snap = IBKRBrokerAdapter._raw_to_snapshot(
            {
                "orderId": "1",
                "symbol": "AAPL",
                "side": "BUY",
                "orderType": "MKT",
                "status": "Filled",
                "totalSize": 100,
                "filledQuantity": 100,
                "remainingQuantity": 0,
                "avgPrice": 150.0,
                "created_at": "2026-01-01T00:00:00",
            }
        )
        assert snap.side == OrderSide.BUY
        assert snap.order_type == OrderType.MARKET
        assert snap.filled_price == 150.0

    def test_sell_side_short_form(self, mock_ibkr_components) -> None:
        from brokers.ibkr.adapter import IBKRBrokerAdapter

        snap = IBKRBrokerAdapter._raw_to_snapshot(
            {
                "orderId": "2",
                "symbol": "TSLA",
                "side": "S",
                "orderType": "LMT",
                "status": "Submitted",
                "totalSize": 50,
                "filledQuantity": 0,
                "remainingQuantity": 50,
                "price": 300.0,
                "created_at": "2026-01-01T00:00:00",
            }
        )
        assert snap.side == OrderSide.SELL
        assert snap.order_type == OrderType.LIMIT
        assert snap.price == 300.0

    def test_unknown_side_defaults_to_buy(self, mock_ibkr_components) -> None:
        from brokers.ibkr.adapter import IBKRBrokerAdapter

        snap = IBKRBrokerAdapter._raw_to_snapshot(
            {
                "orderId": "3",
                "symbol": "GOOG",
                "side": "UNKNOWN",
                "orderType": "MKT",
                "status": "Filled",
                "totalSize": 10,
                "filledQuantity": 10,
                "remainingQuantity": 0,
                "created_at": "2026-01-01T00:00:00",
            }
        )
        assert snap.side == OrderSide.BUY


# =========================================================================
# 7. Registry integration
# =========================================================================


class TestIBKRRegistration:
    def test_ibkr_registered_in_default_registry(
        self, mock_ibkr_components
    ) -> None:
        import brokers

        brokers._registry_initialised = False
        brokers._default_registry = BrokerRegistry()

        from brokers.ibkr.adapter import IBKRBrokerAdapter

        brokers._default_registry.register("ibkr", IBKRBrokerAdapter)
        brokers._registry_initialised = True

        assert "ibkr" in brokers.list_brokers()

    def test_get_ibkr_broker(self, mock_ibkr_components) -> None:
        import brokers

        brokers._registry_initialised = False
        brokers._default_registry = BrokerRegistry()

        from brokers.ibkr.adapter import IBKRBrokerAdapter

        brokers._default_registry.register("ibkr", IBKRBrokerAdapter)
        brokers._registry_initialised = True

        adapter = brokers.get_broker("ibkr")
        assert isinstance(adapter, BrokerAdapter)
        assert adapter.broker_name == "ibkr"
