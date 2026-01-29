"""
Accumulation Zone Conditions
조용한 매집 구간 탐지 조건

Layer 1: Primitive Conditions (기본 빌딩 블록)
- BollingerWidthCondition: BB 폭 체크
- VolumeBelowAvgCondition: 평균 대비 거래량
- PriceFlatCondition: 가격 변동폭 (횡보)
- OBVTrendCondition: OBV 방향
- StochasticLevelCondition: 스토캐스틱 레벨
- VPCITrendCondition: VPCI 방향

Layer 2: Divergence Conditions (다이버전스)
- OBVDivergenceCondition: Price flat + OBV up
- StochasticDivergenceCondition: Price low + Stoch higher low
- VPCIDivergenceCondition: Price flat + VPCI up

Usage:
    from screener.conditions.accumulation import (
        BollingerWidthCondition,
        VolumeBelowAvgCondition,
        OBVDivergenceCondition,
    )
"""

import pandas as pd
import numpy as np

from .base import BaseCondition, ConditionResult
from discovery.indicators import (
    calculate_obv,
    calculate_stochastic,
    calculate_vpci,
    calculate_bollinger_width,
)


# ============================================================
# Layer 1: Primitive Conditions
# ============================================================

class BollingerWidthCondition(BaseCondition):
    """
    볼린저 밴드 폭 조건
    BB 폭이 특정 값 이하일 때 매칭 (수축 구간)
    """

    def __init__(self, max_width_pct: float = 10.0, period: int = 20, std_dev: float = 2.0):
        """
        Args:
            max_width_pct: 최대 BB 폭 (%, 기본 10%)
            period: 이동평균 기간 (기본 20)
            std_dev: 표준편차 배수 (기본 2.0)
        """
        self.max_width_pct = max_width_pct
        self.period = period
        self.std_dev = std_dev

    @property
    def name(self) -> str:
        return f"bb_width_below_{self.max_width_pct}pct"

    @property
    def required_days(self) -> int:
        return self.period + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        bb_width = calculate_bollinger_width(data['close'], self.period, self.std_dev)
        current_width = bb_width.iloc[-1]

        if pd.isna(current_width):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "BB width is NaN"}
            )

        matched = current_width <= self.max_width_pct

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "bb_width_pct": float(current_width),
                "max_width_pct": self.max_width_pct,
                "period": self.period,
            }
        )

    def __repr__(self) -> str:
        return f"BollingerWidthCondition(max_width_pct={self.max_width_pct}, period={self.period})"


class VolumeBelowAvgCondition(BaseCondition):
    """
    평균 거래량 이하 조건
    거래량이 평균의 특정 배수 이하일 때 매칭 (조용한 구간)
    """

    def __init__(self, multiplier: float = 0.8, period: int = 20):
        """
        Args:
            multiplier: 평균 대비 배수 (기본 0.8 = 80%)
            period: 평균 계산 기간 (기본 20일)
        """
        self.multiplier = multiplier
        self.period = period

    @property
    def name(self) -> str:
        return f"volume_below_{self.multiplier}x_avg"

    @property
    def required_days(self) -> int:
        return self.period + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period + 1:
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
        matched = ratio <= self.multiplier

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
        return f"VolumeBelowAvgCondition(multiplier={self.multiplier}, period={self.period})"


class PriceFlatCondition(BaseCondition):
    """
    가격 횡보 조건
    일정 기간 동안의 가격 변동폭이 특정 % 이하일 때 매칭
    """

    def __init__(self, max_range_pct: float = 5.0, period: int = 20):
        """
        Args:
            max_range_pct: 최대 가격 변동폭 (%, 기본 5%)
            period: 측정 기간 (기본 20일)
        """
        self.max_range_pct = max_range_pct
        self.period = period

    @property
    def name(self) -> str:
        return f"price_flat_{self.max_range_pct}pct_{self.period}d"

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

        recent_data = data.tail(self.period)
        high_max = recent_data['high'].max()
        low_min = recent_data['low'].min()
        avg_price = recent_data['close'].mean()

        if avg_price == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Average price is zero"}
            )

        range_pct = ((high_max - low_min) / avg_price) * 100
        matched = range_pct <= self.max_range_pct

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "range_pct": float(range_pct),
                "max_range_pct": self.max_range_pct,
                "high_max": float(high_max),
                "low_min": float(low_min),
                "period": self.period,
            }
        )

    def __repr__(self) -> str:
        return f"PriceFlatCondition(max_range_pct={self.max_range_pct}, period={self.period})"


