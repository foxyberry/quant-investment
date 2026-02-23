"""
Time/Price Pattern Conditions
시계열/가격 패턴 기반 조건
"""

from __future__ import annotations

import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


def _insufficient(name: str) -> ConditionResult:
    return ConditionResult(matched=False, condition_name=name, details={"error": "Insufficient data"})


@register_condition(
    key="overnight_return_filter",
    label="Overnight Return",
    description="Previous close to current open return filter",
    category="time",
    params=[
        {"name": "min_overnight_return_pct", "type": "float", "default": 0.0, "description": "Minimum overnight return %"},
    ],
)
class OvernightReturnFilterCondition(BaseCondition):
    def __init__(self, min_overnight_return_pct: float = 0.0):
        self.min_overnight_return_pct = min_overnight_return_pct

    @property
    def name(self) -> str:
        return "overnight_return_filter"

    @property
    def required_days(self) -> int:
        return 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 2 or "open" not in data.columns:
            return _insufficient(self.name)
        prev_close = data["close"].iloc[-2]
        curr_open = data["open"].iloc[-1]
        if prev_close == 0 or pd.isna(prev_close) or pd.isna(curr_open):
            return _insufficient(self.name)
        overnight_pct = float(((curr_open - prev_close) / prev_close) * 100.0)
        return ConditionResult(
            matched=overnight_pct >= self.min_overnight_return_pct,
            condition_name=self.name,
            details={"overnight_return_pct": overnight_pct},
        )


@register_condition(
    key="distance_from_52w_low",
    label="Distance From 52W Low",
    description="Distance from 252-day low",
    category="price",
    params=[
        {"name": "lookback_days", "type": "int", "default": 252, "description": "Lookback days"},
        {"name": "max_distance_pct", "type": "float", "default": 30.0, "description": "Maximum distance %"},
    ],
)
class DistanceFrom52WLowCondition(BaseCondition):
    def __init__(self, lookback_days: int = 252, max_distance_pct: float = 30.0):
        self.lookback_days = lookback_days
        self.max_distance_pct = max_distance_pct

    @property
    def name(self) -> str:
        return "distance_from_52w_low"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        close = data["close"].iloc[-1]
        low = data["low"].tail(self.lookback_days).min()
        if low == 0 or pd.isna(close) or pd.isna(low):
            return _insufficient(self.name)
        distance_pct = float(((close - low) / low) * 100.0)
        return ConditionResult(
            matched=distance_pct <= self.max_distance_pct,
            condition_name=self.name,
            details={"distance_pct": distance_pct},
        )


@register_condition(
    key="distance_from_200d_high",
    label="Distance From 200D High",
    description="Distance below 200-day high",
    category="price",
    params=[
        {"name": "lookback_days", "type": "int", "default": 200, "description": "Lookback days"},
        {"name": "max_distance_pct", "type": "float", "default": 15.0, "description": "Maximum distance %"},
    ],
)
class DistanceFrom200DHighCondition(BaseCondition):
    def __init__(self, lookback_days: int = 200, max_distance_pct: float = 15.0):
        self.lookback_days = lookback_days
        self.max_distance_pct = max_distance_pct

    @property
    def name(self) -> str:
        return "distance_from_200d_high"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        close = data["close"].iloc[-1]
        high = data["high"].tail(self.lookback_days).max()
        if high == 0 or pd.isna(close) or pd.isna(high):
            return _insufficient(self.name)
        distance_pct = float(((high - close) / high) * 100.0)
        return ConditionResult(
            matched=distance_pct <= self.max_distance_pct,
            condition_name=self.name,
            details={"distance_pct": distance_pct},
        )


