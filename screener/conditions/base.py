"""
Base Condition
스크리닝 조건 기본 클래스

Usage:
    from screener.conditions.base import BaseCondition, ConditionResult
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class ConditionResult:
    """조건 평가 결과"""
    matched: bool
    condition_name: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __bool__(self) -> bool:
        return self.matched


class BaseCondition(ABC):
    """
    스크리닝 조건 기본 클래스

    모든 스크리닝 조건은 이 클래스를 상속받아 구현
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """조건 이름"""
        pass

    @property
    @abstractmethod
    def required_days(self) -> int:
        """조건 평가에 필요한 데이터 일수"""
        pass

    @abstractmethod
    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        """
        조건 평가

        Args:
            ticker: 종목 코드
            data: OHLCV 데이터프레임

        Returns:
            ConditionResult 객체
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class PairsCondition(BaseCondition):
    """
    페어 트레이딩 조건 기본 클래스

    두 종목의 데이터를 동시에 평가하는 조건.
    evaluate()는 단일 종목 경로에서 호출되지 않도록 NotImplementedError를 발생시키고,
    실제 평가는 evaluate_pair()를 통해 수행.
    """

    @property
    def is_pairs(self) -> bool:
        return True

    @property
    def ticker2(self) -> str:
        """The companion ticker symbol, set via __init__ params."""
        return getattr(self, '_ticker2', '')

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        """Single-ticker evaluate not supported for pairs conditions."""
        raise NotImplementedError(
            f"{self.__class__.__name__} is a pairs condition. "
            "Use evaluate_pair(ticker1, data1, ticker2, data2) instead."
        )

    @abstractmethod
    def evaluate_pair(
        self,
        ticker1: str,
        data1: pd.DataFrame,
        ticker2: str,
        data2: pd.DataFrame,
    ) -> ConditionResult:
        """
        페어 조건 평가

        Args:
            ticker1: 주 종목 코드
            data1: 주 종목 OHLCV 데이터프레임
            ticker2: 보조 종목 코드
            data2: 보조 종목 OHLCV 데이터프레임

        Returns:
            ConditionResult 객체
        """
        pass


class ConditionError(Exception):
    """조건 평가 에러"""
    pass
