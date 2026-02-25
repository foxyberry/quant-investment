"""Basic condition catalog for common lag/ratio/range filters.

This module registers a large set of beginner-friendly primitive conditions
used in many rule-based screeners.
"""

from __future__ import annotations

from itertools import combinations

import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


LAGS = [1, 2, 3, 5, 10, 20, 60]
PRICE_FIELDS = [
    ("close", "Close"),
    ("open", "Open"),
    ("high", "High"),
    ("low", "Low"),
]


def _register_price_lag_compare(field: str, left_lag: int, right_lag: int, operator: str) -> None:
    op_symbol = "<" if operator == "lt" else ">"
    key = f"{field}_lag_{left_lag}_{operator}_{right_lag}"

    # Keep the dedicated implementation from price.py for this key.
    if key == "close_lag_1_lt_3":
        return

    class _PriceLagCompareCondition(BaseCondition):
        def __init__(self, left_lag: int = left_lag, right_lag: int = right_lag, operator: str = operator):
            self.left_lag = max(1, int(left_lag))
            self.right_lag = max(1, int(right_lag))
            self.operator = operator if operator in {"lt", "gt"} else "lt"

        @property
        def name(self) -> str:
            return f"{field}_lag_compare_{self.left_lag}_{self.operator}_{self.right_lag}"

        @property
        def required_days(self) -> int:
            return max(self.left_lag, self.right_lag) + 2

        def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
            if field not in data.columns:
                return ConditionResult(False, self.name, {"error": f"Missing {field} column"})
            if len(data) < self.required_days:
                return ConditionResult(False, self.name, {"error": "Insufficient data"})

            left_value = data[field].iloc[-(self.left_lag + 1)]
            right_value = data[field].iloc[-(self.right_lag + 1)]
            if pd.isna(left_value) or pd.isna(right_value):
                return ConditionResult(False, self.name, {"error": f"NaN in {field} data"})

            if self.operator == "lt":
                matched = bool(left_value < right_value)
            else:
                matched = bool(left_value > right_value)

            return ConditionResult(
                matched=matched,
                condition_name=self.name,
                details={
                    "field": field,
                    "left_lag": self.left_lag,
                    "right_lag": self.right_lag,
                    "operator": self.operator,
                    "left_value": float(left_value),
                    "right_value": float(right_value),
                },
            )

    _PriceLagCompareCondition.__name__ = f"{field.title()}Lag{left_lag}{operator.upper()}{right_lag}Condition"
    register_condition(
        key=key,
        label=f"{field.title()} t-{left_lag} {op_symbol} t-{right_lag}",
        description=f"{field.title()} at t-{left_lag} {op_symbol} t-{right_lag}",
        category="price",
        params=[
            {"name": "left_lag", "type": "int", "default": left_lag, "description": "Left lag day"},
            {"name": "right_lag", "type": "int", "default": right_lag, "description": "Right lag day"},
            {"name": "operator", "type": "str", "default": operator, "description": "Comparison operator"},
        ],
    )(_PriceLagCompareCondition)


def _register_volume_lag_compare(left_lag: int, right_lag: int) -> None:
    key = f"volume_lag_{left_lag}_gt_{right_lag}"

    class _VolumeLagCompareCondition(BaseCondition):
        def __init__(self, left_lag: int = left_lag, right_lag: int = right_lag, operator: str = "gt"):
            self.left_lag = max(1, int(left_lag))
            self.right_lag = max(1, int(right_lag))
            self.operator = "gt"

        @property
        def name(self) -> str:
            return f"volume_lag_compare_{self.left_lag}_gt_{self.right_lag}"

        @property
        def required_days(self) -> int:
            return max(self.left_lag, self.right_lag) + 2

        def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
            if "volume" not in data.columns:
                return ConditionResult(False, self.name, {"error": "Missing volume column"})
            if len(data) < self.required_days:
                return ConditionResult(False, self.name, {"error": "Insufficient data"})

            left_value = data["volume"].iloc[-(self.left_lag + 1)]
            right_value = data["volume"].iloc[-(self.right_lag + 1)]
            if pd.isna(left_value) or pd.isna(right_value):
                return ConditionResult(False, self.name, {"error": "NaN in volume data"})

            matched = bool(left_value > right_value)
            return ConditionResult(
                matched=matched,
                condition_name=self.name,
                details={
                    "left_lag": self.left_lag,
                    "right_lag": self.right_lag,
                    "operator": self.operator,
                    "left_value": float(left_value),
                    "right_value": float(right_value),
                },
            )

    _VolumeLagCompareCondition.__name__ = f"VolumeLag{left_lag}GT{right_lag}Condition"
    register_condition(
        key=key,
        label=f"Volume t-{left_lag} > t-{right_lag}",
        description=f"Volume at t-{left_lag} is greater than volume at t-{right_lag}",
        category="volume",
        params=[
            {"name": "left_lag", "type": "int", "default": left_lag, "description": "Left lag day"},
            {"name": "right_lag", "type": "int", "default": right_lag, "description": "Right lag day"},
            {"name": "operator", "type": "str", "default": "gt", "description": "Comparison operator"},
        ],
    )(_VolumeLagCompareCondition)


