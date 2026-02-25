"""Unit tests for the Tiger Brokers adapter.

All SDK interactions are mocked — no live Tiger connection needed.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from brokers.base import (
    AmendRequest,
    BrokerAdapter,
    BrokerRegistry,
    ConnectionState,
    KillSwitchResult,
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
from brokers.tiger.constants import (
    ORDER_TYPE_TO_TIGER,
    SUPPORTED_MARKETS,
    TIGER_STATUS_MAP,
    TIGER_TO_ORDER_TYPE,
)


# =========================================================================
# 1. Constants tests
# =========================================================================


class TestConstants:
    def test_tiger_status_map_covers_expected_statuses(self) -> None:
        expected_canonical = {
            OrderStatus.RECEIVED,
            OrderStatus.CONFIRMED,
            OrderStatus.PARTIAL,
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
        }
        assert expected_canonical == set(TIGER_STATUS_MAP.values())

    def test_order_type_round_trip(self) -> None:
        for ot in OrderType:
            tiger_str = ORDER_TYPE_TO_TIGER[ot]
            assert TIGER_TO_ORDER_TYPE[tiger_str] == ot

    def test_supported_markets(self) -> None:
        assert SUPPORTED_MARKETS == ["US", "HK", "SG"]

    def test_all_tiger_statuses_mapped(self) -> None:
        expected_keys = {
            "Initial", "NEW",
            "PendingNew", "PENDING_NEW",
            "Held", "HELD",
            "Submitted", "SUBMITTED",
            "PendingCancel", "PENDING_CANCEL",
            "PartiallyFilled", "PARTIALLY_FILLED",
            "Filled", "FILLED",
            "Cancelled", "CANCELLED",
            "Rejected", "REJECTED",
            "Expired", "EXPIRED",
        }
        assert set(TIGER_STATUS_MAP.keys()) == expected_keys

    def test_submitted_maps_to_confirmed(self) -> None:
        assert TIGER_STATUS_MAP["Submitted"] == OrderStatus.CONFIRMED
        assert TIGER_STATUS_MAP["SUBMITTED"] == OrderStatus.CONFIRMED


# =========================================================================
# 2. TigerSession tests
# =========================================================================


class TestTigerSession:
    @pytest.fixture()
    def mock_tiger_sdk(self, monkeypatch):
        """Mock all tigeropen SDK modules."""
        # Create mock modules
        mock_config_cls = MagicMock()
        mock_config_instance = MagicMock()
        mock_config_cls.return_value = mock_config_instance

        mock_trade_client_cls = MagicMock()
        mock_trade_client = MagicMock()
        mock_trade_client_cls.return_value = mock_trade_client

        mock_language = MagicMock()
        mock_language.en_US = "en_US"

        # Patch modules into sys.modules
        tigeropen = types.ModuleType("tigeropen")
        tigeropen_common = types.ModuleType("tigeropen.common")
        tigeropen_common_consts = types.ModuleType("tigeropen.common.consts")
        tigeropen_common_consts.Language = mock_language
        tigeropen_config = types.ModuleType("tigeropen.tiger_open_config")
        tigeropen_config.TigerOpenClientConfig = mock_config_cls
        tigeropen_trade = types.ModuleType("tigeropen.trade")
        tigeropen_trade_client = types.ModuleType("tigeropen.trade.trade_client")
        tigeropen_trade_client.TradeClient = mock_trade_client_cls

        modules = {
            "tigeropen": tigeropen,
            "tigeropen.common": tigeropen_common,
            "tigeropen.common.consts": tigeropen_common_consts,
            "tigeropen.tiger_open_config": tigeropen_config,
            "tigeropen.trade": tigeropen_trade,
            "tigeropen.trade.trade_client": tigeropen_trade_client,
        }
        for name, mod in modules.items():
            monkeypatch.setitem(sys.modules, name, mod)

        return {
            "config_cls": mock_config_cls,
            "config": mock_config_instance,
            "trade_client_cls": mock_trade_client_cls,
            "trade_client": mock_trade_client,
        }

    def test_missing_tiger_id(self, mock_tiger_sdk, monkeypatch, tmp_path) -> None:
        key_file = tmp_path / "key.pem"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
        monkeypatch.delenv("TIGER_ID", raising=False)
        monkeypatch.setenv("TIGER_PRIVATE_KEY", str(key_file))
        monkeypatch.setenv("TIGER_ACCOUNT", "12345")

        # Force reimport
        import importlib
        import brokers.tiger.session as sess_mod
        importlib.reload(sess_mod)

        with pytest.raises(BrokerConnectionError, match="TIGER_ID"):
            sess_mod.TigerSession()

    def test_missing_private_key(self, mock_tiger_sdk, monkeypatch) -> None:
        monkeypatch.setenv("TIGER_ID", "test_id")
        monkeypatch.delenv("TIGER_PRIVATE_KEY", raising=False)
        monkeypatch.setenv("TIGER_ACCOUNT", "12345")

        import importlib
        import brokers.tiger.session as sess_mod
        importlib.reload(sess_mod)

        with pytest.raises(BrokerConnectionError, match="TIGER_PRIVATE_KEY"):
            sess_mod.TigerSession()

    def test_missing_account(self, mock_tiger_sdk, monkeypatch, tmp_path) -> None:
        key_file = tmp_path / "key.pem"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
        monkeypatch.setenv("TIGER_ID", "test_id")
        monkeypatch.setenv("TIGER_PRIVATE_KEY", str(key_file))
        monkeypatch.delenv("TIGER_ACCOUNT", raising=False)

        import importlib
        import brokers.tiger.session as sess_mod
        importlib.reload(sess_mod)

        with pytest.raises(BrokerConnectionError, match="TIGER_ACCOUNT"):
            sess_mod.TigerSession()

    def test_successful_init(self, mock_tiger_sdk, monkeypatch, tmp_path) -> None:
        key_file = tmp_path / "key.pem"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
        monkeypatch.setenv("TIGER_ID", "test_id")
        monkeypatch.setenv("TIGER_PRIVATE_KEY", str(key_file))
        monkeypatch.setenv("TIGER_ACCOUNT", "12345")

        import importlib
        import brokers.tiger.session as sess_mod
        importlib.reload(sess_mod)

        session = sess_mod.TigerSession()
        assert session.client is not None
        assert session.config is not None

    def test_check_connection_success(self, mock_tiger_sdk, monkeypatch, tmp_path) -> None:
        key_file = tmp_path / "key.pem"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
        monkeypatch.setenv("TIGER_ID", "test_id")
        monkeypatch.setenv("TIGER_PRIVATE_KEY", str(key_file))
        monkeypatch.setenv("TIGER_ACCOUNT", "12345")

        mock_tiger_sdk["trade_client"].get_managed_accounts.return_value = ["12345"]

        import importlib
        import brokers.tiger.session as sess_mod
        importlib.reload(sess_mod)

        session = sess_mod.TigerSession()
        assert session.check_connection() is True

    def test_check_connection_failure(self, mock_tiger_sdk, monkeypatch, tmp_path) -> None:
        key_file = tmp_path / "key.pem"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
        monkeypatch.setenv("TIGER_ID", "test_id")
        monkeypatch.setenv("TIGER_PRIVATE_KEY", str(key_file))
        monkeypatch.setenv("TIGER_ACCOUNT", "12345")

        mock_tiger_sdk["trade_client"].get_managed_accounts.side_effect = Exception("timeout")

        import importlib
        import brokers.tiger.session as sess_mod
        importlib.reload(sess_mod)

        session = sess_mod.TigerSession()
        with pytest.raises(BrokerConnectionError, match="connection check failed"):
            session.check_connection()

    def test_get_accounts(self, mock_tiger_sdk, monkeypatch, tmp_path) -> None:
        key_file = tmp_path / "key.pem"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
        monkeypatch.setenv("TIGER_ID", "test_id")
        monkeypatch.setenv("TIGER_PRIVATE_KEY", str(key_file))
        monkeypatch.setenv("TIGER_ACCOUNT", "12345")

        mock_tiger_sdk["trade_client"].get_managed_accounts.return_value = [
            "12345",
            "12345678901234567",  # 17-digit = paper
        ]

        import importlib
        import brokers.tiger.session as sess_mod
        importlib.reload(sess_mod)

        session = sess_mod.TigerSession()
        accounts = session.get_accounts()

        assert len(accounts) == 2
        assert accounts[0] == {"account_id": "12345", "is_paper": False}
        assert accounts[1] == {"account_id": "12345678901234567", "is_paper": True}


# =========================================================================
# 3. TigerOrderStream tests
# =========================================================================


class TestTigerOrderStream:
    def _make_stream(self):
        from brokers.tiger.stream import TigerOrderStream

        config = MagicMock()
        return TigerOrderStream(config, "12345")

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
        stream.remove_callback(MagicMock())  # Should not raise

    def test_on_order_changed_dispatches_event(self) -> None:
        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        frame = MagicMock()
        frame.id = 12345
        frame.symbol = "AAPL"
        frame.status = "Filled"
        frame.filled = 100
        frame.quantity = 100
        frame.avg_fill_price = 150.50

        stream._on_order_changed(frame)

        assert len(received) == 1
        event = received[0]
        assert event.broker == "tiger"
        assert event.order_id == "12345"
        assert event.ticker == "AAPL"
        assert event.status == OrderStatus.FILLED
        assert event.filled_quantity == 100
        assert event.unfilled_quantity == 0
        assert event.filled_price == 150.50

    def test_on_order_changed_skips_empty_id(self) -> None:
        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        frame = MagicMock()
        frame.id = ""
        stream._on_order_changed(frame)

        assert len(received) == 0

    def test_on_order_changed_unknown_status_defaults_received(self) -> None:
        stream = self._make_stream()
        received: list[OrderEvent] = []
        stream.add_callback(lambda ev: received.append(ev))

        frame = MagicMock()
        frame.id = 99
        frame.symbol = "TSLA"
        frame.status = "UnknownStatus"
        frame.filled = 0
        frame.quantity = 50
        frame.avg_fill_price = None

        stream._on_order_changed(frame)

        assert len(received) == 1
        assert received[0].status == OrderStatus.RECEIVED

    def test_callback_exception_does_not_propagate(self) -> None:
        stream = self._make_stream()

        def bad_callback(ev: OrderEvent) -> None:
            raise ValueError("callback error")

        stream.add_callback(bad_callback)

        frame = MagicMock()
        frame.id = 1
        frame.symbol = "X"
        frame.status = "Filled"
        frame.filled = 10
        frame.quantity = 10
        frame.avg_fill_price = 100.0

        # Should not raise
        stream._on_order_changed(frame)

    def test_stop_when_not_started(self) -> None:
        stream = self._make_stream()
        stream.stop()  # Should not raise


# =========================================================================
# 4. TigerBrokerAdapter tests
# =========================================================================


@pytest.fixture()
def mock_tiger_components(monkeypatch):
    """Patch all Tiger sub-components for adapter tests."""
    mock_session = MagicMock()
    mock_stream = MagicMock()

    monkeypatch.setenv("TIGER_ID", "test_id")
    monkeypatch.setenv("TIGER_PRIVATE_KEY", "/tmp/fake_key.pem")
    monkeypatch.setenv("TIGER_ACCOUNT", "12345")

    with (
        patch("brokers.tiger.adapter.TigerSession") as mock_session_cls,
        patch("brokers.tiger.adapter.TigerOrderStream") as mock_stream_cls,
    ):
        mock_session_cls.return_value = mock_session
        mock_stream_cls.return_value = mock_stream
        mock_session.config = MagicMock()

        yield {
            "session": mock_session,
            "stream": mock_stream,
        }


def _make_tiger_adapter():
    from brokers.tiger.adapter import TigerBrokerAdapter

    return TigerBrokerAdapter()


# -- Identity --------------------------------------------------------------


class TestTigerIdentity:
    def test_broker_name(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        assert adapter.broker_name == "tiger"

    def test_supported_markets(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        assert adapter.supported_markets == ["US", "HK", "SG"]


# -- Connection status -----------------------------------------------------


class TestTigerConnectionStatus:
    def test_connected(self, mock_tiger_components) -> None:
        mock_tiger_components["session"].check_connection.return_value = True
        mock_tiger_components["session"].get_accounts.return_value = [
            {"account_id": "12345", "is_paper": False}
        ]

        adapter = _make_tiger_adapter()
        result = adapter.get_connection_status()

        assert result.broker == "tiger"
        assert result.status == ConnectionState.CONNECTED
        assert result.accounts == ["12345"]
        assert result.is_paper_trading is False

    def test_disconnected(self, mock_tiger_components) -> None:
        mock_tiger_components["session"].check_connection.side_effect = (
            BrokerConnectionError("timeout")
        )

        adapter = _make_tiger_adapter()
        result = adapter.get_connection_status()
        assert result.status == ConnectionState.DISCONNECTED

    def test_unavailable_when_init_fails(self) -> None:
        with patch(
            "brokers.tiger.adapter.TigerSession",
            side_effect=Exception("no SDK"),
        ):
            adapter = _make_tiger_adapter()
            assert adapter._available is False

            status = adapter.get_connection_status()
            assert status.status == ConnectionState.UNAVAILABLE

    def test_paper_trading_detected(self, mock_tiger_components) -> None:
        mock_tiger_components["session"].check_connection.return_value = True
        mock_tiger_components["session"].get_accounts.return_value = [
            {"account_id": "12345678901234567", "is_paper": True}
        ]

        adapter = _make_tiger_adapter()
        result = adapter.get_connection_status()
        assert result.is_paper_trading is True


# -- place_order -----------------------------------------------------------


class TestTigerPlaceOrder:
    def test_place_market_order(self, mock_tiger_components) -> None:
        mock_order = MagicMock()
        mock_order.id = 1001

        with (
            patch("brokers.tiger.adapter._SDK_UTILS_AVAILABLE", True),
            patch(
                "brokers.tiger.adapter.stock_contract", return_value=MagicMock()
            ),
            patch(
                "brokers.tiger.adapter.market_order", return_value=mock_order
            ),
        ):
            adapter = _make_tiger_adapter()
            request = OrderRequest(
                ticker="AAPL",
                side=OrderSide.BUY,
                quantity=100,
                order_type=OrderType.MARKET,
            )
            result = adapter.place_order(request)

            assert isinstance(result, OrderSnapshot)
            assert result.broker == "tiger"
            assert result.order_id == "1001"
            assert result.status == OrderStatus.RECEIVED
            assert result.ticker == "AAPL"
            assert result.quantity == 100

    def test_place_limit_order(self, mock_tiger_components) -> None:
        mock_order = MagicMock()
        mock_order.id = 1002

        with (
            patch("brokers.tiger.adapter._SDK_UTILS_AVAILABLE", True),
            patch(
                "brokers.tiger.adapter.stock_contract", return_value=MagicMock()
            ),
            patch(
                "brokers.tiger.adapter.limit_order", return_value=mock_order
            ),
        ):
            adapter = _make_tiger_adapter()
            request = OrderRequest(
                ticker="AAPL",
                side=OrderSide.SELL,
                quantity=50,
                order_type=OrderType.LIMIT,
                price=150.0,
            )
            result = adapter.place_order(request)

            assert result.order_id == "1002"
            assert result.price == 150.0
            assert result.side == OrderSide.SELL

    def test_place_order_kill_switch_active(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        adapter._kill_switch_active = True

        request = OrderRequest(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        with pytest.raises(BrokerSafetyError, match="Kill switch"):
            adapter.place_order(request)

    def test_place_order_failure(self, mock_tiger_components) -> None:
        mock_order = MagicMock()
        mock_order.id = None

        mock_tiger_components["session"].client.place_order.side_effect = Exception(
            "Insufficient funds"
        )

        with (
            patch("brokers.tiger.adapter._SDK_UTILS_AVAILABLE", True),
            patch(
                "brokers.tiger.adapter.stock_contract", return_value=MagicMock()
            ),
            patch(
                "brokers.tiger.adapter.market_order", return_value=mock_order
            ),
        ):
            adapter = _make_tiger_adapter()
            request = OrderRequest(
                ticker="AAPL",
                side=OrderSide.BUY,
                quantity=100,
                order_type=OrderType.MARKET,
            )
            with pytest.raises(BrokerValidationError, match="Insufficient funds"):
                adapter.place_order(request)


# -- get_orders ------------------------------------------------------------


class TestTigerGetOrders:
    def test_get_orders(self, mock_tiger_components) -> None:
        order1 = MagicMock()
        order1.id = 1001
        order1.contract = MagicMock()
        order1.contract.symbol = "AAPL"
        order1.action = "BUY"
        order1.quantity = 100
        order1.filled = 100
        order1.remaining = 0
        order1.order_type = "MKT"
        order1.limit_price = None
        order1.avg_fill_price = 150.25
        order1.status = "Filled"

        order2 = MagicMock()
        order2.id = 1002
        order2.contract = MagicMock()
        order2.contract.symbol = "TSLA"
        order2.action = "SELL"
        order2.quantity = 50
        order2.filled = 0
        order2.remaining = 50
        order2.order_type = "LMT"
        order2.limit_price = 300.0
        order2.avg_fill_price = None
        order2.status = "Held"

        mock_tiger_components["session"].client.get_orders.return_value = [order1, order2]

        adapter = _make_tiger_adapter()
        orders = adapter.get_orders()

        assert len(orders) == 2
        assert orders[0].order_id == "1001"
        assert orders[0].status == OrderStatus.FILLED
        assert orders[0].filled_quantity == 100
        assert orders[0].filled_price == 150.25
        assert orders[1].order_id == "1002"
        assert orders[1].status == OrderStatus.CONFIRMED
        assert orders[1].side == OrderSide.SELL

    def test_get_orders_empty(self, mock_tiger_components) -> None:
        mock_tiger_components["session"].client.get_orders.return_value = []
        adapter = _make_tiger_adapter()
        assert adapter.get_orders() == []

    def test_get_orders_none(self, mock_tiger_components) -> None:
        mock_tiger_components["session"].client.get_orders.return_value = None
        adapter = _make_tiger_adapter()
        assert adapter.get_orders() == []


# -- cancel_order ----------------------------------------------------------


class TestTigerCancelOrder:
    def test_cancel_order_success(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        adapter.cancel_order("1001")  # Should not raise
        mock_tiger_components["session"].client.cancel_order.assert_called_once_with(
            id=1001
        )

    def test_cancel_order_not_found(self, mock_tiger_components) -> None:
        mock_tiger_components["session"].client.cancel_order.side_effect = Exception(
            "Order not found"
        )

        adapter = _make_tiger_adapter()
        with pytest.raises(OrderNotFoundError, match="not found"):
            adapter.cancel_order("9999")

    def test_cancel_order_invalid_id(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        with pytest.raises(OrderNotFoundError, match="Invalid order ID"):
            adapter.cancel_order("not-a-number")


# -- amend_order -----------------------------------------------------------


class TestTigerAmendOrder:
    def test_amend_order_quantity(self, mock_tiger_components) -> None:
        with (
            patch("brokers.tiger.adapter._SDK_UTILS_AVAILABLE", True),
            patch("brokers.tiger.adapter.Order") as mock_order_cls,
        ):
            mock_order = MagicMock()
            mock_order_cls.return_value = mock_order

            adapter = _make_tiger_adapter()
            adapter.amend_order("1001", AmendRequest(quantity=200))

            assert mock_order.id == 1001
            assert mock_order.quantity == 200
            mock_tiger_components["session"].client.modify_order.assert_called_once_with(
                mock_order
            )

    def test_amend_order_price(self, mock_tiger_components) -> None:
        with (
            patch("brokers.tiger.adapter._SDK_UTILS_AVAILABLE", True),
            patch("brokers.tiger.adapter.Order") as mock_order_cls,
        ):
            mock_order = MagicMock()
            mock_order_cls.return_value = mock_order

            adapter = _make_tiger_adapter()
            adapter.amend_order("1001", AmendRequest(price=155.0))

            assert mock_order.limit_price == 155.0

    def test_amend_order_kill_switch_active(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        adapter._kill_switch_active = True

        with pytest.raises(BrokerSafetyError, match="Kill switch"):
            adapter.amend_order("1001", AmendRequest(quantity=200))

    def test_amend_order_invalid_id(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        with pytest.raises(OrderNotFoundError, match="Invalid order ID"):
            adapter.amend_order("invalid", AmendRequest(quantity=200))


# -- kill switch -----------------------------------------------------------


class TestTigerKillSwitch:
    def test_kill_switch_cancels_open_orders(self, mock_tiger_components) -> None:
        order_open = MagicMock()
        order_open.id = 1001
        order_open.contract = MagicMock()
        order_open.contract.symbol = "AAPL"
        order_open.action = "BUY"
        order_open.quantity = 100
        order_open.filled = 0
        order_open.remaining = 100
        order_open.order_type = "MKT"
        order_open.limit_price = None
        order_open.avg_fill_price = None
        order_open.status = "Held"  # CONFIRMED -> should be cancelled

        order_filled = MagicMock()
        order_filled.id = 1002
        order_filled.contract = MagicMock()
        order_filled.contract.symbol = "TSLA"
        order_filled.action = "SELL"
        order_filled.quantity = 50
        order_filled.filled = 50
        order_filled.remaining = 0
        order_filled.order_type = "LMT"
        order_filled.limit_price = 300.0
        order_filled.avg_fill_price = 300.0
        order_filled.status = "Filled"  # terminal -> should NOT be cancelled

        mock_tiger_components["session"].client.get_orders.return_value = [
            order_open, order_filled
        ]

        adapter = _make_tiger_adapter()
        result = adapter.activate_kill_switch()

        assert isinstance(result, KillSwitchResult)
        assert result.activated is True
        assert result.cancelled_orders == 1
        assert adapter._kill_switch_active is True

    def test_kill_switch_cancels_partial_orders(self, mock_tiger_components) -> None:
        order_partial = MagicMock()
        order_partial.id = 1003
        order_partial.contract = MagicMock()
        order_partial.contract.symbol = "GOOG"
        order_partial.action = "BUY"
        order_partial.quantity = 100
        order_partial.filled = 30
        order_partial.remaining = 70
        order_partial.order_type = "LMT"
        order_partial.limit_price = 180.0
        order_partial.avg_fill_price = 179.5
        order_partial.status = "PartiallyFilled"  # PARTIAL -> should be cancelled

        mock_tiger_components["session"].client.get_orders.return_value = [order_partial]

        adapter = _make_tiger_adapter()
        result = adapter.activate_kill_switch()

        assert result.cancelled_orders == 1

    def test_kill_switch_blocks_new_orders(self, mock_tiger_components) -> None:
        mock_tiger_components["session"].client.get_orders.return_value = []

        adapter = _make_tiger_adapter()
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


class TestTigerSubscription:
    def test_subscribe_delegates_to_stream(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        cb = MagicMock()
        adapter.subscribe_orders(cb)

        mock_tiger_components["stream"].add_callback.assert_called_once_with(cb)
        mock_tiger_components["stream"].start.assert_called_once()

    def test_unsubscribe_delegates_to_stream(self, mock_tiger_components) -> None:
        adapter = _make_tiger_adapter()
        cb = MagicMock()
        adapter.unsubscribe_orders(cb)

        mock_tiger_components["stream"].remove_callback.assert_called_once_with(cb)


# -- unavailable state -----------------------------------------------------


class TestTigerUnavailable:
    def test_unavailable_when_init_fails(self) -> None:
        with patch(
            "brokers.tiger.adapter.TigerSession", side_effect=Exception("no SDK")
        ):
            adapter = _make_tiger_adapter()
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

    def test_unavailable_get_orders(self) -> None:
        with patch(
            "brokers.tiger.adapter.TigerSession", side_effect=Exception("no SDK")
        ):
            adapter = _make_tiger_adapter()
            with pytest.raises(BrokerConnectionError, match="not available"):
                adapter.get_orders()

    def test_unavailable_cancel_order(self) -> None:
        with patch(
            "brokers.tiger.adapter.TigerSession", side_effect=Exception("no SDK")
        ):
            adapter = _make_tiger_adapter()
            with pytest.raises(BrokerConnectionError, match="not available"):
                adapter.cancel_order("1001")


# =========================================================================
# 5. Registry integration
# =========================================================================


class TestTigerRegistration:
    def test_tiger_registered_in_default_registry(
        self, mock_tiger_components
    ) -> None:
        import brokers

        brokers._registry_initialised = False
        brokers._default_registry = BrokerRegistry()

        from brokers.tiger.adapter import TigerBrokerAdapter

        brokers._default_registry.register("tiger", TigerBrokerAdapter)
        brokers._registry_initialised = True

        assert "tiger" in brokers.list_brokers()

    def test_currency_resolution(self, mock_tiger_components) -> None:
        from brokers.tiger.adapter import TigerBrokerAdapter

        assert TigerBrokerAdapter._resolve_currency("AAPL") == "USD"
        assert TigerBrokerAdapter._resolve_currency("0700.HK") == "HKD"
        assert TigerBrokerAdapter._resolve_currency("D05.SI") == "SGD"
        assert TigerBrokerAdapter._resolve_currency("tsla") == "USD"
        assert TigerBrokerAdapter._resolve_currency("9988.hk") == "HKD"

    def test_place_order_network_error(self, mock_tiger_components) -> None:
        mock_order = MagicMock()
        mock_order.id = None

        mock_tiger_components["session"].client.place_order.side_effect = Exception(
            "connection timeout"
        )

        with (
            patch("brokers.tiger.adapter._SDK_UTILS_AVAILABLE", True),
            patch("brokers.tiger.adapter.stock_contract", return_value=MagicMock()),
            patch("brokers.tiger.adapter.market_order", return_value=mock_order),
        ):
            adapter = _make_tiger_adapter()
            request = OrderRequest(
                ticker="AAPL",
                side=OrderSide.BUY,
                quantity=100,
                order_type=OrderType.MARKET,
            )
            with pytest.raises(BrokerConnectionError, match="network"):
                adapter.place_order(request)

    def test_get_tiger_broker(self, mock_tiger_components) -> None:
        import brokers

        brokers._registry_initialised = False
        brokers._default_registry = BrokerRegistry()

        from brokers.tiger.adapter import TigerBrokerAdapter

        brokers._default_registry.register("tiger", TigerBrokerAdapter)
        brokers._registry_initialised = True

        adapter = brokers.get_broker("tiger")
        assert isinstance(adapter, BrokerAdapter)
        assert adapter.broker_name == "tiger"