class OBVTrendCondition(BaseCondition):
    """
    OBV 추세 조건
    OBV가 특정 방향으로 상승/하락할 때 매칭
    """

    def __init__(self, direction: str = "up", lookback: int = 20):
        """
        Args:
            direction: 추세 방향 ("up" 또는 "down")
            lookback: 측정 기간 (기본 20일)
        """
        if direction not in ("up", "down"):
            raise ValueError("direction must be 'up' or 'down'")
        self.direction = direction
        self.lookback = lookback

    @property
    def name(self) -> str:
        return f"obv_trend_{self.direction}_{self.lookback}d"

    @property
    def required_days(self) -> int:
        return self.lookback + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.lookback + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        obv = calculate_obv(data['close'], data['volume'])
        obv_now = obv.iloc[-1]
        obv_past = obv.iloc[-(self.lookback + 1)]

        obv_change = obv_now - obv_past
        obv_change_pct = (obv_change / abs(obv_past)) * 100 if obv_past != 0 else 0

        if self.direction == "up":
            matched = obv_change > 0
        else:
            matched = obv_change < 0

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "obv_now": float(obv_now),
                "obv_past": float(obv_past),
                "obv_change": float(obv_change),
                "obv_change_pct": float(obv_change_pct),
                "direction": self.direction,
                "lookback": self.lookback,
            }
        )

    def __repr__(self) -> str:
        return f"OBVTrendCondition(direction='{self.direction}', lookback={self.lookback})"


class StochasticLevelCondition(BaseCondition):
    """
    스토캐스틱 레벨 조건
    스토캐스틱 K가 특정 레벨 이하/이상일 때 매칭
    """

    def __init__(
        self,
        threshold: float = 20.0,
        condition: str = "below",
        k_period: int = 14,
        d_period: int = 3
    ):
        """
        Args:
            threshold: 기준 레벨 (기본 20)
            condition: "below" (이하) 또는 "above" (이상)
            k_period: %K 기간 (기본 14)
            d_period: %D 기간 (기본 3)
        """
        if condition not in ("below", "above"):
            raise ValueError("condition must be 'below' or 'above'")
        self.threshold = threshold
        self.condition = condition
        self.k_period = k_period
        self.d_period = d_period

    @property
    def name(self) -> str:
        return f"stoch_{self.condition}_{self.threshold}"

    @property
    def required_days(self) -> int:
        return self.k_period + self.d_period + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.k_period + self.d_period:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        stoch_k, stoch_d = calculate_stochastic(
            data['high'], data['low'], data['close'],
            self.k_period, self.d_period
        )
        current_k = stoch_k.iloc[-1]
        current_d = stoch_d.iloc[-1]

        if pd.isna(current_k):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Stochastic K is NaN"}
            )

        if self.condition == "below":
            matched = current_k <= self.threshold
        else:
            matched = current_k >= self.threshold

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "stoch_k": float(current_k),
                "stoch_d": float(current_d) if not pd.isna(current_d) else None,
                "threshold": self.threshold,
                "condition": self.condition,
            }
        )

    def __repr__(self) -> str:
        return f"StochasticLevelCondition(threshold={self.threshold}, condition='{self.condition}')"


