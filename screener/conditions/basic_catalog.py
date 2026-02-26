"""Basic condition catalog for common lag/ratio/range filters.

This module registers parametric condition classes and dynamic
ratio/range conditions used in many rule-based screeners.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


# ---------------------------------------------------------------------------
# Parametric lag-compare conditions (replace 189 dynamic registrations)
# ---------------------------------------------------------------------------


@register_condition(
    key="price_lag_compare",
    label="Price Lag Compare",
    description="Compare OHLC price at two different lag points",
    category="price",
    params=[
        {
            "name": "field",
            "type": "str",
            "default": "close",
            "description": "Price field",
            "options": ["close", "open", "high", "low"],
        },
        {"name": "lag_a", "type": "int", "default": 1, "description": "First lag (days ago)"},
        {"name": "lag_b", "type": "int", "default": 3, "description": "Second lag (days ago)"},
        {
            "name": "operator",
            "type": "str",
            "default": "lt",
            "description": "Comparison operator",
            "options": ["gt", "lt"],
        },
    ],
    recommended=True,
    order=10,
)
class PriceLagCompareCondition(BaseCondition):
    """Compare an OHLC price field at two different lag points.

    Parameters
    ----------
    field : str
        One of ``"close"``, ``"open"``, ``"high"``, ``"low"``.
    lag_a : int
        First lag in trading days (must be >= 1).
    lag_b : int
        Second lag in trading days (must be >= 1).
    operator : str
        ``"lt"`` (lag_a value < lag_b value) or ``"gt"``.
    """

    VALID_FIELDS: set[str] = {"close", "open", "high", "low"}
    VALID_OPS: set[str] = {"gt", "lt"}

    def __init__(
        self,
        field: str = "close",
        lag_a: int = 1,
        lag_b: int = 3,
        operator: str = "lt",
    ) -> None:
        self.field: str = field if field in self.VALID_FIELDS else "close"
        self.lag_a: int = max(1, int(lag_a))
        self.lag_b: int = max(1, int(lag_b))
        self.operator: str = operator if operator in self.VALID_OPS else "lt"

    @property
    def name(self) -> str:
        return f"price_lag_compare_{self.field}_{self.lag_a}_{self.operator}_{self.lag_b}"

    @property
    def required_days(self) -> int:
        return max(self.lag_a, self.lag_b) + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        col = self.field
        if col not in data.columns:
            return ConditionResult(False, self.name, {"error": f"Missing {col} column"})
        if len(data) < self.required_days:
            return ConditionResult(False, self.name, {"error": "Insufficient data"})

        left_value = data[col].iloc[-(self.lag_a + 1)]
        right_value = data[col].iloc[-(self.lag_b + 1)]
        if pd.isna(left_value) or pd.isna(right_value):
            return ConditionResult(False, self.name, {"error": f"NaN in {col} data"})

        if self.operator == "lt":
            matched = bool(left_value < right_value)
        else:
            matched = bool(left_value > right_value)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "field": self.field,
                "lag_a": self.lag_a,
                "lag_b": self.lag_b,
                "operator": self.operator,
                "left_value": float(left_value),
                "right_value": float(right_value),
            },
        )


@register_condition(
    key="volume_lag_compare",
    label="Volume Lag Compare",
    description="Compare volume at two different lag points",
    category="volume",
    params=[
        {"name": "lag_a", "type": "int", "default": 1, "description": "First lag (days ago)"},
        {"name": "lag_b", "type": "int", "default": 2, "description": "Second lag (days ago)"},
        {
            "name": "operator",
            "type": "str",
            "default": "gt",
            "description": "Comparison operator",
            "options": ["gt", "lt"],
        },
    ],
    recommended=True,
    order=11,
)
class VolumeLagCompareCondition(BaseCondition):
    """Compare volume at two different lag points.

    Parameters
    ----------
    lag_a : int
        First lag in trading days (must be >= 1).
    lag_b : int
        Second lag in trading days (must be >= 1).
    operator : str
        ``"gt"`` (lag_a value > lag_b value) or ``"lt"``.
    """

    VALID_OPS: set[str] = {"gt", "lt"}

    def __init__(
        self,
        lag_a: int = 1,
        lag_b: int = 2,
        operator: str = "gt",
    ) -> None:
        self.lag_a: int = max(1, int(lag_a))
        self.lag_b: int = max(1, int(lag_b))
        self.operator: str = operator if operator in self.VALID_OPS else "gt"

    @property
    def name(self) -> str:
        return f"volume_lag_compare_{self.lag_a}_{self.operator}_{self.lag_b}"

    @property
    def required_days(self) -> int:
        return max(self.lag_a, self.lag_b) + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if "volume" not in data.columns:
            return ConditionResult(False, self.name, {"error": "Missing volume column"})
        if len(data) < self.required_days:
            return ConditionResult(False, self.name, {"error": "Insufficient data"})

        left_value = data["volume"].iloc[-(self.lag_a + 1)]
        right_value = data["volume"].iloc[-(self.lag_b + 1)]
        if pd.isna(left_value) or pd.isna(right_value):
            return ConditionResult(False, self.name, {"error": "NaN in volume data"})

        if self.operator == "lt":
            matched = bool(left_value < right_value)
        else:
            matched = bool(left_value > right_value)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "lag_a": self.lag_a,
                "lag_b": self.lag_b,
                "operator": self.operator,
                "left_value": float(left_value),
                "right_value": float(right_value),
            },
        )


# ---------------------------------------------------------------------------
# Dynamic ratio / range registrations (kept as-is)
# ---------------------------------------------------------------------------


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


for short_period in [2, 3, 5, 10]:
    for long_period in [20, 60]:
        _register_volume_ma_ratio(short_period, long_period)

for lookback_days in [1, 2, 3, 5, 10, 20]:
    _register_return_range(lookback_days)
