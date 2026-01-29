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


class ConditionError(Exception):
    """조건 평가 에러"""
    pass
