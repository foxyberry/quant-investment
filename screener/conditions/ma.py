"""
Moving Average Conditions
이동평균선 관련 스크리닝 조건

Usage:
    from screener.conditions.ma import MATouchCondition, AboveMACondition, BelowMACondition
"""

import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


@register_condition(
    key="ma_touch",
    label="MA Touch",
    description="Price near moving average",
    category="movingAverage",
    params=[
        {"name": "period", "type": "int", "default": 120, "description": "MA period"},
        {"name": "threshold", "type": "float", "default": 0.02, "description": "Touch threshold (ratio)"},
    ],
    recommended=True,
    order=10,
)
class MATouchCondition(BaseCondition):
    """이동평균선 터치 조건"""

    def __init__(self, period: int = 20, threshold: float = 0.02):
        """
        Args:
            period: 이동평균 기간
            threshold: 터치 판정 기준 (기본 2%)
        """
        self.period = period
        self.threshold = threshold

    @property
    def name(self) -> str:
        return f"ma_touch_{self.period}d"

    @property
    def required_days(self) -> int:
        return self.period + 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        close = data['close']
        ma = close.rolling(self.period).mean()

        current_price = close.iloc[-1]
        ma_value = ma.iloc[-1]

        if pd.isna(ma_value):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "MA calculation failed"}
            )

        distance_pct = abs(current_price - ma_value) / ma_value
        matched = distance_pct <= self.threshold

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "ma_value": float(ma_value),
                "ma_period": self.period,
                "distance_pct": float(distance_pct),
                "threshold": self.threshold,
            }
        )

    def __repr__(self) -> str:
        return f"MATouchCondition(period={self.period}, threshold={self.threshold})"


@register_condition(
    key="above_ma",
    label="Above MA",
    description="Price above moving average",
    category="movingAverage",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "MA period"},
        {"name": "min_distance_pct", "type": "float", "default": 0, "description": "Min distance %"},
    ],
    recommended=True,
    order=30,
)
class AboveMACondition(BaseCondition):
    """이동평균선 위 조건"""

    def __init__(self, period: int = 20, min_distance_pct: float = 0):
        """
        Args:
            period: 이동평균 기간
            min_distance_pct: 최소 이격률 (기본 0%)
        """
        self.period = period
        self.min_distance_pct = min_distance_pct

    @property
    def name(self) -> str:
        return f"above_ma_{self.period}d"

    @property
    def required_days(self) -> int:
        return self.period + 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        close = data['close']
        ma = close.rolling(self.period).mean()

        current_price = close.iloc[-1]
        ma_value = ma.iloc[-1]

        if pd.isna(ma_value):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "MA calculation failed"}
            )

        distance_pct = (current_price - ma_value) / ma_value
        matched = distance_pct >= self.min_distance_pct

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "ma_value": float(ma_value),
                "ma_period": self.period,
                "distance_pct": float(distance_pct),
            }
        )

    def __repr__(self) -> str:
        return f"AboveMACondition(period={self.period})"


@register_condition(
    key="below_ma",
    label="Below MA",
    description="Price below moving average",
    category="movingAverage",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "MA period"},
        {"name": "max_distance_pct", "type": "float", "default": 0, "description": "Max distance %"},
    ],
)
class BelowMACondition(BaseCondition):
    """이동평균선 아래 조건"""

    def __init__(self, period: int = 20, max_distance_pct: float = 0):
        """
        Args:
            period: 이동평균 기간
            max_distance_pct: 최대 이격률 (기본 0%, 음수)
        """
        self.period = period
        self.max_distance_pct = max_distance_pct

    @property
    def name(self) -> str:
        return f"below_ma_{self.period}d"

    @property
    def required_days(self) -> int:
        return self.period + 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        close = data['close']
        ma = close.rolling(self.period).mean()

        current_price = close.iloc[-1]
        ma_value = ma.iloc[-1]

        if pd.isna(ma_value):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "MA calculation failed"}
            )

        distance_pct = (current_price - ma_value) / ma_value
        matched = distance_pct <= self.max_distance_pct

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "ma_value": float(ma_value),
                "ma_period": self.period,
                "distance_pct": float(distance_pct),
            }
        )

    def __repr__(self) -> str:
        return f"BelowMACondition(period={self.period})"


