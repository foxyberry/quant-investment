"""
RSI Conditions
RSI 관련 스크리닝 조건

Usage:
    from screener.conditions.rsi import RSIOversoldCondition, RSIOverboughtCondition
"""

import pandas as pd
import numpy as np

from .base import BaseCondition, ConditionResult


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


class RSIOversoldCondition(BaseCondition):
    """RSI 과매도 조건"""

    def __init__(self, threshold: float = 30, period: int = 14):
        """
        Args:
            threshold: 과매도 기준 (기본 30)
            period: RSI 기간
        """
        self.threshold = threshold
        self.period = period

    @property
    def name(self) -> str:
        return f"rsi_oversold_{self.threshold}"

    @property
    def required_days(self) -> int:
        return self.period + 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        rsi = calculate_rsi(data['close'], self.period)
        current_rsi = rsi.iloc[-1]

        if pd.isna(current_rsi):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "RSI calculation failed"}
            )

        matched = current_rsi <= self.threshold

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "rsi": float(current_rsi),
                "threshold": self.threshold,
                "period": self.period,
            }
        )

    def __repr__(self) -> str:
        return f"RSIOversoldCondition(threshold={self.threshold}, period={self.period})"


class RSIOverboughtCondition(BaseCondition):
    """RSI 과매수 조건"""

    def __init__(self, threshold: float = 70, period: int = 14):
        """
        Args:
            threshold: 과매수 기준 (기본 70)
            period: RSI 기간
        """
        self.threshold = threshold
        self.period = period

    @property
    def name(self) -> str:
        return f"rsi_overbought_{self.threshold}"

    @property
    def required_days(self) -> int:
        return self.period + 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        rsi = calculate_rsi(data['close'], self.period)
        current_rsi = rsi.iloc[-1]

        if pd.isna(current_rsi):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "RSI calculation failed"}
            )

        matched = current_rsi >= self.threshold

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "rsi": float(current_rsi),
                "threshold": self.threshold,
                "period": self.period,
            }
        )

    def __repr__(self) -> str:
        return f"RSIOverboughtCondition(threshold={self.threshold}, period={self.period})"


class RSIRangeCondition(BaseCondition):
    """RSI 범위 조건"""

    def __init__(self, lower: float = 30, upper: float = 70, period: int = 14):
        """
        Args:
            lower: 하한
            upper: 상한
            period: RSI 기간
        """
        self.lower = lower
        self.upper = upper
        self.period = period

    @property
    def name(self) -> str:
        return f"rsi_range_{self.lower}_{self.upper}"

    @property
    def required_days(self) -> int:
        return self.period + 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        rsi = calculate_rsi(data['close'], self.period)
        current_rsi = rsi.iloc[-1]

        if pd.isna(current_rsi):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "RSI calculation failed"}
            )

        matched = self.lower <= current_rsi <= self.upper

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "rsi": float(current_rsi),
                "lower": self.lower,
                "upper": self.upper,
                "period": self.period,
            }
        )

    def __repr__(self) -> str:
        return f"RSIRangeCondition(lower={self.lower}, upper={self.upper})"
