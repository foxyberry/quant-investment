"""Tests for global macro snapshot service."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from api.services.global_macro_service import GlobalMacroService


class _ImmediateFuture:
    def __init__(self, fn, *args, **kwargs):
        self._result = None
        self._error = None
        try:
            self._result = fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            self._error = exc

    def result(self, timeout=None):
        if self._error is not None:
            raise self._error
        return self._result


class _ImmediateExecutor:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args, **kwargs):
        return _ImmediateFuture(fn, *args, **kwargs)


def test_fetch_ticker_returns_value_from_fast_info():
    service = GlobalMacroService()
    hist = pd.DataFrame(
        {"Close": [100.0, 100.0]},
        index=pd.to_datetime(["2026-03-10", "2026-03-11"]),
    )

    class _Ticker:
        fast_info = {"lastPrice": 101.0}

        def history(self, period="1d", **kwargs):
            assert period == "2d"
            return hist

    with patch("api.services.global_macro_service.yf.Ticker", return_value=_Ticker()):
        value, change_pct, as_of = service._fetch_ticker(["CL=F"])

    assert value == 101.0
    assert change_pct == 1.0
    assert as_of == "2026-03-11T00:00:00"


def test_fetch_ticker_falls_back_to_history():
    service = GlobalMacroService()
    hist = pd.DataFrame(
        {"Close": [98.0, 100.0]},
        index=pd.to_datetime(["2026-03-10", "2026-03-11"]),
    )

    class _Ticker:
        @property
        def fast_info(self):
            raise RuntimeError("fast_info fail")

        def history(self, period="1d", **kwargs):
            return hist

    with patch("api.services.global_macro_service.yf.Ticker", return_value=_Ticker()):
        value, change_pct, as_of = service._fetch_ticker(["GC=F"])

    assert value == 100.0
    assert change_pct == 2.0408
    assert as_of == "2026-03-11T00:00:00"


def test_fetch_ticker_tries_fallback_symbol():
    service = GlobalMacroService()
    hist = pd.DataFrame(
        {"Close": [100.0, 102.0]},
        index=pd.to_datetime(["2026-03-10", "2026-03-11"]),
    )

    class _FailTicker:
        @property
        def fast_info(self):
            raise RuntimeError("primary fail")

        def history(self, period="1d", **kwargs):
            raise RuntimeError("history fail")

    class _OkTicker:
        fast_info = {"lastPrice": 103.0}

        def history(self, period="1d", **kwargs):
            return hist

    def _ticker_factory(symbol):
        if symbol == "DX-Y.NYB":
            return _FailTicker()
        if symbol == "DX=F":
            return _OkTicker()
        raise AssertionError("unexpected symbol")

    with patch("api.services.global_macro_service.yf.Ticker", side_effect=_ticker_factory):
        value, change_pct, as_of = service._fetch_ticker(["DX-Y.NYB", "DX=F"])

    assert value == 103.0
    assert change_pct == 3.0
    assert as_of == "2026-03-11T00:00:00"


def test_fetch_ticker_returns_none_on_all_failures():
    service = GlobalMacroService()

    class _FailTicker:
        @property
        def fast_info(self):
            raise RuntimeError("fail")

        def history(self, period="1d", **kwargs):
            raise RuntimeError("fail")

    with patch("api.services.global_macro_service.yf.Ticker", return_value=_FailTicker()):
        value, change_pct, as_of = service._fetch_ticker(["DX-Y.NYB", "DX=F"])

    assert value is None
    assert change_pct is None
    assert as_of is None


def test_get_snapshot_returns_all_tickers():
    service = GlobalMacroService()

    result_map = {
        ("DX-Y.NYB", "DX=F"): (104.0, 0.1, "2026-03-11T00:00:00"),
        ("CL=F",): (75.0, -0.2, "2026-03-11T00:00:00"),
        ("GC=F",): (2100.0, 0.3, "2026-03-11T00:00:00"),
        ("HG=F",): (4.2, 0.4, "2026-03-11T00:00:00"),
        ("EEM",): (42.0, 0.5, "2026-03-11T00:00:00"),
        ("EFA",): (84.0, 0.6, "2026-03-11T00:00:00"),
    }

    with (
        patch(
            "api.services.global_macro_service.concurrent.futures.ThreadPoolExecutor",
            _ImmediateExecutor,
        ),
        patch.object(service, "_fetch_ticker", side_effect=lambda symbols: result_map[tuple(symbols)]),
    ):
        snapshot = service.get_snapshot()

    assert snapshot is not None
    assert set(snapshot.keys()) == {
        "dxy",
        "wti",
        "gold",
        "copper",
        "msci_em",
        "msci_dm",
        "em_dm_ratio",
        "copper_gold_ratio",
    }
    assert snapshot["dxy"]["value"] == 104.0
    assert snapshot["em_dm_ratio"] == 0.5
    assert snapshot["copper_gold_ratio"] == 0.002


def test_get_snapshot_null_safe_on_partial_failures():
    service = GlobalMacroService()

    result_map = {
        ("DX-Y.NYB", "DX=F"): (None, None, None),
        ("CL=F",): (None, None, None),
        ("GC=F",): (2000.0, 0.2, "2026-03-11T00:00:00"),
        ("HG=F",): (4.0, 0.1, "2026-03-11T00:00:00"),
        ("EEM",): (None, None, None),
        ("EFA",): (80.0, -0.1, "2026-03-11T00:00:00"),
    }

    with (
        patch(
            "api.services.global_macro_service.concurrent.futures.ThreadPoolExecutor",
            _ImmediateExecutor,
        ),
        patch.object(service, "_fetch_ticker", side_effect=lambda symbols: result_map[tuple(symbols)]),
    ):
        snapshot = service.get_snapshot()

    assert snapshot is not None
    assert snapshot["dxy"]["value"] is None
    assert snapshot["gold"]["value"] == 2000.0
    assert snapshot["em_dm_ratio"] is None
    assert snapshot["copper_gold_ratio"] == 0.002


def test_get_snapshot_returns_none_when_all_fail():
    service = GlobalMacroService()

    with (
        patch(
            "api.services.global_macro_service.concurrent.futures.ThreadPoolExecutor",
            _ImmediateExecutor,
        ),
        patch.object(service, "_fetch_ticker", return_value=(None, None, None)),
    ):
        snapshot = service.get_snapshot()

    assert snapshot is None


def test_em_dm_ratio_calculation():
    service = GlobalMacroService()

    result_map = {
        ("DX-Y.NYB", "DX=F"): (100.0, None, None),
        ("CL=F",): (70.0, None, None),
        ("GC=F",): (2000.0, None, None),
        ("HG=F",): (4.5, None, None),
        ("EEM",): (40.0, None, None),
        ("EFA",): (80.0, None, None),
    }

    with (
        patch(
            "api.services.global_macro_service.concurrent.futures.ThreadPoolExecutor",
            _ImmediateExecutor,
        ),
        patch.object(service, "_fetch_ticker", side_effect=lambda symbols: result_map[tuple(symbols)]),
    ):
        snapshot = service.get_snapshot()

    assert snapshot is not None
    assert snapshot["em_dm_ratio"] == 0.5


def test_copper_gold_ratio_calculation():
    service = GlobalMacroService()

    result_map = {
        ("DX-Y.NYB", "DX=F"): (100.0, None, None),
        ("CL=F",): (70.0, None, None),
        ("GC=F",): (2000.0, None, None),
        ("HG=F",): (4.5, None, None),
        ("EEM",): (40.0, None, None),
        ("EFA",): (80.0, None, None),
    }

    with (
        patch(
            "api.services.global_macro_service.concurrent.futures.ThreadPoolExecutor",
            _ImmediateExecutor,
        ),
        patch.object(service, "_fetch_ticker", side_effect=lambda symbols: result_map[tuple(symbols)]),
    ):
        snapshot = service.get_snapshot()

    assert snapshot is not None
    assert snapshot["copper_gold_ratio"] == 0.00225


def test_em_dm_ratio_none_when_missing():
    service = GlobalMacroService()

    result_map = {
        ("DX-Y.NYB", "DX=F"): (100.0, None, None),
        ("CL=F",): (70.0, None, None),
        ("GC=F",): (2000.0, None, None),
        ("HG=F",): (4.5, None, None),
        ("EEM",): (None, None, None),
        ("EFA",): (80.0, None, None),
    }

    with (
        patch(
            "api.services.global_macro_service.concurrent.futures.ThreadPoolExecutor",
            _ImmediateExecutor,
        ),
        patch.object(service, "_fetch_ticker", side_effect=lambda symbols: result_map[tuple(symbols)]),
    ):
        snapshot = service.get_snapshot()

    assert snapshot is not None
    assert snapshot["em_dm_ratio"] is None
