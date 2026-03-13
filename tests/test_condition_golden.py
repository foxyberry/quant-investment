"""
L5: Golden snapshot regression tests.

Captures evaluate() output for all registered conditions on fixed synthetic data.
If any condition changes output, the test fails -- forcing explicit review.

To regenerate: python -m pytest tests/test_condition_golden.py --regen-golden
"""

from __future__ import annotations

import json
import math
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from screener.conditions.registry import get_condition_class_map, get_condition_metadata
from tests.fixtures.synthetic_data import build_fixture

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "golden"
_GOLDEN_FILE = _GOLDEN_DIR / "conditions_snapshot.v1.json"

# ---------------------------------------------------------------------------
# Deterministic data params (must match what is stored in the snapshot)
# ---------------------------------------------------------------------------

_SEED = 42
_SHAPE = "random_walk"
_DAYS = 200
_PROFILE = "fundamental"

# ---------------------------------------------------------------------------
# Condition helpers (mirrors test_condition_contract.py)
# ---------------------------------------------------------------------------

_metadata = get_condition_metadata()
_class_map = get_condition_class_map()
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


def _build_deterministic_data():
    """Build the same DataFrame used for snapshot generation."""
    return build_fixture(shape=_SHAPE, days=_DAYS, profile=_PROFILE, seed=_SEED)


# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------

class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that converts numpy types to native Python types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            value = float(obj)
            if math.isnan(value) or math.isinf(value):
                return None
            return value
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _sanitize_value(v: Any) -> Any:
    """Convert a single value to a JSON-safe Python native type."""
    if v is None:
        return None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return None
        return fv
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(v, np.ndarray):
        return [_sanitize_value(x) for x in v.tolist()]
    if isinstance(v, (list, tuple)):
        return [_sanitize_value(x) for x in v]
    if isinstance(v, dict):
        return {str(dk): _sanitize_value(dv) for dk, dv in v.items()}
    # bool, int, str pass through
    return v


def _sanitize_details(details: dict) -> dict:
    """Recursively sanitize all values in a details dict."""
    return {str(k): _sanitize_value(v) for k, v in details.items()}


# ---------------------------------------------------------------------------
# Snapshot generation
# ---------------------------------------------------------------------------

def _generate_snapshot() -> dict:
    """Run all conditions on deterministic data and build the snapshot dict."""
    data = _build_deterministic_data()
    conditions_output: dict[str, dict] = {}

    for key in _SINGLE_CONDITION_KEYS:
        cond = _instantiate(key)
        result = cond.evaluate("TEST", data)
        matched = bool(result.matched)
        details = _sanitize_details(result.details)
        conditions_output[key] = {
            "matched": matched,
            "details": details,
        }

    return {
        "version": 1,
        "seed": _SEED,
        "shape": _SHAPE,
        "days": _DAYS,
        "profile": _PROFILE,
        "conditions": conditions_output,
    }


def _write_snapshot(snapshot: dict) -> None:
    """Write snapshot to the golden file with pretty-printing."""
    _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    _GOLDEN_FILE.write_text(
        json.dumps(snapshot, indent=2, cls=_NumpyEncoder, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_snapshot() -> dict:
    """Load the golden snapshot from disk."""
    return json.loads(_GOLDEN_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Value comparison
# ---------------------------------------------------------------------------

_FLOAT_TOLERANCE = 1e-9


def _values_match(actual: Any, expected: Any) -> bool:
    """Compare two sanitized values, using tolerance for floats."""
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False
    if isinstance(actual, float) and isinstance(expected, float):
        return abs(actual - expected) < _FLOAT_TOLERANCE
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(_values_match(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return False
        return all(_values_match(a, e) for a, e in zip(actual, expected))
    return actual == expected


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGoldenSnapshot:
    """L5: Golden snapshot regression tests."""

    def test_snapshot_file_exists(self):
        """The golden snapshot file must exist on disk."""
        assert _GOLDEN_FILE.exists(), (
            f"Golden snapshot not found at {_GOLDEN_FILE}. "
            f"Run: python -m pytest tests/test_condition_golden.py --regen-golden"
        )

    def test_all_conditions_present(self):
        """Snapshot keys must exactly match current registered conditions."""
        if not _GOLDEN_FILE.exists():
            pytest.skip("Golden file does not exist yet; run --regen-golden first")
        snapshot = _load_snapshot()
        snapshot_keys = set(snapshot["conditions"].keys())
        current_keys = set(_SINGLE_CONDITION_KEYS)
        missing = current_keys - snapshot_keys
        extra = snapshot_keys - current_keys
        assert not missing, (
            f"{len(missing)} condition(s) missing from golden snapshot: "
            f"{sorted(missing)}. Run --regen-golden to update."
        )
        assert not extra, (
            f"{len(extra)} stale condition(s) in golden snapshot: "
            f"{sorted(extra)}. Run --regen-golden to update."
        )

    @pytest.mark.parametrize("key", _SINGLE_CONDITION_KEYS, ids=lambda k: k)
    def test_condition_output_matches_golden(self, key: str):
        """Each condition's output must match the golden snapshot exactly."""
        if not _GOLDEN_FILE.exists():
            pytest.skip("Golden file does not exist yet; run --regen-golden first")

        snapshot = _load_snapshot()

        if key not in snapshot["conditions"]:
            pytest.fail(
                f"Condition '{key}' not found in golden snapshot. "
                f"Run --regen-golden to update."
            )

        expected = snapshot["conditions"][key]

        # Re-evaluate the condition on the same deterministic data
        data = _build_deterministic_data()
        cond = _instantiate(key)
        result = cond.evaluate("TEST", data)
        actual_matched = bool(result.matched)
        actual_details = _sanitize_details(result.details)

        # Compare matched
        assert actual_matched == expected["matched"], (
            f"[{key}] matched mismatch: got {actual_matched}, "
            f"expected {expected['matched']}"
        )

        # Compare details
        expected_details = expected["details"]

        # Check keys
        actual_keys = set(actual_details.keys())
        expected_keys = set(expected_details.keys())
        if actual_keys != expected_keys:
            added = actual_keys - expected_keys
            removed = expected_keys - actual_keys
            parts = [f"[{key}] detail keys mismatch."]
            if added:
                parts.append(f"  Added: {sorted(added)}")
            if removed:
                parts.append(f"  Removed: {sorted(removed)}")
            parts.append("Run --regen-golden to update.")
            pytest.fail("\n".join(parts))

        # Compare each value
        mismatches = []
        for dk in sorted(expected_details.keys()):
            if not _values_match(actual_details[dk], expected_details[dk]):
                mismatches.append(
                    f"  {dk}: got {actual_details[dk]!r}, expected {expected_details[dk]!r}"
                )
        if mismatches:
            pytest.fail(
                f"[{key}] detail value mismatches:\n"
                + "\n".join(mismatches)
                + "\nRun --regen-golden to update."
            )
