"""
Screening Conditions Module
스크리닝 조건 모듈

Usage:
    from screener.conditions import (
        # Base
        BaseCondition, ConditionResult,

        # Price conditions
        MinPriceCondition, MaxPriceCondition, PriceRangeCondition,

        # Volume conditions
        MinVolumeCondition, VolumeAboveAvgCondition, VolumeSpikeCondition,

        # MA conditions
        MATouchCondition, AboveMACondition, BelowMACondition,
        MACrossUpCondition, MACrossDownCondition,

        # RSI conditions
        RSIOversoldCondition, RSIOverboughtCondition, RSIRangeCondition,

        # Composite
        AndCondition, OrCondition, NotCondition,
    )
"""

from .base import BaseCondition, ConditionResult, ConditionError

from .price import (
    MinPriceCondition,
    MaxPriceCondition,
    PriceRangeCondition,
    PriceChangeCondition,
)

from .volume import (
    MinVolumeCondition,
    VolumeAboveAvgCondition,
    VolumeSpikeCondition,
)

from .ma import (
    MATouchCondition,
    AboveMACondition,
    BelowMACondition,
    MACrossUpCondition,
    MACrossDownCondition,
)

from .rsi import (
    RSIOversoldCondition,
    RSIOverboughtCondition,
    RSIRangeCondition,
)

from .composite import (
    AndCondition,
    OrCondition,
    NotCondition,
)

__all__ = [
    # Base
    'BaseCondition', 'ConditionResult', 'ConditionError',

    # Price
    'MinPriceCondition', 'MaxPriceCondition', 'PriceRangeCondition', 'PriceChangeCondition',

    # Volume
    'MinVolumeCondition', 'VolumeAboveAvgCondition', 'VolumeSpikeCondition',

    # MA
    'MATouchCondition', 'AboveMACondition', 'BelowMACondition',
    'MACrossUpCondition', 'MACrossDownCondition',

    # RSI
    'RSIOversoldCondition', 'RSIOverboughtCondition', 'RSIRangeCondition',

    # Composite
    'AndCondition', 'OrCondition', 'NotCondition',
]
