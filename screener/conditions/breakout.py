"""
Breakout Conditions
바닥 돌파 관련 스크리닝 조건

Migrated from legacy TechnicalScreener.analyze_bottom_breakout()

Usage:
    from screener.conditions.breakout import (
        BottomBreakoutCondition,
        FreshBreakoutCondition,
        BreakoutWithVolumeCondition,
    )
"""

import pandas as pd
from typing import Optional

from .base import BaseCondition, ConditionResult


class BottomBreakoutCondition(BaseCondition):
    """
    N일 바닥 대비 X% 돌파 조건

    N일간의 최저가 대비 현재가가 X% 이상 상승했는지 확인
    """

    def __init__(
        self,
        lookback_days: int = 20,
        breakout_pct: float = 5.0,
    ):
        """
        Args:
            lookback_days: 바닥 탐색 기간 (일)
            breakout_pct: 돌파 기준 퍼센트 (예: 5.0 = 5%)
        """
        self.lookback_days = lookback_days
        self.breakout_pct = breakout_pct

    @property
    def name(self) -> str:
        return f"bottom_breakout_{self.lookback_days}d_{self.breakout_pct}pct"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.lookback_days + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        # 현재가
        current_price = data['close'].iloc[-1]

        # 바닥 가격 (오늘 제외한 lookback_days 기간)
        lookback_lows = data['low'].iloc[-(self.lookback_days + 1):-1]
        bottom_price = lookback_lows.min()
        bottom_idx = lookback_lows.idxmin()

        # 돌파 가격
        breakout_price = bottom_price * (1 + self.breakout_pct / 100)

        # 현재가가 돌파 가격 이상인지
        is_breakout = current_price >= breakout_price

        # 바닥 대비 상승률
        price_from_bottom_pct = (current_price - bottom_price) / bottom_price * 100

        return ConditionResult(
            matched=is_breakout,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "bottom_price": float(bottom_price),
                "bottom_date": str(bottom_idx),
                "breakout_price": float(breakout_price),
                "price_from_bottom_pct": float(price_from_bottom_pct),
                "lookback_days": self.lookback_days,
                "breakout_pct": self.breakout_pct,
            }
        )

    def __repr__(self) -> str:
        return f"BottomBreakoutCondition(lookback={self.lookback_days}d, breakout={self.breakout_pct}%)"


class FreshBreakoutCondition(BaseCondition):
    """
    신규(첫) 돌파 조건

    이전에 돌파하지 않았고 오늘 처음 돌파한 경우를 감지
    """

    def __init__(
        self,
        lookback_days: int = 20,
        breakout_pct: float = 5.0,
    ):
        """
        Args:
            lookback_days: 바닥 탐색 기간 (일)
            breakout_pct: 돌파 기준 퍼센트
        """
        self.lookback_days = lookback_days
        self.breakout_pct = breakout_pct

    @property
    def name(self) -> str:
        return f"fresh_breakout_{self.lookback_days}d_{self.breakout_pct}pct"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.lookback_days + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        # 현재가
        current_price = data['close'].iloc[-1]

        # 바닥 가격 (오늘 제외)
        lookback_lows = data['low'].iloc[-(self.lookback_days + 1):-1]
        bottom_price = lookback_lows.min()
        bottom_idx = lookback_lows.idxmin()

        # 돌파 가격
        breakout_price = bottom_price * (1 + self.breakout_pct / 100)

        # 오늘 돌파 여부
        is_breakout_today = current_price >= breakout_price

        # 어제까지 돌파한 적 있는지 확인
        prev_closes = data['close'].iloc[-(self.lookback_days):-1]
        has_broken_before = (prev_closes >= breakout_price).any()

        # 신규 돌파: 이전엔 안 했고 오늘 처음 돌파
        is_fresh_breakout = is_breakout_today and not has_broken_before

        # 상태 판단
        if is_fresh_breakout:
            breakout_status = "FRESH_BREAKOUT"
        elif is_breakout_today:
            breakout_status = "ALREADY_ABOVE"
        else:
            breakout_status = "BELOW"

        # 바닥 대비 상승률
        price_from_bottom_pct = (current_price - bottom_price) / bottom_price * 100

        return ConditionResult(
            matched=is_fresh_breakout,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "bottom_price": float(bottom_price),
                "bottom_date": str(bottom_idx),
                "breakout_price": float(breakout_price),
                "price_from_bottom_pct": float(price_from_bottom_pct),
                "breakout_status": breakout_status,
                "is_breakout_today": is_breakout_today,
                "has_broken_before": has_broken_before,
            }
        )

    def __repr__(self) -> str:
        return f"FreshBreakoutCondition(lookback={self.lookback_days}d, breakout={self.breakout_pct}%)"