class VPCITrendCondition(BaseCondition):
    """
    VPCI 추세 조건
    VPCI가 특정 방향으로 상승/하락할 때 매칭
    """

    def __init__(
        self,
        direction: str = "up",
        short_period: int = 5,
        long_period: int = 20,
        lookback: int = 10
    ):
        """
        Args:
            direction: 추세 방향 ("up" 또는 "down")
            short_period: 단기 기간 (기본 5)
            long_period: 장기 기간 (기본 20)
            lookback: 추세 측정 기간 (기본 10)
        """
        if direction not in ("up", "down"):
            raise ValueError("direction must be 'up' or 'down'")
        self.direction = direction
        self.short_period = short_period
        self.long_period = long_period
        self.lookback = lookback

    @property
    def name(self) -> str:
        return f"vpci_trend_{self.direction}_{self.lookback}d"

    @property
    def required_days(self) -> int:
        return self.long_period + self.lookback + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.long_period + self.lookback:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        vpci = calculate_vpci(
            data['close'], data['volume'],
            self.short_period, self.long_period
        )
        vpci_now = vpci.iloc[-1]
        vpci_past = vpci.iloc[-(self.lookback + 1)]

        if pd.isna(vpci_now) or pd.isna(vpci_past):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "VPCI is NaN"}
            )

        vpci_change = vpci_now - vpci_past

        if self.direction == "up":
            matched = vpci_change > 0
        else:
            matched = vpci_change < 0

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "vpci_now": float(vpci_now),
                "vpci_past": float(vpci_past),
                "vpci_change": float(vpci_change),
                "direction": self.direction,
                "lookback": self.lookback,
            }
        )

    def __repr__(self) -> str:
        return f"VPCITrendCondition(direction='{self.direction}', lookback={self.lookback})"


# ============================================================
# Layer 2: Divergence Conditions
# ============================================================

class OBVDivergenceCondition(BaseCondition):
    """
    OBV 다이버전스 조건
    가격은 횡보하는데 OBV가 상승할 때 매칭 (매집 신호)
    """

    def __init__(
        self,
        price_max_range_pct: float = 5.0,
        obv_min_change_pct: float = 5.0,
        period: int = 20
    ):
        """
        Args:
            price_max_range_pct: 가격 횡보 판단 기준 (%, 기본 5%)
            obv_min_change_pct: OBV 상승 판단 기준 (%, 기본 5%)
            period: 측정 기간 (기본 20일)
        """
        self.price_max_range_pct = price_max_range_pct
        self.obv_min_change_pct = obv_min_change_pct
        self.period = period

    @property
    def name(self) -> str:
        return f"obv_divergence_{self.period}d"

    @property
    def required_days(self) -> int:
        return self.period + 30

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.period + 1:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        # 가격 횡보 체크
        recent_data = data.tail(self.period)
        high_max = recent_data['high'].max()
        low_min = recent_data['low'].min()
        avg_price = recent_data['close'].mean()

        if avg_price == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Average price is zero"}
            )

        price_range_pct = ((high_max - low_min) / avg_price) * 100
        price_flat = price_range_pct <= self.price_max_range_pct

        # OBV 상승 체크
        obv = calculate_obv(data['close'], data['volume'])
        obv_now = obv.iloc[-1]
        obv_past = obv.iloc[-(self.period + 1)]

        obv_change_pct = ((obv_now - obv_past) / abs(obv_past)) * 100 if obv_past != 0 else 0
        obv_up = obv_change_pct >= self.obv_min_change_pct

        matched = price_flat and obv_up

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "price_range_pct": float(price_range_pct),
                "price_flat": price_flat,
                "obv_change_pct": float(obv_change_pct),
                "obv_up": obv_up,
                "period": self.period,
            }
        )

    def __repr__(self) -> str:
        return f"OBVDivergenceCondition(period={self.period})"