@register_condition(
    key="gap_up_breakaway",
    label="Gap Up Breakaway",
    description="Gap-up breakout using previous high",
    category="price",
    params=[
        {"name": "min_gap_pct", "type": "float", "default": 1.0, "description": "Minimum gap %"},
    ],
)
class GapUpBreakawayCondition(BaseCondition):
    def __init__(self, min_gap_pct: float = 1.0):
        self.min_gap_pct = min_gap_pct

    @property
    def name(self) -> str:
        return "gap_up_breakaway"

    @property
    def required_days(self) -> int:
        return 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 2 or "open" not in data.columns:
            return _insufficient(self.name)
        prev_high = data["high"].iloc[-2]
        curr_open = data["open"].iloc[-1]
        if prev_high == 0 or pd.isna(prev_high) or pd.isna(curr_open):
            return _insufficient(self.name)
        gap_pct = float(((curr_open - prev_high) / prev_high) * 100.0)
        return ConditionResult(matched=gap_pct >= self.min_gap_pct, condition_name=self.name, details={"gap_pct": gap_pct})


@register_condition(
    key="gap_down_exhaustion",
    label="Gap Down Exhaustion",
    description="Large down-gap exhaustion signal",
    category="price",
    params=[
        {"name": "min_gap_down_pct", "type": "float", "default": 2.0, "description": "Minimum down gap %"},
    ],
)
class GapDownExhaustionCondition(BaseCondition):
    def __init__(self, min_gap_down_pct: float = 2.0):
        self.min_gap_down_pct = min_gap_down_pct

    @property
    def name(self) -> str:
        return "gap_down_exhaustion"

    @property
    def required_days(self) -> int:
        return 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 2 or "open" not in data.columns:
            return _insufficient(self.name)
        prev_low = data["low"].iloc[-2]
        curr_open = data["open"].iloc[-1]
        curr_close = data["close"].iloc[-1]
        if prev_low == 0 or pd.isna(prev_low) or pd.isna(curr_open) or pd.isna(curr_close):
            return _insufficient(self.name)
        gap_down_pct = float(((prev_low - curr_open) / prev_low) * 100.0)
        rebound = curr_close >= curr_open
        return ConditionResult(
            matched=(gap_down_pct >= self.min_gap_down_pct and rebound),
            condition_name=self.name,
            details={"gap_down_pct": gap_down_pct, "rebound": rebound},
        )


@register_condition(
    key="opening_range_breakout",
    label="Opening Range Breakout",
    description="Close breaks previous day range",
    category="price",
    params=[
        {"name": "direction", "type": "str", "default": "up", "description": "up|down"},
    ],
)
class OpeningRangeBreakoutCondition(BaseCondition):
    def __init__(self, direction: str = "up"):
        self.direction = direction

    @property
    def name(self) -> str:
        return f"opening_range_breakout_{self.direction}"

    @property
    def required_days(self) -> int:
        return 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 2:
            return _insufficient(self.name)
        prev_high = data["high"].iloc[-2]
        prev_low = data["low"].iloc[-2]
        curr_close = data["close"].iloc[-1]
        if self.direction == "down":
            matched = curr_close < prev_low
        else:
            matched = curr_close > prev_high
        return ConditionResult(matched=bool(matched), condition_name=self.name, details={"prev_high": float(prev_high), "prev_low": float(prev_low)})


@register_condition(
    key="pivot_point_breakout",
    label="Pivot Point Breakout",
    description="Breakout above/below classic pivot",
    category="price",
    params=[
        {"name": "direction", "type": "str", "default": "up", "description": "up|down"},
    ],
)
class PivotPointBreakoutCondition(BaseCondition):
    def __init__(self, direction: str = "up"):
        self.direction = direction

    @property
    def name(self) -> str:
        return f"pivot_point_breakout_{self.direction}"

    @property
    def required_days(self) -> int:
        return 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 2:
            return _insufficient(self.name)
        prev_high = data["high"].iloc[-2]
        prev_low = data["low"].iloc[-2]
        prev_close = data["close"].iloc[-2]
        pivot = (prev_high + prev_low + prev_close) / 3.0
        curr_close = data["close"].iloc[-1]
        matched = curr_close > pivot if self.direction == "up" else curr_close < pivot
        return ConditionResult(matched=bool(matched), condition_name=self.name, details={"pivot": float(pivot), "close": float(curr_close)})


