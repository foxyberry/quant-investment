"""
Volume Conditions
거래량 관련 스크리닝 조건

Usage:
    from screener.conditions.volume import MinVolumeCondition, VolumeAboveAvgCondition
"""

import pandas as pd

from .base import BaseCondition, ConditionResult


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
