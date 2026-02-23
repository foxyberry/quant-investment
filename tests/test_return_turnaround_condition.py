import pandas as pd

from screener.conditions.price import ReturnTurnaroundCondition
from screener.conditions.registry import get_condition_metadata


def _make_df(closes):
    return pd.DataFrame({"close": closes})


def test_return_turnaround_matched():
    # prev 5d: 100 -> 95 (-5%), recent 5d: 95 -> 100 (+5.26%)
    closes = [100, 99, 98, 97, 96, 95, 96, 97, 98, 99, 100]
    cond = ReturnTurnaroundCondition(period_days=5, prev_max_return_pct=-2.0, min_return_pct=2.0)
    result = cond.evaluate("TEST", _make_df(closes))
    assert bool(result.matched) is True
    assert result.details["prev_return_pct"] <= -2.0
    assert result.details["recent_return_pct"] >= 2.0


def test_return_turnaround_not_matched_when_recent_is_weak():
    # prev 5d: -5%, recent 5d: +1.05% (below min_return_pct=2)
    closes = [100, 99, 98, 97, 96, 95, 95.2, 95.4, 95.6, 95.8, 96]
    cond = ReturnTurnaroundCondition(period_days=5, prev_max_return_pct=-2.0, min_return_pct=2.0)
    result = cond.evaluate("TEST", _make_df(closes))
    assert bool(result.matched) is False
    assert result.details["recent_return_pct"] < 2.0


def test_return_turnaround_insufficient_data():
    cond = ReturnTurnaroundCondition(period_days=5)
    result = cond.evaluate("TEST", _make_df([100, 99, 98]))
    assert bool(result.matched) is False
    assert "error" in result.details


def test_return_turnaround_registered_metadata():
    metadata = get_condition_metadata()
    assert "return_turnaround" in metadata
    assert metadata["return_turnaround"]["category"] == "price"
