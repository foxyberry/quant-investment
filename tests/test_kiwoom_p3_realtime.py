"""Tests for Kiwoom P3 screen manager and realtime subscriptions."""

import pytest

from kiwoom.realtime import RealtimeSubscriptionManager, ScreenManager


class _FakeOcx:
    def __init__(self):
        self.calls = []

    def dynamicCall(self, func_spec, *args):
        self.calls.append((func_spec, args))
        return 0


def test_screen_allocation_release_and_reuse() -> None:
    manager = ScreenManager(start=1000, end=1001)

    s1 = manager.allocate()
    s2 = manager.allocate()
    manager.release(s1)
    s3 = manager.allocate()

    assert s1 == "1000"
    assert s2 == "1001"
    assert s3 == "1000"


def test_screen_exhaustion_raises_runtime_error() -> None:
    manager = ScreenManager(start=1000, end=1000)
    _ = manager.allocate()

    with pytest.raises(RuntimeError):
        manager.allocate()


def test_register_calls_set_real_reg_with_expected_args() -> None:
    ocx = _FakeOcx()
    manager = RealtimeSubscriptionManager(ocx, ScreenManager(start=1100, end=1102))

    screen_no = manager.register("005930", [20, 10, 20, 11], real_type="1")

    assert screen_no == "1100"
    assert ocx.calls[-1] == (
        "SetRealReg(QString, QString, QString, QString)",
        ("1100", "005930", "10,11,20", "1"),
    )
    assert "005930" in manager.tracked_codes


def test_unregister_calls_set_real_remove_and_untracks_code() -> None:
    ocx = _FakeOcx()
    manager = RealtimeSubscriptionManager(ocx, ScreenManager(start=1200, end=1202))
    _ = manager.register("005930", [10, 11])

    manager.unregister("005930")

    assert ocx.calls[-1] == (
        "SetRealRemove(QString, QString)",
        ("1200", "005930"),
    )
    assert "005930" not in manager.tracked_codes


def test_clear_removes_all_tracked_codes() -> None:
    ocx = _FakeOcx()
    manager = RealtimeSubscriptionManager(ocx, ScreenManager(start=1300, end=1305))
    _ = manager.register("005930", [10])
    _ = manager.register("000660", [10])

    manager.clear()

    assert manager.tracked_codes == set()
    remove_calls = [call for call in ocx.calls if call[0] == "SetRealRemove(QString, QString)"]
    assert len(remove_calls) == 2


def test_invalid_code_raises_value_error() -> None:
    ocx = _FakeOcx()
    manager = RealtimeSubscriptionManager(ocx)

    with pytest.raises(ValueError):
        manager.register("", [10])


def test_invalid_fid_list_raises_value_error() -> None:
    ocx = _FakeOcx()
    manager = RealtimeSubscriptionManager(ocx)

    with pytest.raises(ValueError):
        manager.register("005930", [])
