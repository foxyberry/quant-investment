import pandas as pd

from screener.conditions.basic_catalog import (
    PriceLagCompareCondition,
    ReturnRangeCondition,
    VolumeLagCompareCondition,
    VolumeMARatioCondition,
)
from screener.conditions.registry import get_condition_class_map, get_condition_metadata


def _expected_parametric_keys() -> list[str]:
    """Return the four parametric keys registered via @register_condition."""
    return [
        "price_lag_compare",
        "volume_lag_compare",
        "volume_ma_ratio",
        "return_pct_range",
    ]


def _expected_legacy_alias_keys() -> list[str]:
    """Return the 14 legacy alias keys kept for backward compatibility."""
    keys: list[str] = []
    for short_period in [2, 3, 5, 10]:
        for long_period in [20, 60]:
            keys.append(f"volume_ma_ratio_{short_period}_{long_period}")
    for lookback_days in [1, 2, 3, 5, 10, 20]:
        keys.append(f"return_pct_{lookback_days}d_minmax")
    return keys


def _sample_df(length: int = 120) -> pd.DataFrame:
    idx = range(length)
    close = [100 + i * 0.5 for i in idx]
    return pd.DataFrame(
        {
            "open": [v - 0.3 for v in close],
            "high": [v + 1.0 for v in close],
            "low": [v - 1.0 for v in close],
            "close": close,
            "volume": [100000 + (i * 300) for i in idx],
        }
    )


def test_basic_catalog_keys_registered():
    metadata = get_condition_metadata()
    expected = _expected_parametric_keys()

    missing = [k for k in expected if k not in metadata]
    assert not missing, f"Missing catalog condition metadata keys: {missing}"


def test_legacy_alias_keys_in_class_map():
    """Legacy alias keys must be in class_map as callables (but NOT in metadata)."""
    class_map = get_condition_class_map()
    metadata = get_condition_metadata()

    for key in _expected_legacy_alias_keys():
        assert key in class_map, f"Legacy alias missing from class_map: {key}"
        assert callable(class_map[key]), f"Legacy alias must be callable: {key}"
        assert key not in metadata, f"Legacy alias should not appear in metadata: {key}"


def test_price_lag_compare_registered_metadata():
    metadata = get_condition_metadata()
    assert "price_lag_compare" in metadata
    meta = metadata["price_lag_compare"]
    assert meta["category"] == "price"
    assert meta["recommended"] is True
    param_names = [p["name"] for p in meta["params"]]
    assert "field" in param_names
    assert "lag_a" in param_names
    assert "lag_b" in param_names
    assert "operator" in param_names


def test_volume_lag_compare_registered_metadata():
    metadata = get_condition_metadata()
    assert "volume_lag_compare" in metadata
    meta = metadata["volume_lag_compare"]
    assert meta["category"] == "volume"
    assert meta["recommended"] is True
    param_names = [p["name"] for p in meta["params"]]
    assert "lag_a" in param_names
    assert "lag_b" in param_names
    assert "operator" in param_names


def test_volume_ma_ratio_registered_metadata():
    metadata = get_condition_metadata()
    assert "volume_ma_ratio" in metadata
    meta = metadata["volume_ma_ratio"]
    assert meta["category"] == "volume"
    assert meta["recommended"] is True
    param_names = [p["name"] for p in meta["params"]]
    assert "short_period" in param_names
    assert "long_period" in param_names
    assert "min_ratio" in param_names
    assert "max_ratio" in param_names


def test_return_pct_range_registered_metadata():
    metadata = get_condition_metadata()
    assert "return_pct_range" in metadata
    meta = metadata["return_pct_range"]
    assert meta["category"] == "price"
    assert meta["recommended"] is True
    param_names = [p["name"] for p in meta["params"]]
    assert "lookback_days" in param_names
    assert "min_return_pct" in param_names
    assert "max_return_pct" in param_names


def test_price_lag_compare_default_instantiation():
    cond = PriceLagCompareCondition()
    assert cond.field == "close"
    assert cond.lag_a == 1
    assert cond.lag_b == 3
    assert cond.operator == "lt"
    assert cond.name == "price_lag_compare_close_1_lt_3"
    assert cond.required_days == 5


