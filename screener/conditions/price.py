"""
Price Conditions
가격 관련 스크리닝 조건

Usage:
    from screener.conditions.price import MinPriceCondition, PriceRangeCondition
"""

from typing import Optional
import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


@register_condition(
    key="min_price",
    label="Min Price",
    description="Stock price >= threshold",
    category="price",
    params=[{"name": "min_price", "type": "float", "default": 5000, "description": "Minimum price"}],
)
class MinPriceCondition(BaseCondition):
    """최소 주가 조건"""

    def __init__(self, min_price: float):
        """
        Args:
            min_price: 최소 주가
        """
        self.min_price = min_price

    @property
    def name(self) -> str:
        return f"min_price_{self.min_price}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if data.empty:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No data"}
            )

        current_price = data['close'].iloc[-1]
        matched = current_price >= self.min_price

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "min_price": self.min_price,
            }
        )

    def __repr__(self) -> str:
        return f"MinPriceCondition(min_price={self.min_price})"


@register_condition(
    key="max_price",
    label="Max Price",
    description="Stock price <= threshold",
    category="price",
    params=[{"name": "max_price", "type": "float", "default": 100000, "description": "Maximum price"}],
)
class MaxPriceCondition(BaseCondition):
    """최대 주가 조건"""

    def __init__(self, max_price: float):
        """
        Args:
            max_price: 최대 주가
        """
        self.max_price = max_price

    @property
    def name(self) -> str:
        return f"max_price_{self.max_price}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if data.empty:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No data"}
            )

        current_price = data['close'].iloc[-1]
        matched = current_price <= self.max_price

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "max_price": self.max_price,
            }
        )

    def __repr__(self) -> str:
        return f"MaxPriceCondition(max_price={self.max_price})"


@register_condition(
    key="price_range",
    label="Price Range",
    description="Stock price within range",
    category="price",
    params=[
        {"name": "min_price", "type": "float", "default": 0, "description": "Min price"},
        {"name": "max_price", "type": "float", "default": 999999, "description": "Max price"},
    ],
)
class PriceRangeCondition(BaseCondition):
    """가격 범위 조건"""

    def __init__(self, min_price: float = 0, max_price: float = float('inf')):
        """
        Args:
            min_price: 최소 주가
            max_price: 최대 주가
        """
        self.min_price = min_price
        self.max_price = max_price

    @property
    def name(self) -> str:
        return f"price_range_{self.min_price}_{self.max_price}"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if data.empty:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No data"}
            )

        current_price = data['close'].iloc[-1]
        matched = self.min_price <= current_price <= self.max_price

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "min_price": self.min_price,
                "max_price": self.max_price,
            }
        )

    def __repr__(self) -> str:
        return f"PriceRangeCondition(min={self.min_price}, max={self.max_price})"


@register_condition(
    key="price_change",
    label="Price Change %",
    description="Price change over N days",
    category="price",
    params=[
        {"name": "min_change_pct", "type": "float", "default": None, "description": "Min change %"},
        {"name": "max_change_pct", "type": "float", "default": None, "description": "Max change %"},
        {"name": "days", "type": "int", "default": 1, "description": "Period (days)"},
    ],
)
class PriceChangeCondition(BaseCondition):
    """가격 변동률 조건"""

    def __init__(self, min_change_pct: float = None, max_change_pct: float = None, days: int = 1):
        """
        Args:
            min_change_pct: 최소 변동률 (%)
            max_change_pct: 최대 변동률 (%)
            days: 비교 기간 (일)
        """
        self.min_change_pct = min_change_pct
        self.max_change_pct = max_change_pct
        self.days = days

    @property
    def name(self) -> str:
        return f"price_change_{self.days}d"

    @property
    def required_days(self) -> int:
        return self.days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.days + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        current_price = data['close'].iloc[-1]
        past_price = data['close'].iloc[-(self.days + 1)]
        change_pct = (current_price - past_price) / past_price * 100

        matched = True
        if self.min_change_pct is not None:
            matched = matched and (change_pct >= self.min_change_pct)
        if self.max_change_pct is not None:
            matched = matched and (change_pct <= self.max_change_pct)

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "past_price": float(past_price),
                "change_pct": float(change_pct),
                "days": self.days,
            }
        )

    def __repr__(self) -> str:
        return f"PriceChangeCondition(min={self.min_change_pct}%, max={self.max_change_pct}%, days={self.days})"


