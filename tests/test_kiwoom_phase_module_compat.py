"""Compatibility tests for phase-documented Kiwoom module paths."""

from kiwoom.screen_manager import ScreenManager
from kiwoom.tr_request import KiwoomTrClient, TrRequest


class _FakeOcx:
    def dynamicCall(self, *_args, **_kwargs):
        return 0


def test_tr_request_module_re_exports() -> None:
    client = KiwoomTrClient(_FakeOcx())
    req = TrRequest(rq_name="rq", tr_code="opt10001", prev_next=0, screen_no="1001")
    assert client is not None
    assert req.tr_code == "opt10001"


def test_screen_manager_module_re_exports() -> None:
    manager = ScreenManager(start=1000, end=1001)
    first = manager.allocate()
    second = manager.allocate()
    assert first == "1000"
    assert second == "1001"