class BreakoutWithVolumeCondition(BaseCondition):
    """
    거래량 확인 돌파 조건

    바닥 돌파 + 거래량 급증을 함께 확인
    """

    def __init__(
        self,
        lookback_days: int = 20,
        breakout_pct: float = 5.0,
        volume_ratio: float = 1.5,
        volume_avg_days: int = 10,
        fresh_only: bool = True,
    ):
        """
        Args:
            lookback_days: 바닥 탐색 기간 (일)
            breakout_pct: 돌파 기준 퍼센트
            volume_ratio: 평균 거래량 대비 비율 (예: 1.5 = 1.5배)
            volume_avg_days: 평균 거래량 계산 기간
            fresh_only: True면 신규 돌파만, False면 모든 돌파
        """
        self.lookback_days = lookback_days
        self.breakout_pct = breakout_pct
        self.volume_ratio = volume_ratio
        self.volume_avg_days = volume_avg_days
        self.fresh_only = fresh_only

    @property
    def name(self) -> str:
        fresh_str = "fresh_" if self.fresh_only else ""
        return f"{fresh_str}breakout_volume_{self.lookback_days}d_{self.breakout_pct}pct"

    @property
    def required_days(self) -> int:
        return max(self.lookback_days, self.volume_avg_days) + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        required = max(self.lookback_days, self.volume_avg_days) + 1
        if len(data) < required:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        # 현재가 / 현재 거래량
        current_price = data['close'].iloc[-1]
        current_volume = data['volume'].iloc[-1]

        # 바닥 가격
        lookback_lows = data['low'].iloc[-(self.lookback_days + 1):-1]
        bottom_price = lookback_lows.min()
        bottom_idx = lookback_lows.idxmin()

        # 돌파 가격
        breakout_price = bottom_price * (1 + self.breakout_pct / 100)

        # 오늘 돌파 여부
        is_breakout_today = current_price >= breakout_price

        # 신규 돌파 확인 (fresh_only=True인 경우)
        is_fresh = True
        if self.fresh_only:
            prev_closes = data['close'].iloc[-(self.lookback_days):-1]
            has_broken_before = (prev_closes >= breakout_price).any()
            is_fresh = not has_broken_before

        # 거래량 확인
        avg_volume = data['volume'].iloc[-(self.volume_avg_days + 1):-1].mean()
        actual_volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        is_volume_spike = actual_volume_ratio >= self.volume_ratio

        # 최종 판단
        if self.fresh_only:
            matched = is_breakout_today and is_fresh and is_volume_spike
        else:
            matched = is_breakout_today and is_volume_spike

        # 바닥 대비 상승률
        price_from_bottom_pct = (current_price - bottom_price) / bottom_price * 100

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "bottom_price": float(bottom_price),
                "bottom_date": str(bottom_idx),
                "breakout_price": float(breakout_price),
                "price_from_bottom_pct": float(price_from_bottom_pct),
                "is_breakout_today": is_breakout_today,
                "is_fresh": is_fresh,
                "current_volume": float(current_volume),
                "avg_volume": float(avg_volume),
                "volume_ratio": float(actual_volume_ratio),
                "required_volume_ratio": self.volume_ratio,
                "is_volume_spike": is_volume_spike,
            }
        )

    def __repr__(self) -> str:
        fresh_str = "fresh_only, " if self.fresh_only else ""
        return f"BreakoutWithVolumeCondition({fresh_str}lookback={self.lookback_days}d, breakout={self.breakout_pct}%, vol_ratio={self.volume_ratio}x)"


class ResistanceBreakoutCondition(BaseCondition):
    """
    저항선 돌파 조건

    N일간의 최고가(저항선)를 돌파했는지 확인
    """

    def __init__(
        self,
        lookback_days: int = 20,
        breakout_margin_pct: float = 0.0,
    ):
        """
        Args:
            lookback_days: 저항선 탐색 기간 (일)
            breakout_margin_pct: 저항선 위 마진 (예: 1.0 = 1% 위)
        """
        self.lookback_days = lookback_days
        self.breakout_margin_pct = breakout_margin_pct

    @property
    def name(self) -> str:
        return f"resistance_breakout_{self.lookback_days}d"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.lookback_days + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        # 현재가
        current_price = data['close'].iloc[-1]

        # 저항선 (오늘 제외한 lookback_days 기간의 최고가)
        lookback_highs = data['high'].iloc[-(self.lookback_days + 1):-1]
        resistance_price = lookback_highs.max()
        resistance_idx = lookback_highs.idxmax()

        # 돌파 기준가 (저항선 + 마진)
        breakout_price = resistance_price * (1 + self.breakout_margin_pct / 100)

        # 돌파 여부
        is_breakout = current_price >= breakout_price

        # 저항선 대비 위치
        distance_from_resistance_pct = (current_price - resistance_price) / resistance_price * 100

        return ConditionResult(
            matched=is_breakout,
            condition_name=self.name,
            details={
                "current_price": float(current_price),
                "resistance_price": float(resistance_price),
                "resistance_date": str(resistance_idx),
                "breakout_price": float(breakout_price),
                "distance_from_resistance_pct": float(distance_from_resistance_pct),
                "lookback_days": self.lookback_days,
            }
        )

    def __repr__(self) -> str:
        return f"ResistanceBreakoutCondition(lookback={self.lookback_days}d, margin={self.breakout_margin_pct}%)"
