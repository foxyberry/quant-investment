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
# Parametric ratio / range conditions (replace 14 dynamic registrations)
# ---------------------------------------------------------------------------


@register_condition(
    key="volume_ma_ratio",
    label="Volume MA Ratio",
    description="Volume short MA / long MA ratio range filter",
    category="volume",
    params=[
        {"name": "short_period", "type": "int", "default": 5, "description": "Short MA period"},
        {"name": "long_period", "type": "int", "default": 20, "description": "Long MA period"},
        {"name": "min_ratio", "type": "float", "default": 0.8, "description": "Minimum ratio"},
        {"name": "max_ratio", "type": "float", "default": 3.0, "description": "Maximum ratio"},
    ],
    recommended=True,
    order=12,
)
class VolumeMARatioCondition(BaseCondition):
    """Compare short-term vs long-term volume moving averages.

    Parameters
    ----------
    short_period : int
        Short MA period in trading days (must be >= 1).
    long_period : int
        Long MA period in trading days (must be > short_period).
    min_ratio : float
        Minimum acceptable ratio (short_avg / long_avg).
    max_ratio : float
        Maximum acceptable ratio (short_avg / long_avg).
    """

    def __init__(
        self,
        short_period: int = 5,
        long_period: int = 20,
        min_ratio: float = 0.8,
        max_ratio: float = 3.0,
    ) -> None:
        self.short_period: int = max(1, int(short_period))
        self.long_period: int = max(self.short_period + 1, int(long_period))
        self.min_ratio: float = float(min_ratio)
        self.max_ratio: float = float(max_ratio)

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


@register_condition(
    key="return_pct_range",
    label="Return % Range",
    description="N-day return percentage range filter",
    category="price",
    params=[
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
        {"name": "min_return_pct", "type": "float", "default": -5.0, "description": "Minimum return %"},
        {"name": "max_return_pct", "type": "float", "default": 5.0, "description": "Maximum return %"},
    ],
    recommended=True,
    order=13,
)
class ReturnRangeCondition(BaseCondition):
    """Filter stocks by N-day return percentage within a range.

    Parameters
    ----------
    lookback_days : int
        Number of trading days to look back (must be >= 1).
    min_return_pct : float
        Minimum acceptable return percentage.
    max_return_pct : float
        Maximum acceptable return percentage.
    """

    def __init__(
        self,
        lookback_days: int = 5,
        min_return_pct: float = -5.0,
        max_return_pct: float = 5.0,
    ) -> None:
        self.lookback_days: int = max(1, int(lookback_days))
        self.min_return_pct: float = float(min_return_pct)
        self.max_return_pct: float = float(max_return_pct)

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


# ---------------------------------------------------------------------------
# Legacy aliases — keep old keys in CLASS_MAP only (no metadata → hidden
# from the node palette) so that saved strategies referencing them still work.
# Uses functools.partial so that default params match the old variant-specific
# defaults (e.g. volume_ma_ratio_2_20 → short_period=2, long_period=20).
# ---------------------------------------------------------------------------

from .registry import register_alias  # noqa: E402

for _sp in [2, 3, 5, 10]:
    for _lp in [20, 60]:
        register_alias(
            f"volume_ma_ratio_{_sp}_{_lp}",
            VolumeMARatioCondition,
            short_period=_sp,
            long_period=_lp,
        )

for _ld in [1, 2, 3, 5, 10, 20]:
    register_alias(
        f"return_pct_{_ld}d_minmax",
        ReturnRangeCondition,
        lookback_days=_ld,
    )