class StochasticDivergenceCondition(BaseCondition):
    """
    스토캐스틱 다이버전스 조건
    가격은 저점을 낮추는데 스토캐스틱은 저점을 높일 때 매칭 (상승 다이버전스)
    """

    def __init__(
        self,
        k_period: int = 14,
        d_period: int = 3,
        lookback: int = 20,
        divergence_threshold: float = 5.0
    ):
        """
        Args:
            k_period: %K 기간 (기본 14)
            d_period: %D 기간 (기본 3)
            lookback: 다이버전스 탐색 기간 (기본 20)
            divergence_threshold: 다이버전스 판단 기준 (%, 기본 5%)
        """
        self.k_period = k_period
        self.d_period = d_period
        self.lookback = lookback
        self.divergence_threshold = divergence_threshold

    @property
    def name(self) -> str:
        return f"stoch_divergence_{self.lookback}d"

    @property
    def required_days(self) -> int:
        return self.k_period + self.d_period + self.lookback + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        required = self.k_period + self.d_period + self.lookback
        if len(data) < required:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        stoch_k, _ = calculate_stochastic(
            data['high'], data['low'], data['close'],
            self.k_period, self.d_period
        )

        # 최근 lookback 기간 데이터
        recent_close = data['close'].tail(self.lookback)
        recent_stoch = stoch_k.tail(self.lookback)

        # 첫번째 절반과 두번째 절반 비교
        half = self.lookback // 2
        first_half_close = recent_close.iloc[:half]
        second_half_close = recent_close.iloc[half:]
        first_half_stoch = recent_stoch.iloc[:half]
        second_half_stoch = recent_stoch.iloc[half:]

        # 가격 저점 비교 (두번째 절반이 더 낮거나 비슷)
        price_low_first = first_half_close.min()
        price_low_second = second_half_close.min()
        price_lower_or_flat = price_low_second <= price_low_first * (1 + self.divergence_threshold / 100)

        # 스토캐스틱 저점 비교 (두번째 절반이 더 높음)
        stoch_low_first = first_half_stoch.min()
        stoch_low_second = second_half_stoch.min()
        stoch_higher = stoch_low_second > stoch_low_first

        matched = price_lower_or_flat and stoch_higher

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "price_low_first": float(price_low_first),
                "price_low_second": float(price_low_second),
                "stoch_low_first": float(stoch_low_first) if not pd.isna(stoch_low_first) else None,
                "stoch_low_second": float(stoch_low_second) if not pd.isna(stoch_low_second) else None,
                "price_lower_or_flat": price_lower_or_flat,
                "stoch_higher": stoch_higher,
                "lookback": self.lookback,
            }
        )

    def __repr__(self) -> str:
        return f"StochasticDivergenceCondition(lookback={self.lookback})"


class VPCIDivergenceCondition(BaseCondition):
    """
    VPCI 다이버전스 조건
    가격은 횡보하는데 VPCI가 상승할 때 매칭 (조용한 매집 신호)
    """

    def __init__(
        self,
        price_max_range_pct: float = 5.0,
        short_period: int = 5,
        long_period: int = 20,
        lookback: int = 20
    ):
        """
        Args:
            price_max_range_pct: 가격 횡보 판단 기준 (%, 기본 5%)
            short_period: VPCI 단기 기간 (기본 5)
            long_period: VPCI 장기 기간 (기본 20)
            lookback: 측정 기간 (기본 20)
        """
        self.price_max_range_pct = price_max_range_pct
        self.short_period = short_period
        self.long_period = long_period
        self.lookback = lookback

    @property
    def name(self) -> str:
        return f"vpci_divergence_{self.lookback}d"

    @property
    def required_days(self) -> int:
        return self.long_period + self.lookback + 30

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.long_period + self.lookback:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        # 가격 횡보 체크
        recent_data = data.tail(self.lookback)
        high_max = recent_data['high'].max()
        low_min = recent_data['low'].min()
        avg_price = recent_data['close'].mean()

        if avg_price == 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Average price is zero"}
            )

        price_range_pct = ((high_max - low_min) / avg_price) * 100
        price_flat = price_range_pct <= self.price_max_range_pct

        # VPCI 상승 체크
        vpci = calculate_vpci(
            data['close'], data['volume'],
            self.short_period, self.long_period
        )
        vpci_now = vpci.iloc[-1]
        vpci_past = vpci.iloc[-(self.lookback + 1)]

        if pd.isna(vpci_now) or pd.isna(vpci_past):
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "VPCI is NaN"}
            )

        vpci_up = vpci_now > vpci_past

        matched = price_flat and vpci_up

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "price_range_pct": float(price_range_pct),
                "price_flat": price_flat,
                "vpci_now": float(vpci_now),
                "vpci_past": float(vpci_past),
                "vpci_up": vpci_up,
                "lookback": self.lookback,
            }
        )

    def __repr__(self) -> str:
        return f"VPCIDivergenceCondition(lookback={self.lookback})"
