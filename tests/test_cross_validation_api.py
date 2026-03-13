"""
Tests for the cross-validation API service.

Verifies indicator comparison logic using static fixture data.
"""

import sys
import os

import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.services.cross_validation_service import (
    run_cross_validation,
    _calculate_our_rsi,
    _calculate_our_macd,
    _calculate_our_bb,
    _safe_float,
)
from api.schemas.cross_validation import CrossValidationResponse


# --- Fixtures ---

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "cross_validation", "fixtures")


@pytest.fixture(scope="module")
def aapl_data() -> pd.DataFrame:
    """Load AAPL static CSV fixture."""
    path = os.path.join(FIXTURES_DIR, "AAPL.csv")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df


@pytest.fixture(scope="module")
def synthetic_data() -> pd.DataFrame:
    """Generate synthetic OHLCV data."""
    np.random.seed(42)
    n = 300
    dates = pd.bdate_range(start="2024-01-01", periods=n)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    close = pd.Series(close, index=dates).clip(lower=1)
    df = pd.DataFrame({
        "Close": close,
        "Open": close * (1 + np.random.randn(n) * 0.005),
        "High": close * (1 + abs(np.random.randn(n) * 0.01)),
        "Low": close * (1 - abs(np.random.randn(n) * 0.01)),
        "Volume": np.random.randint(100000, 1000000, size=n),
    }, index=dates)
    return df


# --- Tests: helper functions ---

class TestHelpers:
    def test_safe_float_none(self):
        assert _safe_float(None) is None

    def test_safe_float_nan(self):
        assert _safe_float(float("nan")) is None

    def test_safe_float_valid(self):
        assert _safe_float(42.5) == 42.5

    def test_safe_float_string(self):
        assert _safe_float("bad") is None


class TestOurIndicators:
    def test_rsi_returns_float(self, synthetic_data):
        rsi = _calculate_our_rsi(synthetic_data["Close"])
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_macd_returns_tuple(self, synthetic_data):
        macd, signal, hist = _calculate_our_macd(synthetic_data["Close"])
        assert macd is not None
        assert signal is not None
        assert hist is not None

    def test_bb_returns_tuple(self, synthetic_data):
        upper, middle, lower, width = _calculate_our_bb(synthetic_data["Close"])
        assert upper is not None
        assert middle is not None
        assert lower is not None
        assert width is not None
        assert upper > middle > lower

    def test_rsi_insufficient_data(self):
        close = pd.Series([100.0] * 10)
        rsi = _calculate_our_rsi(close)
        # With only 10 data points and period=14, RSI will be NaN
        assert rsi is None


# --- Tests: cross-validation service ---

class TestCrossValidationService:
    def test_run_with_static_data(self, aapl_data):
        """Cross-validation should run with pre-loaded data."""
        result = run_cross_validation(ticker="AAPL", period="1y", data=aapl_data)
        assert isinstance(result, CrossValidationResponse)
        assert result.ticker == "AAPL"
        assert result.data_points > 0
        assert len(result.comparisons) == 8  # RSI, MACD*3, BB*4
        assert len(result.known_divergences) == 3

    def test_comparison_fields(self, aapl_data):
        """Each comparison should have required fields."""
        result = run_cross_validation(ticker="AAPL", data=aapl_data)
        for comp in result.comparisons:
            assert comp.name is not None
            assert isinstance(comp.match, bool)

    def test_macd_matches_closely(self, aapl_data):
        """MACD should match very closely (same algorithm)."""
        result = run_cross_validation(ticker="AAPL", data=aapl_data)
        macd_comps = [c for c in result.comparisons if "MACD" in c.name]
        assert len(macd_comps) == 3
        for c in macd_comps:
            assert c.match, f"{c.name} should match: our={c.our_value}, ref={c.reference_value}"

    def test_rsi_diverges_within_tolerance(self, aapl_data):
        """RSI should match within tolerance despite method difference."""
        result = run_cross_validation(ticker="AAPL", data=aapl_data)
        rsi_comp = next(c for c in result.comparisons if "RSI" in c.name)
        assert rsi_comp.match, f"RSI should match within tolerance: diff={rsi_comp.difference}"

    def test_synthetic_data_works(self, synthetic_data):
        """Cross-validation should work with synthetic data."""
        result = run_cross_validation(ticker="SYNTHETIC", data=synthetic_data)
        assert result.data_points == 300
        assert len(result.comparisons) == 8

    def test_insufficient_data_raises(self):
        """Should raise ValueError for too few data points."""
        short_df = pd.DataFrame({
            "Close": [100.0] * 30,
        })
        with pytest.raises(ValueError, match="Insufficient data"):
            run_cross_validation(ticker="TEST", data=short_df)

    def test_overall_pass_flag(self, aapl_data):
        """Overall pass should reflect individual matches."""
        result = run_cross_validation(ticker="AAPL", data=aapl_data)
        expected = all(c.match for c in result.comparisons)
        assert result.overall_pass == expected