def test_volume_lag_compare_default_instantiation():
    cond = VolumeLagCompareCondition()
    assert cond.lag_a == 1
    assert cond.lag_b == 2
    assert cond.operator == "gt"
    assert cond.name == "volume_lag_compare_1_gt_2"
    assert cond.required_days == 4


def test_volume_ma_ratio_default_instantiation():
    cond = VolumeMARatioCondition()
    assert cond.short_period == 5
    assert cond.long_period == 20
    assert cond.min_ratio == 0.8
    assert cond.max_ratio == 3.0
    assert cond.name == "volume_ma_ratio_5_20"
    assert cond.required_days == 25


def test_volume_ma_ratio_custom_params():
    cond = VolumeMARatioCondition(short_period=2, long_period=60, min_ratio=1.0, max_ratio=2.5)
    assert cond.short_period == 2
    assert cond.long_period == 60
    assert cond.name == "volume_ma_ratio_2_60"


def test_return_range_default_instantiation():
    cond = ReturnRangeCondition()
    assert cond.lookback_days == 5
    assert cond.min_return_pct == -5.0
    assert cond.max_return_pct == 5.0
    assert cond.name == "return_pct_5d_minmax"
    assert cond.required_days == 7


def test_return_range_custom_params():
    cond = ReturnRangeCondition(lookback_days=20, min_return_pct=-10.0, max_return_pct=10.0)
    assert cond.lookback_days == 20
    assert cond.name == "return_pct_20d_minmax"


def test_price_lag_compare_invalid_params_fallback():
    cond = PriceLagCompareCondition(field="invalid", lag_a=-5, operator="bad")
    assert cond.field == "close"
    assert cond.lag_a == 1
    assert cond.operator == "lt"


def test_volume_lag_compare_invalid_operator_fallback():
    cond = VolumeLagCompareCondition(operator="invalid")
    assert cond.operator == "gt"


def test_price_lag_compare_lt_on_increasing_series():
    # On increasing series, t-1 > t-3 so "lt" should be False
    df = _sample_df(40)
    cond = PriceLagCompareCondition(field="close", lag_a=1, lag_b=3, operator="lt")
    result = cond.evaluate("TEST", df)
    assert result.matched is False


def test_price_lag_compare_gt_on_increasing_series():
    # On increasing series, t-1 > t-3 so "gt" should be True
    df = _sample_df(40)
    cond = PriceLagCompareCondition(field="close", lag_a=1, lag_b=3, operator="gt")
    result = cond.evaluate("TEST", df)
    assert result.matched is True
    assert result.details["field"] == "close"
    assert result.details["lag_a"] == 1
    assert result.details["lag_b"] == 3
    assert result.details["operator"] == "gt"


def test_price_lag_compare_lt_on_decreasing_series():
    dec = list(reversed([100 + i * 0.5 for i in range(40)]))
    df = pd.DataFrame(
        {
            "open": [v - 0.3 for v in dec],
            "high": [v + 1.0 for v in dec],
            "low": [v - 1.0 for v in dec],
            "close": dec,
            "volume": [100000 + (i * 300) for i in range(40)],
        }
    )
    cond = PriceLagCompareCondition(field="close", lag_a=1, lag_b=3, operator="lt")
    result = cond.evaluate("TEST", df)
    assert result.matched is True


def test_price_lag_compare_insufficient_data():
    df = pd.DataFrame({"close": [100, 101]})
    cond = PriceLagCompareCondition(field="close", lag_a=1, lag_b=3, operator="lt")
    result = cond.evaluate("TEST", df)
    assert result.matched is False
    assert "error" in result.details


def test_price_lag_compare_missing_column():
    df = pd.DataFrame({"close": [100] * 10})
    cond = PriceLagCompareCondition(field="high", lag_a=1, lag_b=2, operator="gt")
    result = cond.evaluate("TEST", df)
    assert result.matched is False
    assert "Missing" in result.details["error"]


def test_volume_lag_compare_gt_on_increasing_volume():
    # Volume increases over time -> t-1 > t-2 -> "gt" should be True
    df = _sample_df(40)
    cond = VolumeLagCompareCondition(lag_a=1, lag_b=2, operator="gt")
    result = cond.evaluate("TEST", df)
    assert result.matched is True
    assert result.details["lag_a"] == 1
    assert result.details["lag_b"] == 2
    assert result.details["operator"] == "gt"


