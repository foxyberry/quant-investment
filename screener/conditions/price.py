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
        self.lookback_days = lookback_days
        self.min_drop_pct = min_drop_pct
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

        col = self.price_field if self.price_field in data.columns else "high"
        rolling_high = data[col].iloc[-self.lookback_days:].max()

        if rolling_high == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Rolling high is zero"},
            )

        current_price = data["close"].iloc[-1]
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
                "price_field": self.price_field,
            },
        )

    def __repr__(self) -> str:
        return f"DrawdownFromHighCondition(lookback={self.lookback_days}, min_drop={self.min_drop_pct}%, field={self.price_field})"
