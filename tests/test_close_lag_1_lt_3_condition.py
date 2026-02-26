import pandas as pd

from screener.conditions.basic_catalog import PriceLagCompareCondition
from screener.conditions.registry import get_condition_metadata


def _make_df(closes):
    return pd.DataFrame({"close": closes})


def test_close_lag_1_lt_3_matches_when_t1_lower_than_t3():
    # current=t, compare t-1(97) vs t-3(100): 97 < 100 => True
    closes = [95, 98, 100, 99, 97, 96]
    cond = PriceLagCompareCondition(field="close", lag_a=1, lag_b=3, operator="lt")
    result = cond.evaluate("TEST", _make_df(closes))

    assert bool(result.matched) is True
    assert result.details["lag_a"] == 1
    assert result.details["lag_b"] == 3
    assert result.details["operator"] == "lt"


def test_close_lag_1_lt_3_not_matched_when_t1_not_lower_than_t3():
    # current=t, compare t-1(102) vs t-3(100): 102 < 100 => False
    closes = [95, 98, 100, 101, 102, 103]
    cond = PriceLagCompareCondition(field="close", lag_a=1, lag_b=3, operator="lt")
    result = cond.evaluate("TEST", _make_df(closes))

    assert bool(result.matched) is False


def test_close_lag_1_lt_3_insufficient_data():
    cond = PriceLagCompareCondition(field="close", lag_a=1, lag_b=3, operator="lt")
    result = cond.evaluate("TEST", _make_df([100, 101]))

    assert bool(result.matched) is False
    assert "error" in result.details


def test_price_lag_compare_registered_metadata():
    metadata = get_condition_metadata()

    assert "price_lag_compare" in metadata
    assert metadata["price_lag_compare"]["category"] == "price"
