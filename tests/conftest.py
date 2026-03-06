"""
Shared pytest configuration and fixtures for the tests/ directory.
"""

from __future__ import annotations

from pathlib import Path


def pytest_addoption(parser):
    """Register custom CLI options."""
    parser.addoption(
        "--regen-golden",
        action="store_true",
        default=False,
        help="Regenerate golden snapshot files instead of comparing against them.",
    )


def pytest_collection_modifyitems(config, items):
    """When --regen-golden is passed, regenerate the golden snapshot and skip tests."""
    if not config.getoption("--regen-golden", default=False):
        return

    # Lazy import to avoid loading heavy modules when not regenerating
    from tests.test_condition_golden import _generate_snapshot, _write_snapshot

    import pytest

    snapshot = _generate_snapshot()
    _write_snapshot(snapshot)

    count = len(snapshot["conditions"])
    skip_marker = pytest.mark.skip(
        reason=f"Regenerated golden snapshot with {count} conditions"
    )

    golden_module = Path(__file__).resolve().parent / "test_condition_golden.py"
    for item in items:
        item_path = Path(item.fspath).resolve() if hasattr(item, "fspath") else None
        if item_path == golden_module:
            item.add_marker(skip_marker)
