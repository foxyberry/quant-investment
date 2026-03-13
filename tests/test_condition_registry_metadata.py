"""
Tests for Condition Registry Metadata (Issue #112)

Verifies that:
1. Recommended conditions have correct default param values in registry metadata.
2. All conditions include 'recommended' and 'order' fields in metadata.
3. The API service function get_available_conditions() exposes the new fields.
"""

import pytest

# Import condition modules so they register themselves via @register_condition
import screener.conditions.ma  # noqa: F401
import screener.conditions.rsi  # noqa: F401
import screener.conditions.volume  # noqa: F401
import screener.conditions.accumulation  # noqa: F401

from screener.conditions.registry import get_condition_metadata
from api.services.strategy_service import get_available_conditions


# Expected data for the 10 recommended conditions.
# Each tuple: (key, param_name, expected_default, order)
# For 'above_ma' there is no param default override to check,
# so we only verify recommended=True and order.
RECOMMENDED_DEFAULTS = [
    ("ma_touch", "period", 120, 10),
    ("ma_cross_up", "short_period", 5, 20),
    ("ma_cross_up", "long_period", 20, 20),
    ("rsi_oversold", "threshold", 35, 40),
    ("rsi_range", "lower", 50, 50),
    ("volume_spike", "multiplier", 1.5, 60),
    ("volume_above_avg", "multiplier", 1.0, 70),
    ("bollinger_width", "max_width_pct", 15.0, 80),
    ("volume_below_avg", "multiplier", 1.0, 90),
    ("price_flat", "max_range_pct", 10.0, 100),
]

RECOMMENDED_KEYS = [
    "price_lag_compare",
    "ma_touch",
    "volume_ma_ratio",
    "volume_lag_compare",
    "return_pct_range",
    "ma_cross_up",
    "above_ma",
    "rsi_oversold",
    "rsi_range",
    "avg_trading_value",
    "drawdown_from_high",
    "volume_spike",
    "volume_above_avg",
    "bollinger_width",
    "volume_below_avg",
    "price_flat",
]

RECOMMENDED_ORDERS = {
    "price_lag_compare": 10,
    "ma_touch": 10,
    "volume_ma_ratio": 12,
    "volume_lag_compare": 11,
    "return_pct_range": 13,
    "ma_cross_up": 20,
    "above_ma": 30,
    "rsi_oversold": 40,
    "rsi_range": 50,
    "avg_trading_value": 65,
    "drawdown_from_high": 50,
    "volume_spike": 60,
    "volume_above_avg": 70,
    "bollinger_width": 80,
    "volume_below_avg": 90,
    "price_flat": 100,
}


class TestRecommendedConditionsDefaults:
    """Test that the 10 recommended conditions have correct param defaults
    from the registry metadata (not the class __init__ defaults)."""

    def test_recommended_conditions_defaults(self):
        metadata = get_condition_metadata()

        for key, param_name, expected_default, expected_order in RECOMMENDED_DEFAULTS:
            assert key in metadata, f"Condition '{key}' not found in registry metadata"

            meta = metadata[key]

            # Verify recommended flag
            assert meta["recommended"] is True, (
                f"Condition '{key}' should be recommended=True"
            )

            # Verify order
            assert meta["order"] == expected_order, (
                f"Condition '{key}' order: expected {expected_order}, got {meta['order']}"
            )

            # Find the param by name and check its default
            param_found = False
            for param in meta["params"]:
                if param["name"] == param_name:
                    param_found = True
                    assert param["default"] == expected_default, (
                        f"Condition '{key}' param '{param_name}': "
                        f"expected default={expected_default}, got {param['default']}"
                    )
                    break

            assert param_found, (
                f"Condition '{key}' missing param '{param_name}' in metadata"
            )

        # Also verify 'above_ma' is recommended with correct order,
        # even though we have no specific param default override to check
        assert "above_ma" in metadata
        assert metadata["above_ma"]["recommended"] is True
        assert metadata["above_ma"]["order"] == 30


class TestMetadataHasRecommendedAndOrder:
    """Verify that 'recommended' and 'order' keys exist in the metadata dict
    for ALL registered conditions, not just recommended ones."""

    def test_metadata_has_recommended_and_order(self):
        metadata = get_condition_metadata()

        assert len(metadata) > 0, "Registry metadata is empty; condition modules not loaded"

        for key, meta in metadata.items():
            assert "recommended" in meta, (
                f"Condition '{key}' metadata missing 'recommended' field"
            )
            assert "order" in meta, (
                f"Condition '{key}' metadata missing 'order' field"
            )
            assert isinstance(meta["recommended"], bool), (
                f"Condition '{key}' 'recommended' should be bool, got {type(meta['recommended'])}"
            )
            assert isinstance(meta["order"], int), (
                f"Condition '{key}' 'order' should be int, got {type(meta['order'])}"
            )

        # Verify that exactly the expected keys are marked as recommended
        recommended_keys_actual = sorted(
            k for k, m in metadata.items() if m["recommended"]
        )
        recommended_keys_expected = sorted(RECOMMENDED_KEYS)
        assert recommended_keys_actual == recommended_keys_expected, (
            f"Recommended keys mismatch.\n"
            f"  Expected: {recommended_keys_expected}\n"
            f"  Actual:   {recommended_keys_actual}"
        )


class TestGetAvailableConditionsIncludesNewFields:
    """The API service function get_available_conditions() should include
    'recommended' and 'order' in each ConditionInfo output."""

    def test_get_available_conditions_includes_new_fields(self):
        conditions = get_available_conditions()

        assert len(conditions) > 0, "get_available_conditions() returned empty list"

        for cond in conditions:
            # ConditionInfo should have recommended and order attributes
            assert hasattr(cond, "recommended"), (
                f"ConditionInfo '{cond.key}' missing 'recommended' attribute"
            )
            assert hasattr(cond, "order"), (
                f"ConditionInfo '{cond.key}' missing 'order' attribute"
            )
            assert isinstance(cond.recommended, bool), (
                f"ConditionInfo '{cond.key}' recommended should be bool"
            )
            assert isinstance(cond.order, int), (
                f"ConditionInfo '{cond.key}' order should be int"
            )

        # Build a lookup for quick assertions
        cond_map = {c.key: c for c in conditions}

        # Verify recommended conditions are correct in the API output
        for key in RECOMMENDED_KEYS:
            assert key in cond_map, (
                f"Recommended condition '{key}' not in get_available_conditions() output"
            )
            assert cond_map[key].recommended is True, (
                f"ConditionInfo '{key}' should have recommended=True"
            )
            assert cond_map[key].order == RECOMMENDED_ORDERS[key], (
                f"ConditionInfo '{key}' order: "
                f"expected {RECOMMENDED_ORDERS[key]}, got {cond_map[key].order}"
            )

        # Verify non-recommended conditions have recommended=False
        for cond in conditions:
            if cond.key not in RECOMMENDED_KEYS:
                assert cond.recommended is False, (
                    f"ConditionInfo '{cond.key}' should have recommended=False"
                )
