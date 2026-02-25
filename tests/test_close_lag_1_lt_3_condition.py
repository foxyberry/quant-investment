import pandas as pd

from screener.conditions.price import CloseLag1Lt3Condition
from screener.conditions.registry import get_condition_metadata


def _make_df(closes):
    return pd.DataFrame({"close": closes})


def test_close_lag_1_lt_3_matches_when_t1_lower_than_t3():
    # current=t, compare t-1(97) vs t-3(100): 97 < 100 => True
    closes = [95, 98, 100, 99, 97, 96]
    cond = CloseLag1Lt3Condition()
    result = cond.evaluate("TEST", _make_df(closes))

    assert bool(result.matched) is True
    assert result.details["left_lag"] == 1
    assert result.details["right_lag"] == 3
    assert result.details["operator"] == "lt"


def test_close_lag_1_lt_3_not_matched_when_t1_not_lower_than_t3():
    # current=t, compare t-1(102) vs t-3(100): 102 < 100 => False
    closes = [95, 98, 100, 101, 102, 103]
    cond = CloseLag1Lt3Condition()
    result = cond.evaluate("TEST", _make_df(closes))

    assert bool(result.matched) is False


def test_close_lag_1_lt_3_insufficient_data():
    cond = CloseLag1Lt3Condition()
    result = cond.evaluate("TEST", _make_df([100, 101]))

    assert bool(result.matched) is False
    assert "error" in result.details


def test_close_lag_1_lt_3_registered_metadata():
    metadata = get_condition_metadata()

    assert "close_lag_1_lt_3" in metadata
    assert metadata["close_lag_1_lt_3"]["category"] == "price"
