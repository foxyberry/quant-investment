"""Unit tests for the brokers/ package public API.

Covers:
- brokers.exceptions  -- exception hierarchy and inheritance
- brokers.base        -- DTO validation, BrokerRegistry
- brokers.kiwoom.adapter -- KiwoomBrokerAdapter (KiwoomService fully mocked)
- brokers.__init__    -- module-level get_broker() / list_brokers()
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

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
    BrokerError,
    BrokerSafetyError,
    BrokerValidationError,
    OrderNotFoundError,
)
from kiwoom.safety import SafetyViolation

# =========================================================================
# 1. Exception hierarchy tests
# =========================================================================


class TestExceptionHierarchy:
    """Verify the broker exception hierarchy matches documented MRO."""

    def test_broker_error_is_runtime_error(self) -> None:
        assert issubclass(BrokerError, RuntimeError)
        err = BrokerError("boom")
        assert isinstance(err, RuntimeError)

    def test_broker_validation_error_is_value_error(self) -> None:
        assert issubclass(BrokerValidationError, ValueError)
        assert issubclass(BrokerValidationError, BrokerError)
        err = BrokerValidationError("bad input")
        assert isinstance(err, ValueError)
        assert isinstance(err, BrokerError)

    def test_order_not_found_is_key_error(self) -> None:
        assert issubclass(OrderNotFoundError, KeyError)
        assert issubclass(OrderNotFoundError, BrokerError)
        err = OrderNotFoundError("ORD999")
        assert isinstance(err, KeyError)
        assert isinstance(err, BrokerError)

    def test_broker_safety_error_is_broker_error(self) -> None:
        assert issubclass(BrokerSafetyError, BrokerError)
        err = BrokerSafetyError("kill switch active")
        assert isinstance(err, BrokerError)
        assert isinstance(err, RuntimeError)

    def test_broker_connection_error_is_broker_error(self) -> None:
        assert issubclass(BrokerConnectionError, BrokerError)
        err = BrokerConnectionError("timeout")
        assert isinstance(err, BrokerError)
        assert isinstance(err, RuntimeError)


# =========================================================================
# 2. DTO validation tests
# =========================================================================


class TestDTOValidation:
    """Verify Pydantic DTOs enforce constraints correctly."""

    def test_order_request_rejects_zero_quantity(self) -> None:
        with pytest.raises(ValidationError):
            OrderRequest(
                ticker="005930",
                side=OrderSide.BUY,
                quantity=0,
                order_type=OrderType.LIMIT,
                price=70000.0,
            )

    def test_order_request_market_without_price(self) -> None:
        req = OrderRequest(
            ticker="005930",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.MARKET,
            price=None,
        )
        assert req.price is None
        assert req.order_type == OrderType.MARKET

    def test_order_request_limit_with_price(self) -> None:
        req = OrderRequest(
            ticker="005930",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.LIMIT,
            price=100.0,
        )
        assert req.price == 100.0
        assert req.order_type == OrderType.LIMIT

    def test_order_snapshot_round_trip(self) -> None:
        snap = OrderSnapshot(
            order_id="ORD1",
            broker="kiwoom",
            ticker="005930",
            side=OrderSide.BUY,
            quantity=10,
            filled_quantity=5,
            unfilled_quantity=5,
            order_type=OrderType.LIMIT,
            price=70000.0,
            filled_price=69500.0,
            status=OrderStatus.PARTIAL,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:01:00",
        )
        dumped = snap.model_dump()
        reconstructed = OrderSnapshot(**dumped)
        assert reconstructed == snap
        assert reconstructed.order_id == "ORD1"
        assert reconstructed.filled_quantity == 5

    def test_amend_request_partial_fields(self) -> None:
        # Only quantity
        amend_qty = AmendRequest(quantity=20)
        assert amend_qty.quantity == 20
        assert amend_qty.price is None

        # Only price
        amend_price = AmendRequest(price=75000.0)
        assert amend_price.quantity is None
        assert amend_price.price == 75000.0

    def test_connection_status_defaults(self) -> None:
        status = ConnectionStatus(
            broker="test",
            status=ConnectionState.DISCONNECTED,
        )
        assert status.accounts == []
        assert status.is_paper_trading is None
        assert status.user_id is None
        assert status.updated_at is None


# =========================================================================
# 3. BrokerRegistry tests
# =========================================================================


class _DummyAdapter(BrokerAdapter):
    """Minimal concrete adapter for registry tests."""

    @property
    def broker_name(self) -> str:
        return "dummy"

    @property
    def supported_markets(self) -> list[str]:
        return ["TEST"]

    def get_connection_status(self) -> ConnectionStatus:
        return ConnectionStatus(
            broker="dummy", status=ConnectionState.CONNECTED
        )

    def place_order(self, request: OrderRequest) -> OrderSnapshot:
        raise NotImplementedError

    def get_orders(self) -> list[OrderSnapshot]:
        return []

    def cancel_order(self, order_id: str) -> None:
        raise NotImplementedError

    def amend_order(self, order_id: str, request: AmendRequest) -> None:
        raise NotImplementedError

    def activate_kill_switch(self) -> KillSwitchResult:
        raise NotImplementedError

    def subscribe_orders(self, callback: OrderCallback) -> None:
        pass

    def unsubscribe_orders(self, callback: OrderCallback) -> None:
        pass


class TestBrokerRegistry:
    """Verify BrokerRegistry register/get/list semantics."""

    def test_registry_register_and_get(self) -> None:
        registry = BrokerRegistry()
        registry.register("dummy", _DummyAdapter)
        adapter = registry.get("dummy")
        assert isinstance(adapter, _DummyAdapter)
        assert adapter.broker_name == "dummy"

    def test_registry_singleton(self) -> None:
        registry = BrokerRegistry()
        registry.register("dummy", _DummyAdapter)
        first = registry.get("dummy")
        second = registry.get("dummy")
        assert first is second

    def test_registry_unknown_raises_key_error(self) -> None:
        registry = BrokerRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.get("nonexistent")

    def test_registry_list_brokers(self) -> None:
        registry = BrokerRegistry()
        registry.register("beta", _DummyAdapter)
        registry.register("alpha", _DummyAdapter)
        assert registry.list_brokers() == ["alpha", "beta"]

    def test_registry_reject_non_adapter(self) -> None:
        registry = BrokerRegistry()
        with pytest.raises(TypeError, match="BrokerAdapter subclass"):
            registry.register("bad", dict)  # type: ignore[arg-type]


# =========================================================================
# 4. KiwoomBrokerAdapter tests (KiwoomService mocked)
# =========================================================================

# Shared raw order dict factory
_RAW_ORDER_TEMPLATE = {
    "order_id": "ORD1",
    "ticker": "005930",
    "side": "BUY",
    "quantity": 10,
    "filled_quantity": 0,
    "unfilled_quantity": 10,
    "order_type": "LIMIT",
    "price": 70000.0,
    "filled_price": None,
    "status": "RECEIVED",
    "created_at": "2026-01-01T00:00:00",
    "updated_at": None,
}


def _make_raw_order(**overrides: object) -> dict:
    """Return a copy of the template order dict with optional overrides."""
    d = dict(_RAW_ORDER_TEMPLATE)
    d.update(overrides)
    return d


@pytest.fixture()
def mock_kiwoom_service(monkeypatch):
    """Replace KiwoomService with a MagicMock before importing the adapter.

    The fixture patches ``KiwoomService`` at the module level so that
    ``KiwoomBrokerAdapter.__init__`` never touches real COM objects.
    """
    service = MagicMock()
    service._chejan = MagicMock()

    monkeypatch.setattr(
        "brokers.kiwoom.adapter.KiwoomService",
        MagicMock(get_instance=MagicMock(return_value=service)),
    )
    return service


def _make_adapter():
    """Instantiate a fresh KiwoomBrokerAdapter (call after patching)."""
    from brokers.kiwoom.adapter import KiwoomBrokerAdapter

    return KiwoomBrokerAdapter()


# -- Identity --------------------------------------------------------------


class TestKiwoomIdentity:
    def test_broker_name(self, mock_kiwoom_service) -> None:
        adapter = _make_adapter()
        assert adapter.broker_name == "kiwoom"

    def test_supported_markets(self, mock_kiwoom_service) -> None:
        adapter = _make_adapter()
        assert adapter.supported_markets == ["KRX"]


# -- Connection status -----------------------------------------------------


class TestKiwoomConnectionStatus:
    def test_get_connection_status(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.get_connection_status.return_value = {
            "status": "connected",
            "is_mock_trading": True,
            "user_id": "test",
            "accounts": ["123"],
            "updated_at": "2026-01-01T00:00:00",
        }
        adapter = _make_adapter()
        result = adapter.get_connection_status()

        assert result.broker == "kiwoom"
        assert result.status == ConnectionState.CONNECTED
        assert result.is_paper_trading is True
        assert result.user_id == "test"
        assert result.accounts == ["123"]
        assert result.updated_at == "2026-01-01T00:00:00"


# -- place_order -----------------------------------------------------------


class TestKiwoomPlaceOrder:
    def test_place_order_success(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.place_order.return_value = _make_raw_order()
        adapter = _make_adapter()

        request = OrderRequest(
            ticker="005930",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.LIMIT,
            price=70000.0,
        )
        result = adapter.place_order(request)

        assert isinstance(result, OrderSnapshot)
        assert result.broker == "kiwoom"
        assert result.order_id == "ORD1"
        assert result.status == OrderStatus.RECEIVED

        mock_kiwoom_service.place_order.assert_called_once_with(
            ticker="005930",
            side="BUY",
            quantity=10,
            order_type="LIMIT",
            price=70000.0,
        )

    def test_place_order_validation_error(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.place_order.side_effect = ValueError("bad ticker")
        adapter = _make_adapter()

        request = OrderRequest(
            ticker="INVALID",
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.MARKET,
        )

        with pytest.raises(BrokerValidationError, match="bad ticker"):
            adapter.place_order(request)

    def test_place_order_safety_violation(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.place_order.side_effect = SafetyViolation(
            "kill switch"
        )
        adapter = _make_adapter()

        request = OrderRequest(
            ticker="005930",
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.MARKET,
        )

        with pytest.raises(BrokerSafetyError, match="kill switch"):
            adapter.place_order(request)

    def test_place_order_no_accounts(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.place_order.side_effect = RuntimeError(
            "No accounts available"
        )
        adapter = _make_adapter()

        request = OrderRequest(
            ticker="005930",
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.MARKET,
        )

        with pytest.raises(BrokerConnectionError, match="No accounts"):
            adapter.place_order(request)

    def test_place_order_runtime_error(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.place_order.side_effect = RuntimeError(
            "OCX failure"
        )
        adapter = _make_adapter()

        request = OrderRequest(
            ticker="005930",
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.MARKET,
        )

        with pytest.raises(BrokerError, match="OCX failure"):
            adapter.place_order(request)


# -- get_orders ------------------------------------------------------------


class TestKiwoomGetOrders:
    def test_get_orders(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.get_orders.return_value = [
            _make_raw_order(order_id="ORD1"),
            _make_raw_order(order_id="ORD2", status="FILLED", filled_quantity=10, unfilled_quantity=0),
        ]
        adapter = _make_adapter()
        orders = adapter.get_orders()

        assert len(orders) == 2
        assert all(isinstance(o, OrderSnapshot) for o in orders)
        assert orders[0].order_id == "ORD1"
        assert orders[1].order_id == "ORD2"
        assert orders[1].status == OrderStatus.FILLED


# -- cancel_order ----------------------------------------------------------


class TestKiwoomCancelOrder:
    def test_cancel_order_success(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.cancel_order.return_value = None
        adapter = _make_adapter()
        adapter.cancel_order("ORD1")
        mock_kiwoom_service.cancel_order.assert_called_once_with("ORD1")

    def test_cancel_order_not_found(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.cancel_order.side_effect = KeyError("ORD999")
        adapter = _make_adapter()

        with pytest.raises(OrderNotFoundError):
            adapter.cancel_order("ORD999")

    def test_cancel_order_safety(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.cancel_order.side_effect = SafetyViolation(
            "blocked"
        )
        adapter = _make_adapter()

        with pytest.raises(BrokerSafetyError, match="blocked"):
            adapter.cancel_order("ORD1")


# -- amend_order -----------------------------------------------------------


class TestKiwoomAmendOrder:
    def test_amend_order_success(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.amend_order.return_value = None
        adapter = _make_adapter()

        amend = AmendRequest(quantity=20, price=71000.0)
        adapter.amend_order("ORD1", amend)

        mock_kiwoom_service.amend_order.assert_called_once_with(
            order_id="ORD1",
            quantity=20,
            price=71000.0,
        )

    def test_amend_order_not_found(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.amend_order.side_effect = KeyError("ORD999")
        adapter = _make_adapter()

        with pytest.raises(OrderNotFoundError):
            adapter.amend_order("ORD999", AmendRequest(quantity=5))

    def test_amend_order_validation_error(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.amend_order.side_effect = ValueError(
            "invalid quantity"
        )
        adapter = _make_adapter()

        with pytest.raises(BrokerValidationError, match="invalid quantity"):
            adapter.amend_order("ORD1", AmendRequest(price=0.0))


# -- kill switch -----------------------------------------------------------


class TestKiwoomKillSwitch:
    def test_kill_switch(self, mock_kiwoom_service) -> None:
        mock_kiwoom_service.activate_kill_switch.return_value = {
            "activated": True,
            "cancelled_orders": 3,
        }
        adapter = _make_adapter()
        result = adapter.activate_kill_switch()

        assert isinstance(result, KillSwitchResult)
        assert result.activated is True
        assert result.cancelled_orders == 3


# -- subscribe / unsubscribe / chejan dispatch -----------------------------


class TestKiwoomSubscription:
    def test_subscribe_and_dispatch(self, mock_kiwoom_service) -> None:
        adapter = _make_adapter()

        received: list[OrderEvent] = []
        callback: OrderCallback = lambda ev: received.append(ev)
        adapter.subscribe_orders(callback)

        # Simulate a chejan order event
        adapter._on_chejan_event(
            {
                "type": "order",
                "order_no": "ORD42",
                "code": "005930",
                "status": "FILLED",
                "filled_qty": 10,
                "unfilled_qty": 0,
                "fill_price": 70000,
            }
        )

        assert len(received) == 1
        event = received[0]
        assert event.order_id == "ORD42"
        assert event.broker == "kiwoom"
        assert event.status == OrderStatus.FILLED
        assert event.filled_quantity == 10
        assert event.filled_price == 70000.0

    def test_subscribe_ignores_balance_events(
        self, mock_kiwoom_service
    ) -> None:
        adapter = _make_adapter()

        received: list[OrderEvent] = []
        adapter.subscribe_orders(lambda ev: received.append(ev))

        adapter._on_chejan_event(
            {
                "type": "balance",
                "order_no": "ORD42",
                "code": "005930",
                "status": "FILLED",
            }
        )

        assert len(received) == 0

    def test_subscribe_ignores_no_order_no(
        self, mock_kiwoom_service
    ) -> None:
        adapter = _make_adapter()

        received: list[OrderEvent] = []
        adapter.subscribe_orders(lambda ev: received.append(ev))

        adapter._on_chejan_event(
            {
                "type": "order",
                "order_no": "",
                "code": "005930",
                "status": "FILLED",
            }
        )

        assert len(received) == 0

    def test_unsubscribe_removes_callback(
        self, mock_kiwoom_service
    ) -> None:
        adapter = _make_adapter()

        received: list[OrderEvent] = []
        callback: OrderCallback = lambda ev: received.append(ev)
        adapter.subscribe_orders(callback)
        adapter.unsubscribe_orders(callback)

        adapter._on_chejan_event(
            {
                "type": "order",
                "order_no": "ORD42",
                "code": "005930",
                "status": "FILLED",
                "filled_qty": 10,
                "unfilled_qty": 0,
                "fill_price": 70000,
            }
        )

        assert len(received) == 0

    def test_subscribe_no_duplicates(self, mock_kiwoom_service) -> None:
        adapter = _make_adapter()

        call_count = 0

        def counting_callback(ev: OrderEvent) -> None:
            nonlocal call_count
            call_count += 1

        # Register the same callback twice
        adapter.subscribe_orders(counting_callback)
        adapter.subscribe_orders(counting_callback)

        adapter._on_chejan_event(
            {
                "type": "order",
                "order_no": "ORD42",
                "code": "005930",
                "status": "FILLED",
                "filled_qty": 10,
                "unfilled_qty": 0,
                "fill_price": 70000,
            }
        )

        # Should only be called once despite two registrations
        assert call_count == 1


# -- chejan status mapping -------------------------------------------------


class TestChejanStatusMapping:
    """Verify raw chejan status strings map to canonical OrderStatus."""

    @pytest.fixture(autouse=True)
    def _setup(self, mock_kiwoom_service):
        self.adapter = _make_adapter()

    def _dispatch_and_get_status(self, raw_status: str) -> OrderStatus:
        received: list[OrderEvent] = []
        callback: OrderCallback = lambda ev: received.append(ev)
        self.adapter.subscribe_orders(callback)

        self.adapter._on_chejan_event(
            {
                "type": "order",
                "order_no": "ORD1",
                "code": "005930",
                "status": raw_status,
                "filled_qty": 0,
                "unfilled_qty": 10,
                "fill_price": None,
            }
        )

        self.adapter.unsubscribe_orders(callback)
        assert len(received) == 1
        return received[0].status

    def test_cancelled_maps_to_canceled(self) -> None:
        assert self._dispatch_and_get_status("CANCELLED") == OrderStatus.CANCELED

    def test_placed_maps_to_confirmed(self) -> None:
        assert self._dispatch_and_get_status("PLACED") == OrderStatus.CONFIRMED

    def test_pending_maps_to_received(self) -> None:
        assert self._dispatch_and_get_status("PENDING") == OrderStatus.RECEIVED

    def test_filled_maps_to_filled(self) -> None:
        assert self._dispatch_and_get_status("FILLED") == OrderStatus.FILLED

    def test_unknown_falls_back_to_received(self) -> None:
        assert self._dispatch_and_get_status("XYZABC") == OrderStatus.RECEIVED


# =========================================================================
# 5. Module-level convenience functions
# =========================================================================


class TestModuleLevelFunctions:
    """Test brokers.get_broker() and brokers.list_brokers()."""

    def test_list_brokers_includes_kiwoom(self, mock_kiwoom_service) -> None:
        import brokers

        # Reset the module registry state so our mock is used
        brokers._registry_initialised = False
        brokers._default_registry = BrokerRegistry()

        # Manually register with the mocked adapter class
        from brokers.kiwoom.adapter import KiwoomBrokerAdapter

        brokers._default_registry.register("kiwoom", KiwoomBrokerAdapter)
        brokers._registry_initialised = True

        result = brokers.list_brokers()
        assert "kiwoom" in result

    def test_get_broker_returns_adapter(self, mock_kiwoom_service) -> None:
        import brokers

        brokers._registry_initialised = False
        brokers._default_registry = BrokerRegistry()

        from brokers.kiwoom.adapter import KiwoomBrokerAdapter

        brokers._default_registry.register("kiwoom", KiwoomBrokerAdapter)
        brokers._registry_initialised = True

        adapter = brokers.get_broker("kiwoom")
        assert isinstance(adapter, BrokerAdapter)
        assert adapter.broker_name == "kiwoom"

    def test_get_broker_unknown_raises(self, mock_kiwoom_service) -> None:
        import brokers

        brokers._registry_initialised = False
        brokers._default_registry = BrokerRegistry()
        brokers._registry_initialised = True

        with pytest.raises(KeyError, match="not registered"):
            brokers.get_broker("nonexistent")
