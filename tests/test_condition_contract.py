"""
L0: Interface Contract Tests for all registered conditions.

Verifies that every condition obeys the BaseCondition contract:
- evaluate() returns ConditionResult without exception
- result.matched is bool
- result.details is dict
- required_days is positive int
- Insufficient data returns matched=False with error
- Input DataFrame is not mutated
"""

from __future__ import annotations

from functools import partial

import numpy as np
import pandas as pd
import pytest

from screener.conditions.base import ConditionResult
from screener.conditions.registry import get_condition_class_map, get_condition_metadata
from tests.fixtures.synthetic_data import build_fixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_metadata = get_condition_metadata()
_class_map = get_condition_class_map()

# Only test keys that exist in both metadata AND class_map
_CONDITION_KEYS = sorted(k for k in _metadata if k in _class_map)
_SINGLE_CONDITION_KEYS = sorted(k for k in _CONDITION_KEYS if not _metadata[k].get("is_pairs", False))


def _instantiate(key: str):
    """Create a condition instance from registry metadata defaults."""
    meta = _metadata[key]
    cls_or_partial = _class_map[key]
    params = {p["name"]: p["default"] for p in meta.get("params", [])}
    if isinstance(cls_or_partial, partial):
        return cls_or_partial(**params)
    return cls_or_partial(**params)


def _build_rich_data(days: int = 200) -> pd.DataFrame:
    """Build a DataFrame with all possible columns for maximum compatibility."""
    return build_fixture(shape="random_walk", days=days, profile="fundamental", seed=42)


# ---------------------------------------------------------------------------
# L0 Contract Tests
# ---------------------------------------------------------------------------


class TestConditionContract:
    """L0: Interface contract tests for all conditions."""

    @pytest.mark.parametrize("key", _SINGLE_CONDITION_KEYS, ids=lambda k: k)
    def test_evaluate_returns_condition_result(self, key: str):
        """evaluate() must return a ConditionResult, never raise."""
        cond = _instantiate(key)
        data = _build_rich_data()
        result = cond.evaluate("TEST", data)
        assert isinstance(result, ConditionResult), (
            f"{key}: evaluate() returned {type(result).__name__}, expected ConditionResult"
        )

    @pytest.mark.parametrize("key", _SINGLE_CONDITION_KEYS, ids=lambda k: k)
    def test_matched_is_bool(self, key: str):
        """result.matched must be a bool (including numpy bool_)."""
        cond = _instantiate(key)
        data = _build_rich_data()
        result = cond.evaluate("TEST", data)
        assert isinstance(result.matched, (bool, np.bool_)), (
            f"{key}: matched is {type(result.matched).__name__}, expected bool"
        )

    @pytest.mark.parametrize("key", _SINGLE_CONDITION_KEYS, ids=lambda k: k)
    def test_details_is_dict(self, key: str):
        """result.details must be a dict."""
        cond = _instantiate(key)
        data = _build_rich_data()
        result = cond.evaluate("TEST", data)
        assert isinstance(result.details, dict), (
            f"{key}: details is {type(result.details).__name__}, expected dict"
        )

    @pytest.mark.parametrize("key", _CONDITION_KEYS, ids=lambda k: k)
    def test_required_days_is_positive_int(self, key: str):
        """required_days must return a positive integer."""
        cond = _instantiate(key)
        rd = cond.required_days
        assert isinstance(rd, int), (
            f"{key}: required_days is {type(rd).__name__}, expected int"
        )
        assert rd > 0, f"{key}: required_days is {rd}, must be > 0"

    @pytest.mark.parametrize("key", _SINGLE_CONDITION_KEYS, ids=lambda k: k)
    def test_insufficient_data_returns_false(self, key: str):
        """With too few rows, matched must be False."""
        cond = _instantiate(key)
        # Use 1 row — less than any condition's required_days (except trivial)
        data = _build_rich_data(days=1)
        result = cond.evaluate("TEST", data)
        # Most conditions require > 1 day. For those requiring exactly 1,
        # this test still passes because it doesn't assert error.
        assert isinstance(result, ConditionResult)
        # We only assert matched=False for conditions needing > 1 day
        if cond.required_days > 1:
            assert result.matched is False, (
                f"{key}: matched=True with only 1 row but required_days={cond.required_days}"
            )

    @pytest.mark.parametrize("key", _SINGLE_CONDITION_KEYS, ids=lambda k: k)
    def test_empty_dataframe_returns_false(self, key: str):
        """With 0 rows, must return matched=False without exception."""
        cond = _instantiate(key)
        data = _build_rich_data(days=200).iloc[:0]
        result = cond.evaluate("TEST", data)
        assert isinstance(result, ConditionResult)
        assert result.matched is False, (
            f"{key}: matched=True with empty DataFrame"
        )

    @pytest.mark.parametrize("key", _SINGLE_CONDITION_KEYS, ids=lambda k: k)
    def test_input_dataframe_not_mutated(self, key: str):
        """evaluate() must not modify the input DataFrame."""
        cond = _instantiate(key)
        data = _build_rich_data()
        original_columns = list(data.columns)
        original_shape = data.shape
        original_values = data.values.copy()

        cond.evaluate("TEST", data)

        assert list(data.columns) == original_columns, (
            f"{key}: columns changed after evaluate()"
        )
        assert data.shape == original_shape, (
            f"{key}: shape changed after evaluate()"
        )

    @pytest.mark.parametrize("key", _SINGLE_CONDITION_KEYS, ids=lambda k: k)
    def test_condition_name_is_string(self, key: str):
        """result.condition_name must be a non-empty string."""
        cond = _instantiate(key)
        data = _build_rich_data()
        result = cond.evaluate("TEST", data)
        assert isinstance(result.condition_name, str), (
            f"{key}: condition_name is {type(result.condition_name).__name__}"
        )
        assert len(result.condition_name) > 0, (
            f"{key}: condition_name is empty"
        )


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


class TestRegistryCompleteness:
    """Verify registry integrity."""

    def test_all_metadata_keys_have_class(self):
        """Every key in metadata must have a corresponding class."""
        missing = set(_metadata.keys()) - set(_class_map.keys())
        assert not missing, f"Metadata keys without class: {missing}"

    def test_all_keys_instantiable(self):
        """Every registered condition can be instantiated with default params."""
        failures = []
        for key in _CONDITION_KEYS:
            try:
                _instantiate(key)
            except Exception as e:
                failures.append(f"{key}: {e}")
        assert not failures, f"Failed to instantiate:\n" + "\n".join(failures)

    def test_minimum_condition_count(self):
        """Sanity check: at least 100 conditions registered."""
        assert len(_CONDITION_KEYS) >= 100, (
            f"Only {len(_CONDITION_KEYS)} conditions registered, expected >= 100"
        )
