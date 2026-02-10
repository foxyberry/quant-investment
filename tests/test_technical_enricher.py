"""
Tests for TechnicalEnricher module

Tests the data_enrichment.technical module that calculates
technical indicators and their signal interpretations.
"""

import pytest
import pandas as pd
import numpy as np

from data_enrichment import (
    TechnicalEnricher,
    TechnicalEnricherConfig,
    enrich_technical,
    RSISignal,
    MACDCross,
    BBPosition,
    OBVTrend,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    close = 100 + np.cumsum(np.random.randn(100) * 2)
    high = close + np.abs(np.random.randn(100))
    low = close - np.abs(np.random.randn(100))
    open_price = close + np.random.randn(100) * 0.5
    volume = np.random.randint(1000000, 10000000, 100)

    return pd.DataFrame(
        {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


@pytest.fixture
def uptrend_data():
    """Create data with clear uptrend for testing."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    close = np.linspace(100, 150, 50)  # Steady uptrend
    high = close + 1
    low = close - 1
    open_price = close - 0.5
    volume = np.ones(50) * 1000000

    return pd.DataFrame(
        {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


@pytest.fixture
def downtrend_data():
    """Create data with clear downtrend for testing."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    close = np.linspace(150, 100, 50)  # Steady downtrend
    high = close + 1
    low = close - 1
    open_price = close + 0.5
    volume = np.ones(50) * 1000000

    return pd.DataFrame(
        {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


@pytest.fixture
def enricher():
    """Create TechnicalEnricher instance."""
    return TechnicalEnricher()


# ============================================================================
# Basic Functionality Tests
# ============================================================================


class TestTechnicalEnricherBasic:
    """Test basic enricher functionality."""

    def test_enrich_returns_dict(self, enricher, sample_ohlcv_data):
        """Enricher should return a dictionary."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        assert isinstance(result, dict)

    def test_enrich_contains_all_required_keys(self, enricher, sample_ohlcv_data):
        """Result should contain all required indicator keys."""
        result = enricher.enrich("TEST", sample_ohlcv_data)

        required_keys = [
            "ticker",
            "rsi",
            "rsi_signal",
            "macd",
            "macd_signal",
            "macd_histogram",
            "macd_cross",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_position",
            "obv",
            "obv_trend",
            "stochastic_k",
            "stochastic_d",
        ]

        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_ticker_preserved(self, enricher, sample_ohlcv_data):
        """Ticker should be preserved in result."""
        result = enricher.enrich("AAPL", sample_ohlcv_data)
        assert result["ticker"] == "AAPL"

    def test_rsi_in_valid_range(self, enricher, sample_ohlcv_data):
        """RSI should be between 0 and 100."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        assert 0 <= result["rsi"] <= 100

    def test_stochastic_in_valid_range(self, enricher, sample_ohlcv_data):
        """Stochastic values should be between 0 and 100."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        assert 0 <= result["stochastic_k"] <= 100
        assert 0 <= result["stochastic_d"] <= 100


# ============================================================================
# RSI Signal Tests
# ============================================================================


class TestRSISignals:
    """Test RSI signal interpretation."""

    def test_rsi_overbought_signal(self, enricher, uptrend_data):
        """Strong uptrend should produce overbought RSI."""
        result = enricher.enrich("TEST", uptrend_data)
        # After strong uptrend, RSI should be high
        assert result["rsi"] > 50

    def test_rsi_oversold_signal(self, enricher, downtrend_data):
        """Strong downtrend should produce oversold RSI."""
        result = enricher.enrich("TEST", downtrend_data)
        # After strong downtrend, RSI should be low
        assert result["rsi"] < 50

    def test_rsi_signal_values(self, enricher, sample_ohlcv_data):
        """RSI signal should be one of the valid values."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        valid_signals = [
            RSISignal.OVERSOLD.value,
            RSISignal.NEUTRAL.value,
            RSISignal.OVERBOUGHT.value,
        ]
        assert result["rsi_signal"] in valid_signals


# ============================================================================
# MACD Cross Tests
# ============================================================================


class TestMACDCross:
    """Test MACD crossover detection."""

    def test_macd_cross_values(self, enricher, sample_ohlcv_data):
        """MACD cross should be one of the valid values."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        valid_crosses = [
            MACDCross.BULLISH.value,
            MACDCross.BEARISH.value,
            MACDCross.NONE.value,
        ]
        assert result["macd_cross"] in valid_crosses

    def test_macd_histogram_calculation(self, enricher, sample_ohlcv_data):
        """MACD histogram should equal MACD minus signal."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        expected = result["macd"] - result["macd_signal"]
        assert abs(result["macd_histogram"] - expected) < 0.01


# ============================================================================
# Bollinger Bands Tests
# ============================================================================


class TestBollingerBands:
    """Test Bollinger Bands calculations."""

    def test_bb_order(self, enricher, sample_ohlcv_data):
        """Upper BB should be above middle, middle above lower."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        assert result["bb_upper"] >= result["bb_middle"]
        assert result["bb_middle"] >= result["bb_lower"]

    def test_bb_position_values(self, enricher, sample_ohlcv_data):
        """BB position should be one of the valid values."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        valid_positions = [
            BBPosition.ABOVE.value,
            BBPosition.MIDDLE.value,
            BBPosition.BELOW.value,
        ]
        assert result["bb_position"] in valid_positions


# ============================================================================
# OBV Tests
# ============================================================================


class TestOBV:
    """Test OBV calculations."""

    def test_obv_trend_values(self, enricher, sample_ohlcv_data):
        """OBV trend should be one of the valid values."""
        result = enricher.enrich("TEST", sample_ohlcv_data)
        valid_trends = [
            OBVTrend.RISING.value,
            OBVTrend.FALLING.value,
            OBVTrend.FLAT.value,
        ]
        assert result["obv_trend"] in valid_trends

    def test_obv_uptrend_rising(self, enricher, uptrend_data):
        """Uptrend should produce rising OBV."""
        result = enricher.enrich("TEST", uptrend_data)
        assert result["obv_trend"] == OBVTrend.RISING.value

    def test_obv_downtrend_falling(self, enricher, downtrend_data):
        """Downtrend should produce falling OBV."""
        result = enricher.enrich("TEST", downtrend_data)
        assert result["obv_trend"] == OBVTrend.FALLING.value


# ============================================================================
# Configuration Tests
# ============================================================================


class TestConfiguration:
    """Test custom configuration."""

    def test_custom_rsi_period(self, sample_ohlcv_data):
        """Custom RSI period should work."""
        config = TechnicalEnricherConfig(rsi_period=21)
        enricher = TechnicalEnricher(config)
        result = enricher.enrich("TEST", sample_ohlcv_data)
        assert result["rsi"] is not None

    def test_custom_rsi_thresholds(self, sample_ohlcv_data):
        """Custom RSI thresholds should affect signals."""
        # Very narrow thresholds
        config = TechnicalEnricherConfig(rsi_oversold=45, rsi_overbought=55)
        enricher = TechnicalEnricher(config)
        result = enricher.enrich("TEST", sample_ohlcv_data)
        # With narrow thresholds, more likely to be oversold/overbought
        assert result["rsi_signal"] in ["oversold", "neutral", "overbought"]


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_column_raises(self, enricher):
        """Missing required column should raise ValueError."""
        incomplete_data = pd.DataFrame(
            {"open": [1, 2, 3], "high": [2, 3, 4], "low": [0.5, 1.5, 2.5]}
        )
        with pytest.raises(ValueError, match="Missing required columns"):
            enricher.enrich("TEST", incomplete_data)

    def test_short_data_returns_values(self, enricher):
        """Short data should still return values (possibly None for some)."""
        short_data = pd.DataFrame(
            {
                "open": [100, 101],
                "high": [102, 103],
                "low": [99, 100],
                "close": [101, 102],
                "volume": [1000000, 1100000],
            }
        )
        result = enricher.enrich("TEST", short_data)
        assert result["ticker"] == "TEST"


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunction:
    """Test the enrich_technical convenience function."""

    def test_enrich_technical_works(self, sample_ohlcv_data):
        """Convenience function should work like enricher."""
        result = enrich_technical("TEST", sample_ohlcv_data)
        assert isinstance(result, dict)
        assert "rsi" in result
        assert "macd" in result