@register_condition(
    key="month_of_year_seasonality",
    label="Month Of Year Seasonality",
    description="Average return for target month",
    category="time",
    params=[
        {"name": "target_month", "type": "int", "default": 1, "description": "Target month (1-12)"},
        {"name": "min_avg_return_pct", "type": "float", "default": 0.0, "description": "Minimum average return %"},
    ],
)
class MonthOfYearSeasonalityCondition(BaseCondition):
    def __init__(self, target_month: int = 1, min_avg_return_pct: float = 0.0):
        self.target_month = target_month
        self.min_avg_return_pct = min_avg_return_pct

    @property
    def name(self) -> str:
        return "month_of_year_seasonality"

    @property
    def required_days(self) -> int:
        return 260

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days or not isinstance(data.index, pd.DatetimeIndex):
            return _insufficient(self.name)
        monthly_close = data["close"].resample("M").last()
        monthly_ret = monthly_close.pct_change().dropna()
        month_ret = monthly_ret[monthly_ret.index.month == self.target_month]
        if len(month_ret) == 0:
            return _insufficient(self.name)
        avg_pct = float(month_ret.mean() * 100.0)
        return ConditionResult(matched=avg_pct >= self.min_avg_return_pct, condition_name=self.name, details={"avg_return_pct": avg_pct})


@register_condition(
    key="turn_of_month_effect",
    label="Turn Of Month",
    description="Turn-of-month return effect",
    category="time",
    params=[
        {"name": "window_days", "type": "int", "default": 3, "description": "Days around month change"},
        {"name": "min_avg_return_pct", "type": "float", "default": 0.0, "description": "Minimum average return %"},
    ],
)
class TurnOfMonthEffectCondition(BaseCondition):
    def __init__(self, window_days: int = 3, min_avg_return_pct: float = 0.0):
        self.window_days = window_days
        self.min_avg_return_pct = min_avg_return_pct

    @property
    def name(self) -> str:
        return "turn_of_month_effect"

    @property
    def required_days(self) -> int:
        return 120

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days or not isinstance(data.index, pd.DatetimeIndex):
            return _insufficient(self.name)
        daily_ret = data["close"].pct_change().dropna()
        idx = daily_ret.index
        mask = (idx.day <= self.window_days) | (idx.day >= (idx.days_in_month - self.window_days + 1))
        sample = daily_ret[mask]
        if len(sample) == 0:
            return _insufficient(self.name)
        avg_pct = float(sample.mean() * 100.0)
        return ConditionResult(matched=avg_pct >= self.min_avg_return_pct, condition_name=self.name, details={"avg_return_pct": avg_pct})


@register_condition(
    key="day_of_week_seasonality",
    label="Day Of Week",
    description="Average weekday return effect",
    category="time",
    params=[
        {"name": "target_weekday", "type": "int", "default": 0, "description": "Weekday (0=Mon)"},
        {"name": "min_avg_return_pct", "type": "float", "default": 0.0, "description": "Minimum average return %"},
    ],
)
class DayOfWeekSeasonalityCondition(BaseCondition):
    def __init__(self, target_weekday: int = 0, min_avg_return_pct: float = 0.0):
        self.target_weekday = target_weekday
        self.min_avg_return_pct = min_avg_return_pct

    @property
    def name(self) -> str:
        return "day_of_week_seasonality"

    @property
    def required_days(self) -> int:
        return 60

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days or not isinstance(data.index, pd.DatetimeIndex):
            return _insufficient(self.name)
        daily_ret = data["close"].pct_change().dropna()
        sample = daily_ret[daily_ret.index.weekday == self.target_weekday]
        if len(sample) == 0:
            return _insufficient(self.name)
        avg_pct = float(sample.mean() * 100.0)
        return ConditionResult(matched=avg_pct >= self.min_avg_return_pct, condition_name=self.name, details={"avg_return_pct": avg_pct})
