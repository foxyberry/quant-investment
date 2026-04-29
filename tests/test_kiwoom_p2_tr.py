"""Tests for Kiwoom P2 TR request helpers."""

import pytest

from brokers.kiwoom.tr import KiwoomTrClient, TrRequest


class _FakeOcx:
    def __init__(self):
        self.calls = []

    def dynamicCall(self, func_spec, *args):
        self.calls.append((func_spec, args))
        if "CommRqData" in func_spec:
            return 0
        if "GetCommData" in func_spec:
            return " 12345 "
        if "GetRepeatCnt" in func_spec:
            return 7
        return ""


def test_set_input_value_delegates_to_ocx() -> None:
    ocx = _FakeOcx()
    client = KiwoomTrClient(ocx)

    client.set_input_value("종목코드", "005930")

    assert ocx.calls[-1] == (
        "SetInputValue(QString, QString)",
        ("종목코드", "005930"),
    )


def test_comm_rq_data_delegates_and_returns_int() -> None:
    ocx = _FakeOcx()
    client = KiwoomTrClient(ocx)
    request = TrRequest(rq_name="opt10001_req", tr_code="opt10001", prev_next=0, screen_no="1001")

    ret = client.comm_rq_data(request)

    assert ret == 0
    assert ocx.calls[-1] == (
        "CommRqData(QString, QString, int, QString)",
        ("opt10001_req", "opt10001", 0, "1001"),
    )


def test_get_comm_data_returns_stripped_string() -> None:
    ocx = _FakeOcx()
    client = KiwoomTrClient(ocx)

    value = client.get_comm_data("opt10001", "주식기본정보", 0, "현재가")

    assert value == "12345"


def test_get_repeat_cnt_returns_int() -> None:
    ocx = _FakeOcx()
    client = KiwoomTrClient(ocx)

    count = client.get_repeat_cnt("opt10081", "주식일봉차트")

    assert count == 7


def test_invalid_screen_no_raises_value_error() -> None:
    with pytest.raises(ValueError):
        TrRequest(rq_name="rq", tr_code="tr", prev_next=0, screen_no="12")


def test_empty_rq_name_raises_value_error() -> None:
    with pytest.raises(ValueError):
        TrRequest(rq_name="", tr_code="tr", prev_next=0, screen_no="1234")


def test_empty_tr_code_raises_value_error() -> None:
    with pytest.raises(ValueError):
        TrRequest(rq_name="rq", tr_code="", prev_next=0, screen_no="1234")


def test_tr_request_normalizes_whitespace_fields() -> None:
    request = TrRequest(
        rq_name="  opt10001_req  ",
        tr_code="  opt10001  ",
        prev_next=0,
        screen_no="1001",
    )
    assert request.rq_name == "opt10001_req"
    assert request.tr_code == "opt10001"
