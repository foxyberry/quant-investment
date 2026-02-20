"""
Volume Conditions
거래량 관련 스크리닝 조건

Usage:
    from screener.conditions.volume import MinVolumeCondition, VolumeAboveAvgCondition
"""

import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


@register_condition(
    key="min_volume",
    label="Min Volume",
    description="Volume >= threshold",
    category="volume",
    params=[{"name": "min_volume", "type": "int", "default": 100000, "description": "Minimum volume"}],
)
class MinVolumeCondition(BaseCondition):
    """최소 거래량 조건"""

    def __init__(self, min_volume: int):
        """
        Args:
            min_volume: 최소 거래량
        """
        self.min_volume = min_volume

    @property
    def name(self) -> str:
        return f"min_volume_{self.min_volume}"

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

        current_volume = data['volume'].iloc[-1]
        matched = current_volume >= self.min_volume

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_volume": int(current_volume),
                "min_volume": self.min_volume,
            }
        )

    def __repr__(self) -> str:
        return f"MinVolumeCondition(min_volume={self.min_volume:,})"


@register_condition(
    key="volume_above_avg",
    label="Volume Above Avg",
    description="Volume above moving average",
    category="volume",
    params=[
        {"name": "multiplier", "type": "float", "default": 1.0, "description": "Avg multiplier"},
        {"name": "period", "type": "int", "default": 20, "description": "Average period"},
    ],
    recommended=True,
    order=70,
)
class VolumeAboveAvgCondition(BaseCondition):
    """평균 거래량 대비 조건"""

    def __init__(self, multiplier: float = 1.5, period: int = 20):
        """
        Args:
            multiplier: 평균 대비 배수
            period: 평균 계산 기간
        """
        self.multiplier = multiplier
        self.period = period

    @property
    def name(self) -> str:
        return f"volume_above_avg_{self.multiplier}x_{self.period}d"

    @property
    def required_days(self) -> int:
        return self.period + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        current_volume = data['volume'].iloc[-1]
        avg_volume = data['volume'].iloc[-self.period:].mean()

        if avg_volume == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Average volume is zero"}
            )

        ratio = current_volume / avg_volume
        matched = ratio >= self.multiplier

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_volume": int(current_volume),
                "avg_volume": float(avg_volume),
                "ratio": float(ratio),
                "multiplier": self.multiplier,
                "period": self.period,
            }
        )

    def __repr__(self) -> str:
        return f"VolumeAboveAvgCondition(multiplier={self.multiplier}, period={self.period})"


@register_condition(
    key="volume_spike",
    label="Volume Spike",
    description="Sudden volume increase",
    category="volume",
    params=[
        {"name": "multiplier", "type": "float", "default": 1.5, "description": "Spike multiplier"},
        {"name": "period", "type": "int", "default": 20, "description": "Average period"},
    ],
    recommended=True,
    order=60,
)
class VolumeSpikeCondition(BaseCondition):
    """거래량 급증 조건"""

    def __init__(self, multiplier: float = 2.0, period: int = 20):
        """
        Args:
            multiplier: 평균 대비 배수 (급증 기준)
            period: 평균 계산 기간
        """
        self.multiplier = multiplier
        self.period = period

    @property
    def name(self) -> str:
        return f"volume_spike_{self.multiplier}x"

    @property
    def required_days(self) -> int:
        return self.period + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        current_volume = data['volume'].iloc[-1]
        # 오늘 제외한 평균
        avg_volume = data['volume'].iloc[-(self.period + 1):-1].mean()

        if avg_volume == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Average volume is zero"}
            )

        ratio = current_volume / avg_volume
        matched = ratio >= self.multiplier

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_volume": int(current_volume),
                "avg_volume": float(avg_volume),
                "ratio": float(ratio),
                "multiplier": self.multiplier,
            }
        )

    def __repr__(self) -> str:
        return f"VolumeSpikeCondition(multiplier={self.multiplier}, period={self.period})"


@register_condition(
    key="avg_trading_value",
    label="Average Trading Value",
    description="N-day average trading value >= threshold",
    category="volume",
    params=[
        {"name": "lookback_days", "type": "int", "default": 20, "description": "Average period (days)"},
        {"name": "min_value", "type": "float", "default": 1500000000, "description": "Minimum avg trading value (KRW)"},
    ],
    recommended=True,
    order=65,
)
class AvgTradingValueCondition(BaseCondition):
    """평균 거래대금 조건 (저유동성 종목 제거)"""

    def __init__(self, lookback_days: int = 20, min_value: float = 1_500_000_000):
        self.lookback_days = max(1, lookback_days)
        self.min_value = max(0, min_value)

    @property
    def name(self) -> str:
        return f"avg_trading_value_{self.lookback_days}d"

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

        window = data.iloc[-self.lookback_days:]
        trading_values = window["close"] * window["volume"]
        avg_trading_value = trading_values.mean()

        if pd.isna(avg_trading_value):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "NaN in trading value data"},
            )

        current_trading_value = float(data["close"].iloc[-1] * data["volume"].iloc[-1])
        matched = avg_trading_value >= self.min_value

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "avg_trading_value": round(float(avg_trading_value)),
                "current_trading_value": round(current_trading_value),
                "lookback_days": self.lookback_days,
                "min_value": self.min_value,
            },
        )

    def __repr__(self) -> str:
        return f"AvgTradingValueCondition(lookback={self.lookback_days}, min_value={self.min_value:,.0f})"
