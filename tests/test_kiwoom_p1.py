"""Tests for Kiwoom P1 scaffolding: constants and mock connection/login."""

import threading

import pytest

from brokers.kiwoom import (
    ChejanGubun,
    ErrorCode,
    FID,
    HogaType,
    KiwoomConnection,
    MarketType,
    OrderType,
    RealType,
    ServerType,
)
from brokers.kiwoom.connection import _error_description


def test_public_exports_available() -> None:
    """Module-level exports should be importable from kiwoom package."""
    assert KiwoomConnection is not None
    assert ErrorCode.OP_ERR_NONE == 0
    assert OrderType.NEW_BUY == 1
    assert HogaType.MARKET == "03"
    assert MarketType.KOSPI == "STK"
    assert RealType.STOCK_EXECUTION == "주식체결"
    assert ChejanGubun.ORDER == "0"
    assert ServerType.MOCK == "1"


def test_error_description_known_and_unknown() -> None:
    """_error_description should resolve known enums and fallback on unknown."""
    assert _error_description(0) == "OP_ERR_NONE (0)"
    assert _error_description(-9999) == "Unknown error (-9999)"


def test_fid_namespace_cannot_be_instantiated_or_subclassed() -> None:
    """FID is a namespace class and should reject object creation/subclassing."""
    with pytest.raises(TypeError):
        FID()

    with pytest.raises(TypeError):

        class _BadFID(FID):
            pass


def test_login_success_in_mock_mode() -> None:
    """Mock mode login should complete and mark session as connected."""
    conn = KiwoomConnection(mock=True)

    assert conn.login() is True
    assert conn.is_connected() is True
    assert conn.is_mock_trading() is True


def test_get_account_list_parsing() -> None:
    """Account list should be parsed from semicolon-delimited ACCNO payload."""
    conn = KiwoomConnection(mock=True)
    accounts = conn.get_account_list()

    assert accounts == ["8012345678", "8098765432"]


def test_logout_clears_connected_state() -> None:
    """logout() should transition connected session to disconnected."""
    conn = KiwoomConnection(mock=True)
    assert conn.login() is True

    conn.logout()

    assert conn.is_connected() is False


def test_login_failure_when_commconnect_returns_error() -> None:
    """login() should fail immediately when CommConnect returns non-zero."""
    conn = KiwoomConnection(mock=True)

    original_dynamic_call = conn.ocx.dynamicCall

    def failing_dynamic_call(func_spec, *args):
        if "CommConnect()" in func_spec:
            return -100
        return original_dynamic_call(func_spec, *args)

    conn.ocx.dynamicCall = failing_dynamic_call

    assert conn.login() is False
    assert conn.is_connected() is False


def test_login_failure_when_event_returns_error_code() -> None:
    """login() should fail when OnEventConnect callback reports non-zero code."""
    conn = KiwoomConnection(mock=True)

    def dynamic_call_with_failed_event(func_spec, *args):
        if "CommConnect()" in func_spec:
            threading.Timer(0.01, lambda: conn._on_event_connect(-100)).start()
            return 0
        return ""

    conn.ocx.dynamicCall = dynamic_call_with_failed_event

    assert conn.login() is False
    assert conn.is_connected() is False


def test_login_timeout_when_event_never_arrives() -> None:
    """login() should timeout and fail if OnEventConnect is never fired."""
    conn = KiwoomConnection(mock=True)
    conn._LOGIN_TIMEOUT = 0.05

    conn.ocx.dynamicCall = lambda func_spec, *args: 0

    assert conn.login() is False
    assert conn.is_connected() is False
