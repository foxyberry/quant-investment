"""
Tests for Accumulation Zone Screening Conditions
"""

import pytest
import pandas as pd
import numpy as np

from screener.conditions.accumulation import (
    # Layer 1
    BollingerWidthCondition,
    VolumeBelowAvgCondition,
    PriceFlatCondition,
    OBVTrendCondition,
    StochasticLevelCondition,
    VPCITrendCondition,
    # Layer 2
    OBVDivergenceCondition,
    StochasticDivergenceCondition,
    VPCIDivergenceCondition,
)
from discovery.indicators import (
    calculate_obv,
    calculate_stochastic,
    calculate_vpci,
    calculate_bollinger_width,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing"""
    np.random.seed(42)
    n = 100

    # Create a relatively flat price series
    base_price = 10000
    noise = np.random.randn(n) * 50
    close = pd.Series(base_price + np.cumsum(noise * 0.1))

    high = close + abs(np.random.randn(n) * 30)
    low = close - abs(np.random.randn(n) * 30)
    open_price = close.shift(1).fillna(close.iloc[0])
    volume = pd.Series(np.random.randint(10000, 100000, n))

    return pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })


@pytest.fixture
def flat_price_data():
    """Generate flat price data (sideways movement)"""
    np.random.seed(123)
    n = 50

    # Very flat price
    base_price = 10000
    close = pd.Series([base_price + np.random.randn() * 10 for _ in range(n)])
    high = close + 5
    low = close - 5
    volume = pd.Series([50000] * n)

    return pd.DataFrame({
        'open': close.shift(1).fillna(close.iloc[0]),
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })


@pytest.fixture
def trending_up_data():
    """Generate upward trending price data"""
    np.random.seed(456)
    n = 50

    close = pd.Series([10000 + i * 100 + np.random.randn() * 20 for i in range(n)])
    high = close + 30
    low = close - 30
    volume = pd.Series([100000 + i * 1000 for i in range(n)])  # Increasing volume

    return pd.DataFrame({
        'open': close.shift(1).fillna(close.iloc[0]),
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })


# ============================================================
# Indicator Function Tests
# ============================================================

class TestIndicatorFunctions:
    """Test indicator calculation functions"""

    def test_calculate_obv(self, sample_ohlcv_data):
        """Test OBV calculation"""
        obv = calculate_obv(sample_ohlcv_data['close'], sample_ohlcv_data['volume'])

        assert len(obv) == len(sample_ohlcv_data)
        assert not obv.isna().all()
        assert obv.iloc[0] == sample_ohlcv_data['volume'].iloc[0]

    def test_calculate_stochastic(self, sample_ohlcv_data):
        """Test Stochastic calculation"""
        stoch_k, stoch_d = calculate_stochastic(
            sample_ohlcv_data['high'],
            sample_ohlcv_data['low'],
            sample_ohlcv_data['close'],
        )

        assert len(stoch_k) == len(sample_ohlcv_data)
        assert len(stoch_d) == len(sample_ohlcv_data)

        # Valid values should be between 0 and 100
        valid_k = stoch_k.dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all()

    def test_calculate_vpci(self, sample_ohlcv_data):
        """Test VPCI calculation"""
        vpci = calculate_vpci(
            sample_ohlcv_data['close'],
            sample_ohlcv_data['volume'],
        )

        assert len(vpci) == len(sample_ohlcv_data)
        # After warmup period, should have valid values
        assert not vpci.iloc[-1:].isna().all()

    def test_calculate_bollinger_width(self, sample_ohlcv_data):
        """Test Bollinger Width calculation"""
        bb_width = calculate_bollinger_width(sample_ohlcv_data['close'])

        assert len(bb_width) == len(sample_ohlcv_data)
        # Width should be positive
        valid_width = bb_width.dropna()
        assert (valid_width > 0).all()


# ============================================================
# Layer 1 Condition Tests
# ============================================================

class TestBollingerWidthCondition:
    """Test BollingerWidthCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = BollingerWidthCondition(max_width_pct=10.0)

        assert cond.name == "bb_width_below_10.0pct"
        assert cond.required_days > 0
        assert "10.0" in repr(cond)

    def test_narrow_band_matches(self, flat_price_data):
        """Test that narrow BB width matches"""
        cond = BollingerWidthCondition(max_width_pct=20.0)
        result = cond.evaluate("TEST", flat_price_data)

        assert result.matched
        assert "bb_width_pct" in result.details

    def test_wide_band_fails(self, trending_up_data):
        """Test that wide BB width fails"""
        cond = BollingerWidthCondition(max_width_pct=1.0)  # Very strict
        result = cond.evaluate("TEST", trending_up_data)

        assert not result.matched


class TestVolumeBelowAvgCondition:
    """Test VolumeBelowAvgCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = VolumeBelowAvgCondition(multiplier=0.8)

        assert "0.8" in cond.name
        assert cond.required_days > 0

    def test_low_volume_matches(self):
        """Test that low volume matches"""
        # Create data with declining volume
        np.random.seed(789)
        n = 30
        volume = pd.Series([100000] * 20 + [50000] * 10)  # Low volume at end
        close = pd.Series([10000] * n)

        data = pd.DataFrame({
            'open': close,
            'high': close + 10,
            'low': close - 10,
            'close': close,
            'volume': volume,
        })

        cond = VolumeBelowAvgCondition(multiplier=0.8)
        result = cond.evaluate("TEST", data)

        assert result.matched
        assert result.details["ratio"] < 0.8

    def test_high_volume_fails(self):
        """Test that high volume fails"""
        n = 30
        volume = pd.Series([50000] * 20 + [200000] * 10)  # High volume at end
        close = pd.Series([10000] * n)

        data = pd.DataFrame({
            'open': close,
            'high': close + 10,
            'low': close - 10,
            'close': close,
            'volume': volume,
        })

        cond = VolumeBelowAvgCondition(multiplier=0.8)
        result = cond.evaluate("TEST", data)

        assert not result.matched


class TestPriceFlatCondition:
    """Test PriceFlatCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = PriceFlatCondition(max_range_pct=5.0)

        assert "5.0" in cond.name
        assert cond.required_days > 0

    def test_flat_price_matches(self, flat_price_data):
        """Test that flat price matches"""
        cond = PriceFlatCondition(max_range_pct=5.0)
        result = cond.evaluate("TEST", flat_price_data)

        assert result.matched
        assert result.details["range_pct"] <= 5.0

    def test_volatile_price_fails(self, trending_up_data):
        """Test that volatile price fails"""
        cond = PriceFlatCondition(max_range_pct=5.0)
        result = cond.evaluate("TEST", trending_up_data)

        assert not result.matched


class TestOBVTrendCondition:
    """Test OBVTrendCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = OBVTrendCondition(direction="up")

        assert "up" in cond.name
        assert cond.required_days > 0

    def test_direction_validation(self):
        """Test that invalid direction raises error"""
        with pytest.raises(ValueError):
            OBVTrendCondition(direction="sideways")

    def test_upward_obv_matches(self, trending_up_data):
        """Test that upward OBV matches"""
        cond = OBVTrendCondition(direction="up", lookback=20)
        result = cond.evaluate("TEST", trending_up_data)

        assert result.matched
        assert result.details["obv_change"] > 0


class TestStochasticLevelCondition:
    """Test StochasticLevelCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = StochasticLevelCondition(threshold=20.0, condition="below")

        assert "below" in cond.name
        assert "20" in cond.name

    def test_condition_validation(self):
        """Test that invalid condition raises error"""
        with pytest.raises(ValueError):
            StochasticLevelCondition(condition="invalid")

    def test_oversold_matches(self):
        """Test oversold condition"""
        # Create oversold data (prices at lows)
        n = 30
        high = pd.Series([100] * n)
        low = pd.Series([90] * n)
        close = pd.Series([91] * n)  # Close near low

        data = pd.DataFrame({
            'open': close,
            'high': high,
            'low': low,
            'close': close,
            'volume': pd.Series([10000] * n),
        })

        cond = StochasticLevelCondition(threshold=20.0, condition="below")
        result = cond.evaluate("TEST", data)

        assert result.matched
        assert result.details["stoch_k"] <= 20.0


class TestVPCITrendCondition:
    """Test VPCITrendCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = VPCITrendCondition(direction="up")

        assert "up" in cond.name
        assert cond.required_days > 0

    def test_direction_validation(self):
        """Test that invalid direction raises error"""
        with pytest.raises(ValueError):
            VPCITrendCondition(direction="invalid")


# ============================================================
# Layer 2 Divergence Condition Tests
# ============================================================

class TestOBVDivergenceCondition:
    """Test OBVDivergenceCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = OBVDivergenceCondition()

        assert "divergence" in cond.name
        assert cond.required_days > 0

    def test_insufficient_data(self):
        """Test with insufficient data"""
        cond = OBVDivergenceCondition(period=20)

        small_data = pd.DataFrame({
            'open': [100] * 5,
            'high': [101] * 5,
            'low': [99] * 5,
            'close': [100] * 5,
            'volume': [10000] * 5,
        })

        result = cond.evaluate("TEST", small_data)
        assert not result.matched
        assert "error" in result.details


class TestStochasticDivergenceCondition:
    """Test StochasticDivergenceCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = StochasticDivergenceCondition()

        assert "divergence" in cond.name
        assert cond.required_days > 0

    def test_insufficient_data(self):
        """Test with insufficient data"""
        cond = StochasticDivergenceCondition(lookback=20)

        small_data = pd.DataFrame({
            'open': [100] * 10,
            'high': [101] * 10,
            'low': [99] * 10,
            'close': [100] * 10,
            'volume': [10000] * 10,
        })

        result = cond.evaluate("TEST", small_data)
        assert not result.matched


class TestVPCIDivergenceCondition:
    """Test VPCIDivergenceCondition"""

    def test_basic_properties(self):
        """Test basic condition properties"""
        cond = VPCIDivergenceCondition()

        assert "divergence" in cond.name
        assert cond.required_days > 0


# ============================================================
# Integration Tests
# ============================================================

class TestAccumulationPresets:
    """Test accumulation presets"""

    def test_preset_imports(self):
        """Test that presets can be imported"""
        from screener.presets import (
            accumulation_basic,
            accumulation_obv,
            accumulation_full,
        )

        basic = accumulation_basic()
        assert len(basic) == 4

        obv = accumulation_obv()
        assert len(obv) == 5

        full = accumulation_full()
        assert len(full) == 5  # Last one is OrCondition

    def test_preset_registry(self):
        """Test that presets are in registry"""
        from screener.presets import PRESET_REGISTRY, get_preset

        assert "accumulation_basic" in PRESET_REGISTRY
        assert "accumulation_obv" in PRESET_REGISTRY
        assert "accumulation_full" in PRESET_REGISTRY

        # Test get_preset
        basic = get_preset("accumulation_basic")
        assert len(basic) > 0

    def test_screener_exports(self):
        """Test that conditions are exported from screener"""
        from screener import (
            BollingerWidthCondition,
            VolumeBelowAvgCondition,
            PriceFlatCondition,
            OBVTrendCondition,
            StochasticLevelCondition,
            VPCITrendCondition,
            OBVDivergenceCondition,
            StochasticDivergenceCondition,
            VPCIDivergenceCondition,
        )

        # Just verify imports work
        assert BollingerWidthCondition is not None
        assert OBVDivergenceCondition is not None


# ============================================================
# Edge Case Tests
# ============================================================

class TestEdgeCases:
    """Test edge cases"""

    def test_empty_data(self):
        """Test with empty DataFrame"""
        empty_data = pd.DataFrame({
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': [],
        })

        cond = BollingerWidthCondition()
        result = cond.evaluate("TEST", empty_data)

        assert not result.matched
        assert "error" in result.details

    def test_nan_values(self):
        """Test with NaN values"""
        data = pd.DataFrame({
            'open': [np.nan] * 30,
            'high': [np.nan] * 30,
            'low': [np.nan] * 30,
            'close': [np.nan] * 30,
            'volume': [np.nan] * 30,
        })

        cond = BollingerWidthCondition()
        result = cond.evaluate("TEST", data)

        assert not result.matched

    def test_zero_volume(self):
        """Test with zero volume"""
        data = pd.DataFrame({
            'open': [100] * 30,
            'high': [101] * 30,
            'low': [99] * 30,
            'close': [100] * 30,
            'volume': [0] * 30,
        })

        cond = VolumeBelowAvgCondition()
        result = cond.evaluate("TEST", data)

        assert not result.matched
        assert "error" in result.details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