def _register_volume_ma_ratio(short_period: int, long_period: int) -> None:
    key = f"volume_ma_ratio_{short_period}_{long_period}"

    class _VolumeMARatioCondition(BaseCondition):
        def __init__(
            self,
            short_period: int = short_period,
            long_period: int = long_period,
            min_ratio: float = 0.8,
            max_ratio: float = 3.0,
        ):
            self.short_period = max(1, int(short_period))
            self.long_period = max(self.short_period + 1, int(long_period))
            self.min_ratio = float(min_ratio)
            self.max_ratio = float(max_ratio)

        @property
        def name(self) -> str:
            return f"volume_ma_ratio_{self.short_period}_{self.long_period}"

        @property
        def required_days(self) -> int:
            return self.long_period + 5

        def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
            if "volume" not in data.columns:
                return ConditionResult(False, self.name, {"error": "Missing volume column"})
            if len(data) < self.required_days:
                return ConditionResult(False, self.name, {"error": "Insufficient data"})

            short_avg = data["volume"].tail(self.short_period).mean()
            long_avg = data["volume"].tail(self.long_period).mean()
            if pd.isna(short_avg) or pd.isna(long_avg) or long_avg <= 0:
                return ConditionResult(False, self.name, {"error": "Invalid moving average data"})

            ratio = float(short_avg / long_avg)
            matched = self.min_ratio <= ratio <= self.max_ratio
            return ConditionResult(
                matched=bool(matched),
                condition_name=self.name,
                details={
                    "short_period": self.short_period,
                    "long_period": self.long_period,
                    "short_avg": float(short_avg),
                    "long_avg": float(long_avg),
                    "ratio": ratio,
                    "min_ratio": self.min_ratio,
                    "max_ratio": self.max_ratio,
                },
            )

    _VolumeMARatioCondition.__name__ = f"VolumeMARatio{short_period}{long_period}Condition"
    register_condition(
        key=key,
        label=f"Volume MA Ratio {short_period}/{long_period}",
        description=f"Volume short MA({short_period}) / long MA({long_period}) ratio range filter",
        category="volume",
        params=[
            {"name": "short_period", "type": "int", "default": short_period, "description": "Short MA period"},
            {"name": "long_period", "type": "int", "default": long_period, "description": "Long MA period"},
            {"name": "min_ratio", "type": "float", "default": 0.8, "description": "Minimum ratio"},
            {"name": "max_ratio", "type": "float", "default": 3.0, "description": "Maximum ratio"},
        ],
    )(_VolumeMARatioCondition)


def _register_return_range(lookback_days: int) -> None:
    key = f"return_pct_{lookback_days}d_minmax"

    class _ReturnRangeCondition(BaseCondition):
        def __init__(
            self,
            lookback_days: int = lookback_days,
            min_return_pct: float = -5.0,
            max_return_pct: float = 5.0,
        ):
            self.lookback_days = max(1, int(lookback_days))
            self.min_return_pct = float(min_return_pct)
            self.max_return_pct = float(max_return_pct)

        @property
        def name(self) -> str:
            return f"return_pct_{self.lookback_days}d_minmax"

        @property
        def required_days(self) -> int:
            return self.lookback_days + 2

        def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
            if "close" not in data.columns:
                return ConditionResult(False, self.name, {"error": "Missing close column"})
            if len(data) < self.required_days:
                return ConditionResult(False, self.name, {"error": "Insufficient data"})

            current = data["close"].iloc[-1]
            past = data["close"].iloc[-(self.lookback_days + 1)]
            if pd.isna(current) or pd.isna(past) or past <= 0:
                return ConditionResult(False, self.name, {"error": "Invalid close data"})

            return_pct = float(((current - past) / past) * 100.0)
            matched = self.min_return_pct <= return_pct <= self.max_return_pct
            return ConditionResult(
                matched=bool(matched),
                condition_name=self.name,
                details={
                    "lookback_days": self.lookback_days,
                    "return_pct": return_pct,
                    "min_return_pct": self.min_return_pct,
                    "max_return_pct": self.max_return_pct,
                },
            )

    _ReturnRangeCondition.__name__ = f"ReturnPct{lookback_days}DRangeCondition"
    register_condition(
        key=key,
        label=f"{lookback_days}D Return % Range",
        description=f"{lookback_days}-day return percentage range filter",
        category="price",
        params=[
            {"name": "lookback_days", "type": "int", "default": lookback_days, "description": "Lookback days"},
            {"name": "min_return_pct", "type": "float", "default": -5.0, "description": "Minimum return %"},
            {"name": "max_return_pct", "type": "float", "default": 5.0, "description": "Maximum return %"},
        ],
    )(_ReturnRangeCondition)


for field, _ in PRICE_FIELDS:
    for left_lag, right_lag in combinations(LAGS, 2):
        _register_price_lag_compare(field, left_lag, right_lag, "gt")
        _register_price_lag_compare(field, left_lag, right_lag, "lt")

for left_lag, right_lag in combinations(LAGS, 2):
    _register_volume_lag_compare(left_lag, right_lag)

for short_period in [2, 3, 5, 10]:
    for long_period in [20, 60]:
        _register_volume_ma_ratio(short_period, long_period)

for lookback_days in [1, 2, 3, 5, 10, 20]:
    _register_return_range(lookback_days)
