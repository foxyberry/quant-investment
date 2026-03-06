import numpy as np
import pandas as pd

from screener.conditions.quant_indicators import (
    VWAPCrossSignalCondition,
    VWAPDistancePctCondition,
    RelativeVolumePercentileCondition,
    TurnoverRatioMinCondition,
    ATRPercentileFilterCondition,
    ATRExpansionBreakoutCondition,
    NATRFilterCondition,
    DMIDirectionalCrossCondition,
    IchimokuCloudBreakoutCondition,
    IchimokuTenkanKijunCrossCondition,
)
from screener.conditions.registry import get_condition_metadata


def _df(n=320):
    idx = pd.bdate_range("2024-01-02", periods=n)
    close = pd.Series(np.r_[np.linspace(100, 90, n // 3), np.linspace(91, 150, n - n // 3)], index=idx)
    open_ = close * 0.998
    high = close * 1.01
    low = close * 0.99
    volume = pd.Series(np.linspace(1_000_000, 2_200_000, n), index=idx)
    shares = pd.Series(np.full(n, 100_000_000.0), index=idx)
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "shares_outstanding": shares,
    }, index=idx)


def test_quant_indicator_keys_registered():
    keys = set(get_condition_metadata().keys())
    expected = {
        "vwap_cross_signal",
        "vwap_distance_pct",
        "relative_volume_percentile",
        "turnover_ratio_min",
        "atr_percentile_filter",
        "atr_expansion_breakout",
        "natr_filter",
        "dmi_directional_cross",
        "ichimoku_cloud_breakout",
        "ichimoku_tenkan_kijun_cross",
    }
    assert expected.issubset(keys)


def test_quant_indicator_conditions_compute():
    data = _df()
    assert "cross_day" in VWAPCrossSignalCondition().evaluate("T", data).details
    assert "distance_pct" in VWAPDistancePctCondition(max_distance_pct=100).evaluate("T", data).details
    assert "percentile" in RelativeVolumePercentileCondition(min_percentile=0).evaluate("T", data).details
    assert "turnover_ratio" in TurnoverRatioMinCondition(min_turnover_ratio=0).evaluate("T", data).details
    assert "percentile" in ATRPercentileFilterCondition(max_percentile=100).evaluate("T", data).details
    assert "atr_expanded" in ATRExpansionBreakoutCondition(atr_multiplier=0).evaluate("T", data).details
    assert "natr_pct" in NATRFilterCondition(max_natr_pct=100).evaluate("T", data).details
    assert "cross_day" in DMIDirectionalCrossCondition(lookback_days=20).evaluate("T", data).details
    assert "cloud_top" in IchimokuCloudBreakoutCondition().evaluate("T", data).details
    assert "cross_day" in IchimokuTenkanKijunCrossCondition(lookback_days=20).evaluate("T", data).details


def test_turnover_ratio_missing_shares_yfinance_fallback():
    """When shares_outstanding is absent from DataFrame, yfinance info API
    is used as fallback."""
    from unittest.mock import patch
    data = _df().drop(columns=["shares_outstanding"])
    with patch("screener.conditions.fundamental._get_info", return_value={"sharesOutstanding": 1_000_000_000}):
        result = TurnoverRatioMinCondition(min_turnover_ratio=0).evaluate("AAPL", data)
    assert "turnover_ratio" in result.details
    assert result.matched is True


def test_turnover_ratio_missing_shares_failsafe():
    """When shares_outstanding is absent and yfinance also fails,
    should return matched=False with error."""
    from unittest.mock import patch
    data = _df().drop(columns=["shares_outstanding"])
    with patch("screener.conditions.fundamental._get_info", return_value={}):
        result = TurnoverRatioMinCondition().evaluate("FAKE_TICKER_XYZ", data)
    assert result.matched is False
    assert "error" in result.details
