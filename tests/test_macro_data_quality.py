"""Tests for _compute_data_quality overall field in api/routers/market.py."""

from __future__ import annotations

import pytest

from api.routers.market import _compute_data_quality


def _make_bundle(
    fx_age: float | None = 100,
    futures_age: float | None = 100,
    flow_age: float | None = 100,
    *,
    fx_present: bool = True,
    futures_present: bool = True,
    flow_present: bool = True,
) -> dict:
    """Build a minimal bundle dict for _compute_data_quality."""
    bundle: dict = {
        "freshness": {
            "fx_age_sec": fx_age,
            "futures_age_sec": futures_age,
            "flow_age_sec": flow_age,
        },
    }
    if fx_present:
        bundle["fx"] = {"value": 1350.0}
    if futures_present:
        bundle["futures"] = {"value": 350.0}
    if flow_present:
        bundle["flow"] = {"foreign_net": -100_000_000}
    return bundle


class TestDataQualityOverall:
    """Test overall sufficiency gating logic."""

    def test_all_ok(self):
        """0 bad sources → sufficient."""
        dq = _compute_data_quality(_make_bundle(), is_kr=True)
        assert dq.overall == "sufficient"
        assert dq.fx == "ok"
        assert dq.futures == "ok"
        assert dq.flow == "ok"

    def test_one_stale(self):
        """1 bad source → sufficient."""
        dq = _compute_data_quality(
            _make_bundle(fx_age=5000),  # stale (>1200s)
            is_kr=True,
        )
        assert dq.overall == "sufficient"
        assert dq.fx == "stale"

    def test_two_stale(self):
        """2 bad sources → insufficient."""
        dq = _compute_data_quality(
            _make_bundle(fx_age=5000, futures_age=5000),
            is_kr=True,
        )
        assert dq.overall == "insufficient"

    def test_two_missing(self):
        """2 missing sources → insufficient."""
        dq = _compute_data_quality(
            _make_bundle(fx_present=False, flow_present=False),
            is_kr=True,
        )
        assert dq.overall == "insufficient"
        assert dq.fx == "missing"
        assert dq.flow == "missing"

    def test_mixed_stale_and_missing(self):
        """1 stale + 1 missing = 2 bad → insufficient."""
        dq = _compute_data_quality(
            _make_bundle(fx_age=5000, futures_present=False),
            is_kr=True,
        )
        assert dq.overall == "insufficient"

    def test_all_missing(self):
        """3 bad sources → insufficient."""
        dq = _compute_data_quality(
            _make_bundle(fx_present=False, futures_present=False, flow_present=False),
            is_kr=True,
        )
        assert dq.overall == "insufficient"

    def test_us_mode_always_sufficient(self):
        """US mode always returns sufficient (KR gating doesn't apply)."""
        dq = _compute_data_quality({}, is_kr=False)
        assert dq.overall == "sufficient"
        assert dq.fx is None
        assert dq.futures is None
        assert dq.flow is None