@register_condition(
    key="ma_cross_up",
    label="MA Cross Up",
    description="Golden cross (short MA crosses above long MA)",
    category="movingAverage",
    params=[
        {"name": "short_period", "type": "int", "default": 5, "description": "Short MA period"},
        {"name": "long_period", "type": "int", "default": 20, "description": "Long MA period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
    ],
    recommended=True,
    order=20,
)
class MACrossUpCondition(BaseCondition):
    """골든크로스 조건 (단기 MA가 장기 MA 상향 돌파)"""

    def __init__(self, short_period: int = 20, long_period: int = 60, lookback_days: int = 5):
        """
        Args:
            short_period: 단기 이동평균 기간
            long_period: 장기 이동평균 기간
            lookback_days: 크로스 발생 탐지 기간
        """
        self.short_period = short_period
        self.long_period = long_period
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return f"ma_cross_up_{self.short_period}_{self.long_period}"

    @property
    def required_days(self) -> int:
        return self.long_period + 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.long_period + self.lookback_days:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        close = data['close']
        short_ma = close.rolling(self.short_period).mean()
        long_ma = close.rolling(self.long_period).mean()

        # 최근 lookback_days 내 크로스 발생 체크
        matched = False
        cross_day = None

        for i in range(1, self.lookback_days + 1):
            prev_short = short_ma.iloc[-(i + 1)]
            prev_long = long_ma.iloc[-(i + 1)]
            curr_short = short_ma.iloc[-i]
            curr_long = long_ma.iloc[-i]

            if pd.isna(prev_short) or pd.isna(prev_long):
                continue

            if prev_short <= prev_long and curr_short > curr_long:
                matched = True
                cross_day = i
                break

        cross_date = data.index[-cross_day].strftime('%Y-%m-%d') if cross_day else None

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "short_ma": float(short_ma.iloc[-1]),
                "long_ma": float(long_ma.iloc[-1]),
                "short_period": self.short_period,
                "long_period": self.long_period,
                "cross_day": cross_day,
                "cross_date": cross_date,
            }
        )

    def __repr__(self) -> str:
        return f"MACrossUpCondition(short={self.short_period}, long={self.long_period})"


@register_condition(
    key="ma_cross_down",
    label="MA Cross Down",
    description="Death cross (short MA crosses below long MA)",
    category="movingAverage",
    params=[
        {"name": "short_period", "type": "int", "default": 20, "description": "Short MA period"},
        {"name": "long_period", "type": "int", "default": 60, "description": "Long MA period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
    ],
)
class MACrossDownCondition(BaseCondition):
    """데드크로스 조건 (단기 MA가 장기 MA 하향 돌파)"""

    def __init__(self, short_period: int = 20, long_period: int = 60, lookback_days: int = 5):
        """
        Args:
            short_period: 단기 이동평균 기간
            long_period: 장기 이동평균 기간
            lookback_days: 크로스 발생 탐지 기간
        """
        self.short_period = short_period
        self.long_period = long_period
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return f"ma_cross_down_{self.short_period}_{self.long_period}"

    @property
    def required_days(self) -> int:
        return self.long_period + 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.long_period + self.lookback_days:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        close = data['close']
        short_ma = close.rolling(self.short_period).mean()
        long_ma = close.rolling(self.long_period).mean()

        # 최근 lookback_days 내 크로스 발생 체크
        matched = False
        cross_day = None

        for i in range(1, self.lookback_days + 1):
            prev_short = short_ma.iloc[-(i + 1)]
            prev_long = long_ma.iloc[-(i + 1)]
            curr_short = short_ma.iloc[-i]
            curr_long = long_ma.iloc[-i]

            if pd.isna(prev_short) or pd.isna(prev_long):
                continue

            if prev_short >= prev_long and curr_short < curr_long:
                matched = True
                cross_day = i
                break

        cross_date = data.index[-cross_day].strftime('%Y-%m-%d') if cross_day else None

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "short_ma": float(short_ma.iloc[-1]),
                "long_ma": float(long_ma.iloc[-1]),
                "short_period": self.short_period,
                "long_period": self.long_period,
                "cross_day": cross_day,
                "cross_date": cross_date,
            }
        )

    def __repr__(self) -> str:
        return f"MACrossDownCondition(short={self.short_period}, long={self.long_period})"
