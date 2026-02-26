"""Tests for legacy alias resolution of old lag condition keys."""

import pytest

from screener.conditions.basic_catalog import PriceLagCompareCondition, VolumeLagCompareCondition


def test_price_lag_alias_resolves():
    """Old key 'close_lag_1_gt_3' should resolve to PriceLagCompareCondition."""
    from api.services.strategy_service import _build_condition

    cond = _build_condition("close_lag_1_gt_3", {})
    assert isinstance(cond, PriceLagCompareCondition)
    assert cond.field == "close"
    assert cond.lag_a == 1
    assert cond.lag_b == 3
    assert cond.operator == "gt"


def test_volume_lag_alias_resolves():
    """Old key 'volume_lag_1_gt_3' should resolve to VolumeLagCompareCondition."""
    from api.services.strategy_service import _build_condition

    cond = _build_condition("volume_lag_1_gt_3", {})
    assert isinstance(cond, VolumeLagCompareCondition)
    assert cond.lag_a == 1
    assert cond.lag_b == 3
    assert cond.operator == "gt"


def test_unknown_key_raises():
    """Unknown keys should still raise ValueError."""
    from api.services.strategy_service import _build_condition

    with pytest.raises(ValueError, match="Unknown condition type"):
        _build_condition("nonexistent_condition_key", {})


def test_user_param_overrides_alias_defaults():
    """User-supplied params should override the alias defaults."""
    from api.services.strategy_service import _build_condition

    # Legacy key defaults to field=open, lag_a=1, lag_b=2, operator=gt
    # but user overrides operator to "lt"
    cond = _build_condition("open_lag_1_gt_2", {"operator": "lt"})
    assert isinstance(cond, PriceLagCompareCondition)
    assert cond.field == "open"
    assert cond.lag_a == 1
    assert cond.lag_b == 2
    assert cond.operator == "lt"  # user override


def test_canonical_key_still_works():
    """The new canonical key 'price_lag_compare' should work directly."""
    from api.services.strategy_service import _build_condition

    cond = _build_condition("price_lag_compare", {"field": "high", "lag_a": 5, "lag_b": 10, "operator": "gt"})
    assert isinstance(cond, PriceLagCompareCondition)
    assert cond.field == "high"
    assert cond.lag_a == 5
    assert cond.lag_b == 10


def test_all_price_lag_aliases_exist():
    """Verify all 168 price lag aliases are present."""
    from itertools import combinations
    from api.services.strategy_service import _LEGACY_ALIAS_MAP

    lags = [1, 2, 3, 5, 10, 20, 60]
    for field in ["close", "open", "high", "low"]:
        for left, right in combinations(lags, 2):
            for op in ("gt", "lt"):
                key = f"{field}_lag_{left}_{op}_{right}"
                assert key in _LEGACY_ALIAS_MAP, f"Missing alias: {key}"


def test_legacy_param_names_remapped():
    """Old saved strategies use 'left_lag'/'right_lag' param names.
    These should be remapped to 'lag_a'/'lag_b' automatically."""
    from api.services.strategy_service import _build_condition

    # Simulate a saved strategy with old param names
    cond = _build_condition("close_lag_1_gt_3", {"left_lag": 2, "right_lag": 5})
    assert isinstance(cond, PriceLagCompareCondition)
    assert cond.lag_a == 2  # remapped from left_lag
    assert cond.lag_b == 5  # remapped from right_lag
    assert cond.field == "close"
    assert cond.operator == "gt"


def test_legacy_param_names_volume():
    """Volume lag conditions with old param names should also work."""
    from api.services.strategy_service import _build_condition

    cond = _build_condition("volume_lag_1_gt_2", {"left_lag": 3, "right_lag": 10})
    assert isinstance(cond, VolumeLagCompareCondition)
    assert cond.lag_a == 3  # remapped from left_lag
    assert cond.lag_b == 10  # remapped from right_lag


def test_all_volume_lag_aliases_exist():
    """Verify all 21 volume lag aliases are present."""
    from itertools import combinations
    from api.services.strategy_service import _LEGACY_ALIAS_MAP

    lags = [1, 2, 3, 5, 10, 20, 60]
    for left, right in combinations(lags, 2):
        key = f"volume_lag_{left}_gt_{right}"
        assert key in _LEGACY_ALIAS_MAP, f"Missing alias: {key}"
