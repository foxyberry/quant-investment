import numpy as np
import pandas as pd

from screener.conditions.registry import get_condition_metadata
from screener.conditions.time_price import (
    OvernightReturnFilterCondition,
    DistanceFrom52WLowCondition,
    DistanceFrom200DHighCondition,
    GapUpBreakawayCondition,
    GapDownExhaustionCondition,
    OpeningRangeBreakoutCondition,
    PivotPointBreakoutCondition,
    MonthOfYearSeasonalityCondition,
    TurnOfMonthEffectCondition,
    DayOfWeekSeasonalityCondition,
)


def _df(n: int = 400) -> pd.DataFrame:
    idx = pd.bdate_range("2023-01-02", periods=n)
    close = pd.Series(np.linspace(100, 140, n), index=idx)
    open_ = close * 0.997
    high = close * 1.01
    low = close * 0.99
    volume = pd.Series(np.linspace(1_000_000, 2_000_000, n), index=idx)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def test_time_price_keys_registered():
    metadata = get_condition_metadata()
    expected = {
        "overnight_return_filter",
        "distance_from_52w_low",
        "distance_from_200d_high",
        "gap_up_breakaway",
        "gap_down_exhaustion",
        "opening_range_breakout",
        "pivot_point_breakout",
        "month_of_year_seasonality",
        "turn_of_month_effect",
        "day_of_week_seasonality",
    }
    assert expected.issubset(set(metadata.keys()))


def test_time_price_conditions_evaluate():
    data = _df()
    assert "overnight_return_pct" in OvernightReturnFilterCondition(-100).evaluate("T", data).details
    assert "distance_pct" in DistanceFrom52WLowCondition(max_distance_pct=1000).evaluate("T", data).details
    assert "distance_pct" in DistanceFrom200DHighCondition(max_distance_pct=1000).evaluate("T", data).details
    assert "gap_pct" in GapUpBreakawayCondition(min_gap_pct=-100).evaluate("T", data).details
    assert "gap_down_pct" in GapDownExhaustionCondition(min_gap_down_pct=-100).evaluate("T", data).details
    assert "prev_high" in OpeningRangeBreakoutCondition("up").evaluate("T", data).details
    assert "pivot" in PivotPointBreakoutCondition("up").evaluate("T", data).details
    assert "avg_return_pct" in MonthOfYearSeasonalityCondition(target_month=1, min_avg_return_pct=-100).evaluate("T", data).details
    assert "avg_return_pct" in TurnOfMonthEffectCondition(window_days=3, min_avg_return_pct=-100).evaluate("T", data).details
    assert "avg_return_pct" in DayOfWeekSeasonalityCondition(target_weekday=0, min_avg_return_pct=-100).evaluate("T", data).details


def test_insufficient_data_failsafe():
    short = _df(3)
    result = MonthOfYearSeasonalityCondition().evaluate("T", short)
    assert result.matched is False
    assert result.details.get("error") == "Insufficient data"
