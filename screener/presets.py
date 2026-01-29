"""
Screening Presets
자주 사용하는 스크리닝 조건 조합

Usage:
    from screener.presets import ma_touch_160, oversold_bounce, golden_cross
    from screener.stock_screener import StockScreener

    # 프리셋 사용
    screener = StockScreener(conditions=ma_touch_160())
    results = screener.run(universe="KOSPI")

    # 프리셋 + 추가 조건
    screener = StockScreener(conditions=ma_touch_160())
    screener.add_condition(MinVolumeCondition(100000))
    results = screener.run(universe="KOSPI")
"""

from typing import List
from .conditions import (
    BaseCondition,
    # Price
    MinPriceCondition, MaxPriceCondition, PriceRangeCondition, PriceChangeCondition,
    # Volume
    MinVolumeCondition, VolumeAboveAvgCondition, VolumeSpikeCondition,
    # MA
    MATouchCondition, AboveMACondition, BelowMACondition, MACrossUpCondition, MACrossDownCondition,
    # RSI
    RSIOversoldCondition, RSIOverboughtCondition, RSIRangeCondition,
    # Composite
    AndCondition, OrCondition,
)


def ma_touch_160(threshold: float = 0.02, min_price: int = 5000) -> List[BaseCondition]:
    """
    160일선 터치 전략
    - 160일 이동평균선 근처 (±2%)
    - 최소 가격 5000원 이상
    """
    return [
        MinPriceCondition(min_price),
        MATouchCondition(period=160, threshold=threshold),
    ]


def ma_touch_120(threshold: float = 0.02, min_price: int = 5000) -> List[BaseCondition]:
    """
    120일선 터치 전략
    - 120일 이동평균선 근처 (±2%)
    - 최소 가격 5000원 이상
    """
    return [
        MinPriceCondition(min_price),
        MATouchCondition(period=120, threshold=threshold),
    ]


def ma_touch_200(threshold: float = 0.02, min_price: int = 5000) -> List[BaseCondition]:
    """
    200일선 터치 전략 (장기 추세선)
    - 200일 이동평균선 근처 (±2%)
    - 최소 가격 5000원 이상
    """
    return [
        MinPriceCondition(min_price),
        MATouchCondition(period=200, threshold=threshold),
    ]


def oversold_bounce(rsi_threshold: float = 30, min_price: int = 5000) -> List[BaseCondition]:
    """
    과매도 반등 전략
    - RSI 30 이하
    - 최소 가격 5000원 이상
    """
    return [
        MinPriceCondition(min_price),
        RSIOversoldCondition(threshold=rsi_threshold),
    ]


def golden_cross(short_period: int = 20, long_period: int = 60, min_price: int = 5000) -> List[BaseCondition]:
    """
    골든크로스 전략
    - 단기 MA가 장기 MA 상향 돌파
    - 최소 가격 5000원 이상
    """
    return [
        MinPriceCondition(min_price),
        MACrossUpCondition(short_period=short_period, long_period=long_period),
    ]


def dead_cross(short_period: int = 20, long_period: int = 60, min_price: int = 5000) -> List[BaseCondition]:
    """
    데드크로스 전략 (공매도/청산용)
    - 단기 MA가 장기 MA 하향 돌파
    - 최소 가격 5000원 이상
    """
    return [
        MinPriceCondition(min_price),
        MACrossDownCondition(short_period=short_period, long_period=long_period),
    ]


def volume_breakout(multiplier: float = 2.0, min_price: int = 5000) -> List[BaseCondition]:
    """
    거래량 돌파 전략
    - 평균 대비 2배 이상 거래량
    - 최소 가격 5000원 이상
    """
    return [
        MinPriceCondition(min_price),
        VolumeSpikeCondition(multiplier=multiplier),
    ]


def ma_touch_with_oversold(
    ma_period: int = 160,
    ma_threshold: float = 0.02,
    rsi_threshold: float = 40,
    min_price: int = 5000
) -> List[BaseCondition]:
    """
    이평선 터치 + RSI 과매도 복합 전략
    - 이평선 터치
    - RSI 40 이하
    - 최소 가격
    """
    return [
        MinPriceCondition(min_price),
        MATouchCondition(period=ma_period, threshold=ma_threshold),
        RSIOversoldCondition(threshold=rsi_threshold),
    ]


def trend_following(min_price: int = 5000) -> List[BaseCondition]:
    """
    추세 추종 전략
    - 20일선 위
    - 60일선 위
    - RSI 50 이상
    """
    return [
        MinPriceCondition(min_price),
        AboveMACondition(period=20),
        AboveMACondition(period=60),
        RSIRangeCondition(lower=50, upper=70),
    ]


def value_dip(min_price: int = 5000) -> List[BaseCondition]:
    """
    가치 저점 매수 전략
    - 120일선 아래
    - RSI 35 이하
    - 거래량 평균 이상
    """
    return [
        MinPriceCondition(min_price),
        BelowMACondition(period=120),
        RSIOversoldCondition(threshold=35),
        VolumeAboveAvgCondition(multiplier=1.0),
    ]


def momentum_breakout(min_price: int = 5000) -> List[BaseCondition]:
    """
    모멘텀 돌파 전략
    - 20일 골든크로스 + 거래량 급증
    """
    return [
        MinPriceCondition(min_price),
        MACrossUpCondition(short_period=5, long_period=20),
        VolumeSpikeCondition(multiplier=1.5),
    ]


# 프리셋 목록 (CLI 등에서 사용)
PRESET_REGISTRY = {
    "ma_touch_160": ma_touch_160,
    "ma_touch_120": ma_touch_120,
    "ma_touch_200": ma_touch_200,
    "oversold_bounce": oversold_bounce,
    "golden_cross": golden_cross,
    "dead_cross": dead_cross,
    "volume_breakout": volume_breakout,
    "ma_touch_with_oversold": ma_touch_with_oversold,
    "trend_following": trend_following,
    "value_dip": value_dip,
    "momentum_breakout": momentum_breakout,
}


def get_preset(name: str, **kwargs) -> List[BaseCondition]:
    """이름으로 프리셋 가져오기"""
    if name not in PRESET_REGISTRY:
        available = ", ".join(PRESET_REGISTRY.keys())
        raise ValueError(f"Unknown preset: {name}. Available: {available}")
    return PRESET_REGISTRY[name](**kwargs)


def list_presets() -> List[str]:
    """사용 가능한 프리셋 목록"""
    return list(PRESET_REGISTRY.keys())