@register_condition(
    key="close_lag_1_lt_3",
    label="Close t-1 < t-3",
    description="Close price at t-1 is lower than close price at t-3",
    category="price",
    params=[
        {"name": "left_lag", "type": "int", "default": 1, "description": "Left lag day"},
        {"name": "right_lag", "type": "int", "default": 3, "description": "Right lag day"},
        {"name": "operator", "type": "str", "default": "lt", "description": "Comparison operator"},
    ],
)
class CloseLag1Lt3Condition(BaseCondition):
    """종가 지연 비교 조건 (기본: t-1 < t-3)."""

    def __init__(self, left_lag: int = 1, right_lag: int = 3, operator: str = "lt"):
        self.left_lag = max(1, int(left_lag))
        self.right_lag = max(1, int(right_lag))
        self.operator = operator if operator in {"lt", "gt"} else "lt"

    @property
    def name(self) -> str:
        return f"close_lag_compare_{self.left_lag}_{self.operator}_{self.right_lag}"

    @property
    def required_days(self) -> int:
        return max(self.left_lag, self.right_lag) + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if "close" not in data.columns:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Missing close column"},
            )

        if len(data) < self.required_days:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"},
            )

        left_idx = -(self.left_lag + 1)
        right_idx = -(self.right_lag + 1)
        left_value = data["close"].iloc[left_idx]
        right_value = data["close"].iloc[right_idx]

        if pd.isna(left_value) or pd.isna(right_value):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "NaN in close data"},
            )

        if self.operator == "lt":
            matched = bool(left_value < right_value)
        else:
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

    def __repr__(self) -> str:
        return (
            "CloseLag1Lt3Condition("
            f"left_lag={self.left_lag}, right_lag={self.right_lag}, operator='{self.operator}')"
        )


@register_condition(
    key="return_turnaround",
    label="Return Turnaround",
    description="Previous N-day return <= threshold and recent N-day return >= threshold",
    category="price",
    params=[
        {"name": "period_days", "type": "int", "default": 5, "description": "Return period (days)"},
        {"name": "prev_max_return_pct", "type": "float", "default": -2.0, "description": "Max previous return %"},
        {"name": "min_return_pct", "type": "float", "default": 2.0, "description": "Min recent return %"},
    ],
)
class ReturnTurnaroundCondition(BaseCondition):
    """이전 구간 약세 -> 최근 구간 반등 전환 조건"""

    def __init__(
        self,
        period_days: int = 5,
        prev_max_return_pct: float = -2.0,
        min_return_pct: float = 2.0,
    ):
        self.period_days = max(1, period_days)
        self.prev_max_return_pct = prev_max_return_pct
        self.min_return_pct = min_return_pct

    @property
    def name(self) -> str:
        return f"return_turnaround_{self.period_days}d"

    @property
    def required_days(self) -> int:
        return (self.period_days * 2) + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < (self.period_days * 2 + 1):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"},
            )

        current_price = data["close"].iloc[-1]
        boundary_price = data["close"].iloc[-(self.period_days + 1)]
        prev_price = data["close"].iloc[-(self.period_days * 2 + 1)]

        if boundary_price <= 0 or prev_price <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Invalid price data for return calculation"},
            )

        recent_return_pct = (current_price - boundary_price) / boundary_price * 100
        prev_return_pct = (boundary_price - prev_price) / prev_price * 100

        matched = (
            prev_return_pct <= self.prev_max_return_pct
            and recent_return_pct >= self.min_return_pct
        )

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "boundary_price": float(boundary_price),
                "prev_price": float(prev_price),
                "recent_return_pct": round(float(recent_return_pct), 3),
                "prev_return_pct": round(float(prev_return_pct), 3),
                "period_days": self.period_days,
                "prev_max_return_pct": self.prev_max_return_pct,
                "min_return_pct": self.min_return_pct,
            },
        )

    def __repr__(self) -> str:
        return (
            "ReturnTurnaroundCondition("
            f"period_days={self.period_days}, "
            f"prev_max_return_pct={self.prev_max_return_pct}, "
            f"min_return_pct={self.min_return_pct})"
        )


@register_condition(
    key="drawdown_from_high",
    label="Drawdown From N-day High",
    description="Drop % from N-day rolling high",
    category="price",
    params=[
        {"name": "lookback_days", "type": "int", "default": 120, "description": "Lookback period (days)"},
        {"name": "min_drop_pct", "type": "float", "default": 20.0, "description": "Minimum drop % from high"},
        {"name": "price_field", "type": "str", "default": "high", "description": "Price field for high: 'high' or 'close'"},
    ],
    recommended=True,
    order=50,
)
class DrawdownFromHighCondition(BaseCondition):
    """N일 고점 대비 하락률 조건"""

    def __init__(self, lookback_days: int = 120, min_drop_pct: float = 20.0, price_field: str = "high"):
        self.lookback_days = max(1, lookback_days)
        self.min_drop_pct = max(0.0, min_drop_pct)
        self.price_field = price_field if price_field in ("high", "close") else "high"

    @property
    def name(self) -> str:
        return f"drawdown_from_high_{self.lookback_days}d_{self.min_drop_pct}pct"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.lookback_days:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"},
            )

        col = self.price_field if self.price_field in data.columns else "close"
        rolling_high = data[col].iloc[-self.lookback_days:].max()
        current_price = data["close"].iloc[-1]

        if pd.isna(rolling_high) or pd.isna(current_price):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "NaN in price data"},
            )

        if rolling_high <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Rolling high is zero or negative"},
            )

        drop_pct = (rolling_high - current_price) / rolling_high * 100
        matched = drop_pct >= self.min_drop_pct

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "rolling_high": float(rolling_high),
                "drop_pct": round(float(drop_pct), 2),
                "lookback_days": self.lookback_days,
                "min_drop_pct": self.min_drop_pct,
                "price_field": col,
            },
        )

    def __repr__(self) -> str:
        return f"DrawdownFromHighCondition(lookback={self.lookback_days}, min_drop={self.min_drop_pct}%, field={self.price_field})"