def test_volume_lag_compare_lt_on_increasing_volume():
    # Volume increases -> t-1 > t-2 -> "lt" should be False
    df = _sample_df(40)
    cond = VolumeLagCompareCondition(lag_a=1, lag_b=2, operator="lt")
    result = cond.evaluate("TEST", df)
    assert result.matched is False


def test_volume_lag_compare_insufficient_data():
    df = pd.DataFrame({"volume": [100000]})
    cond = VolumeLagCompareCondition(lag_a=1, lag_b=2, operator="gt")
    result = cond.evaluate("TEST", df)
    assert result.matched is False
    assert "error" in result.details


def test_volume_lag_compare_missing_column():
    df = pd.DataFrame({"close": [100] * 10})
    cond = VolumeLagCompareCondition(lag_a=1, lag_b=2, operator="gt")
    result = cond.evaluate("TEST", df)
    assert result.matched is False
    assert "Missing" in result.details["error"]


def test_parametric_conditions_via_class_map():
    """Verify that the parametric classes are accessible via the registry."""
    class_map = get_condition_class_map()

    assert "price_lag_compare" in class_map
    assert class_map["price_lag_compare"] is PriceLagCompareCondition

    assert "volume_lag_compare" in class_map
    assert class_map["volume_lag_compare"] is VolumeLagCompareCondition

    assert "volume_ma_ratio" in class_map
    assert class_map["volume_ma_ratio"] is VolumeMARatioCondition

    assert "return_pct_range" in class_map
    assert class_map["return_pct_range"] is ReturnRangeCondition


def test_volume_ma_ratio_evaluate():
    """Test VolumeMARatioCondition evaluation with controlled data."""
    vol = [100000] * 70 + [150000] * 10
    df = pd.DataFrame(
        {
            "open": [100.0] * 80,
            "high": [101.0] * 80,
            "low": [99.0] * 80,
            "close": [100.0] * 80,
            "volume": vol,
        }
    )
    cond = VolumeMARatioCondition(short_period=2, long_period=20, min_ratio=1.1, max_ratio=2.0)
    result = cond.evaluate("TEST", df)
    assert result.matched is True
    assert result.details["short_period"] == 2
    assert result.details["long_period"] == 20


def test_volume_ma_ratio_legacy_alias():
    """Legacy alias volume_ma_ratio_2_20 should resolve to VolumeMARatioCondition with correct defaults."""
    class_map = get_condition_class_map()
    alias = class_map["volume_ma_ratio_2_20"]

    # Instantiate without explicit params — should use partial defaults (sp=2, lp=20)
    cond = alias()
    assert isinstance(cond, VolumeMARatioCondition)
    assert cond.short_period == 2
    assert cond.long_period == 20

    vol = [100000] * 70 + [150000] * 10
    df = pd.DataFrame(
        {
            "open": [100.0] * 80,
            "high": [101.0] * 80,
            "low": [99.0] * 80,
            "close": [100.0] * 80,
            "volume": vol,
        }
    )
    cond = alias(min_ratio=1.1, max_ratio=2.0)
    assert cond.evaluate("TEST", df).matched is True


def test_return_range_evaluate():
    """Test ReturnRangeCondition evaluation."""
    df = _sample_df(40)
    cond = ReturnRangeCondition(lookback_days=5, min_return_pct=-10.0, max_return_pct=10.0)
    result = cond.evaluate("TEST", df)
    assert isinstance(result.matched, bool)
    assert result.details["lookback_days"] == 5


def test_return_range_legacy_alias():
    """Legacy alias return_pct_5d_minmax should resolve to ReturnRangeCondition with correct defaults."""
    class_map = get_condition_class_map()
    alias = class_map["return_pct_5d_minmax"]

    # Instantiate without explicit params — should use partial default (lookback_days=5)
    cond = alias()
    assert isinstance(cond, ReturnRangeCondition)
    assert cond.lookback_days == 5

    df = _sample_df(40)
    cond = alias(min_return_pct=-10.0, max_return_pct=10.0)
    result = cond.evaluate("TEST", df)
    assert isinstance(result.matched, bool)
