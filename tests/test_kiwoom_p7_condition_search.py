"""Tests for Kiwoom P7 condition search realtime screening."""

import threading

import pytest

from brokers.kiwoom.condition_search import ConditionDefinition, ConditionSearchManager
from brokers.kiwoom.realtime import ScreenManager


class _FakeOcx:
    def __init__(self):
        self.calls = []
        self._callbacks = {}
        self._condition_name_list = ""
        self._stop_ret = 1

    def dynamicCall(self, func_spec, *args):
        self.calls.append((func_spec, args))

        if "GetConditionLoad()" in func_spec:
            cb = self._callbacks.get("OnReceiveConditionVer")
            if cb is not None:
                threading.Timer(0.01, lambda: cb(1, "OK")).start()
            return 1
        if "GetConditionNameList()" in func_spec:
            return self._condition_name_list
        if "SendCondition(QString, QString, int, int)" in func_spec:
            return 1
        if "SendConditionStop(QString, QString, int)" in func_spec:
            return self._stop_ret
        return 0


def test_load_conditions_waits_for_on_receive_condition_ver() -> None:
    ocx = _FakeOcx()
    manager = ConditionSearchManager(ocx)

    assert manager.load_conditions(timeout=0.2) is True


def test_get_condition_list_parses_expected_format() -> None:
    ocx = _FakeOcx()
    ocx._condition_name_list = "0^급등주;1^거래량폭증;2^돌파;"
    manager = ConditionSearchManager(ocx)

    conditions = manager.get_condition_list()

    assert conditions == [
        ConditionDefinition(index=0, name="급등주"),
        ConditionDefinition(index=1, name="거래량폭증"),
        ConditionDefinition(index=2, name="돌파"),
    ]


def test_start_and_stop_monitoring_manage_screen_and_calls() -> None:
    ocx = _FakeOcx()
    manager = ConditionSearchManager(ocx, screen_manager=ScreenManager(start=3100, end=3102))

    screen_no = manager.start_monitoring("급등주", 0)
    assert screen_no == "3100"
    assert ("SendCondition(QString, QString, int, int)", ("3100", "급등주", 0, 1)) in ocx.calls

    stopped = manager.stop_monitoring("급등주", 0)
    assert stopped is True
    assert ("SendConditionStop(QString, QString, int)", ("3100", "급등주", 0)) in ocx.calls


def test_stop_monitoring_keeps_state_when_send_condition_stop_fails() -> None:
    ocx = _FakeOcx()
    ocx._stop_ret = 0
    manager = ConditionSearchManager(ocx, screen_manager=ScreenManager(start=3110, end=3112))

    _ = manager.start_monitoring("급등주", 0)
    stopped = manager.stop_monitoring("급등주", 0)

    assert stopped is False
    assert manager.active_conditions[(0, "급등주")] == "3110"


def test_realtime_condition_limit_enforced() -> None:
    ocx = _FakeOcx()
    manager = ConditionSearchManager(ocx, screen_manager=ScreenManager(start=3200, end=3215))

    for i in range(ConditionSearchManager.MAX_REALTIME_CONDITIONS):
        _ = manager.start_monitoring(f"조건{i}", i)

    with pytest.raises(RuntimeError):
        manager.start_monitoring("초과조건", 999)


def test_tr_condition_and_real_condition_emit_discovery_payloads() -> None:
    ocx = _FakeOcx()
    watch_events = []
    signal_events = []
    manager = ConditionSearchManager(
        ocx,
        watchlist_sink=watch_events.append,
        signal_sink=signal_events.append,
    )

    manager.on_receive_tr_condition("3300", "005930;000660;", "급등주", 1, 0)
    manager.on_receive_real_condition("005930", "I", "급등주", "1")
    manager.on_receive_real_condition("005930", "D", "급등주", "1")

    assert len(watch_events) >= 3
    assert len(signal_events) >= 3
    assert watch_events[0]["action"] == "watch"
    assert watch_events[0]["ticker"] == "005930.KS"
    assert watch_events[-1]["action"] == "unwatch"


def test_observer_receives_condition_events() -> None:
    ocx = _FakeOcx()
    manager = ConditionSearchManager(ocx)
    events = []
    manager.add_observer(events.append)

    manager.on_receive_condition_ver(1, "ok")
    manager.on_receive_tr_condition("3400", "005930;", "급등주", 3, 0)
    manager.on_receive_real_condition("005930", "I", "급등주", "3")

    assert events[0]["type"] == "condition_ver"
    assert events[1]["type"] == "tr_condition"
    assert events[2]["type"] == "real_condition"


def test_invalid_condition_index_is_ignored_in_realtime_callback() -> None:
    ocx = _FakeOcx()
    manager = ConditionSearchManager(ocx)
    events = []
    manager.add_observer(events.append)

    manager.on_receive_real_condition("005930", "I", "급등주", "")
    manager.on_receive_real_condition("005930", "I", "급등주", "x")

    assert events == []


def test_discovery_ticker_uses_suffix_resolver() -> None:
    ocx = _FakeOcx()
    watch_events = []
    manager = ConditionSearchManager(
        ocx,
        watchlist_sink=watch_events.append,
        ticker_suffix_resolver=lambda code: "KQ" if code == "035720" else "KS",
    )

    manager.on_receive_real_condition("035720", "I", "코스닥조건", "1")
    assert watch_events[0]["ticker"] == "035720.KQ"
