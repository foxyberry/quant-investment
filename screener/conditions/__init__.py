"""
Screening Conditions Module

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

        # Fundamental conditions
        PERatioCondition, PBRatioCondition, PSRatioCondition, PCFRatioCondition,
        DividendYieldCondition, EarningsYieldCondition, EbitEvCondition,
        FcfYieldCondition, PegRatioCondition, DebtToEquityCondition,
        CurrentRatioCondition, RoeCondition, PiotroskiFScoreCondition,
        AltmanZScoreCondition, RoicCondition, clear_info_cache,
    )
"""

from .base import BaseCondition, ConditionResult, ConditionError

from .price import (
    MinPriceCondition,
    MaxPriceCondition,
    PriceRangeCondition,
    PriceChangeCondition,
    ReturnTurnaroundCondition,
    DrawdownFromHighCondition,
)

from .volume import (
    MinVolumeCondition,
    VolumeAboveAvgCondition,
    VolumeSpikeCondition,
    AvgTradingValueCondition,
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

from .momentum import (
    EMACrossCondition,
    EMASlopeCondition,
    SMASlopeCondition,
    MACDSignalCrossCondition,
    MACDHistogramSlopeCondition,
    CCIOverboughtOversoldCondition,
    WilliamsRReversalCondition,
    TRIXCrossCondition,
    AroonTrendSignalCondition,
    MoneyFlowIndexSignalCondition,
)

from .risk import (
    DownsideVolatilityFilterCondition,
    SemivarianceFilterCondition,
    RollingSharpeFilterCondition,
    RollingSortinoFilterCondition,
    UlcerIndexFilterCondition,
    CalmarRatioFilterCondition,
    MaxDrawdownWindowFilterCondition,
    ReturnSkewnessFilterCondition,
    ReturnKurtosisFilterCondition,
    IntradayReturnFilterCondition,
)

from .composite import (
    AndCondition,
    OrCondition,
    NotCondition,
)

from .accumulation import (
    # Layer 1: Primitive Conditions
    BollingerWidthCondition,
    VolumeBelowAvgCondition,
    PriceFlatCondition,
    OBVTrendCondition,
    StochasticLevelCondition,
    VPCITrendCondition,
    # Layer 2: Divergence Conditions
    OBVDivergenceCondition,
    StochasticDivergenceCondition,
    VPCIDivergenceCondition,
)

from .breakout import (
    BottomBreakoutCondition,
    FreshBreakoutCondition,
    BreakoutWithVolumeCondition,
    ResistanceBreakoutCondition,
)

from .fundamental import (
    PERatioCondition,
    PBRatioCondition,
    PSRatioCondition,
    PCFRatioCondition,
    DividendYieldCondition,
    EarningsYieldCondition,
    EbitEvCondition,
    FcfYieldCondition,
    PegRatioCondition,
    DebtToEquityCondition,
    CurrentRatioCondition,
    RoeCondition,
    PiotroskiFScoreCondition,
    AltmanZScoreCondition,
    RoicCondition,
    clear_info_cache,
)

# Registry accessors (populated by @register_condition decorators above)
from .registry import get_condition_class_map, get_condition_metadata

__all__ = [
    # Base
    'BaseCondition', 'ConditionResult', 'ConditionError',

    # Price
    'MinPriceCondition', 'MaxPriceCondition', 'PriceRangeCondition', 'PriceChangeCondition',
    'ReturnTurnaroundCondition',
    'DrawdownFromHighCondition',

    # Volume
    'MinVolumeCondition', 'VolumeAboveAvgCondition', 'VolumeSpikeCondition',
    'AvgTradingValueCondition',

    # MA
    'MATouchCondition', 'AboveMACondition', 'BelowMACondition',
    'MACrossUpCondition', 'MACrossDownCondition',

    # RSI
    'RSIOversoldCondition', 'RSIOverboughtCondition', 'RSIRangeCondition',

    # Momentum
    'EMACrossCondition', 'EMASlopeCondition', 'SMASlopeCondition',
    'MACDSignalCrossCondition', 'MACDHistogramSlopeCondition',
    'CCIOverboughtOversoldCondition', 'WilliamsRReversalCondition',
    'TRIXCrossCondition', 'AroonTrendSignalCondition', 'MoneyFlowIndexSignalCondition',

    # Risk
    'DownsideVolatilityFilterCondition', 'SemivarianceFilterCondition',
    'RollingSharpeFilterCondition', 'RollingSortinoFilterCondition',
    'UlcerIndexFilterCondition', 'CalmarRatioFilterCondition',
    'MaxDrawdownWindowFilterCondition', 'ReturnSkewnessFilterCondition',
    'ReturnKurtosisFilterCondition', 'IntradayReturnFilterCondition',

    # Composite
    'AndCondition', 'OrCondition', 'NotCondition',

    # Accumulation (Layer 1 - Primitives)
    'BollingerWidthCondition', 'VolumeBelowAvgCondition', 'PriceFlatCondition',
    'OBVTrendCondition', 'StochasticLevelCondition', 'VPCITrendCondition',

    # Accumulation (Layer 2 - Divergences)
    'OBVDivergenceCondition', 'StochasticDivergenceCondition', 'VPCIDivergenceCondition',

    # Breakout
    'BottomBreakoutCondition', 'FreshBreakoutCondition',
    'BreakoutWithVolumeCondition', 'ResistanceBreakoutCondition',

    # Fundamental
    'PERatioCondition', 'PBRatioCondition', 'PSRatioCondition', 'PCFRatioCondition',
    'DividendYieldCondition', 'EarningsYieldCondition', 'EbitEvCondition', 'FcfYieldCondition',
    'PegRatioCondition', 'DebtToEquityCondition', 'CurrentRatioCondition', 'RoeCondition',
    'PiotroskiFScoreCondition', 'AltmanZScoreCondition', 'RoicCondition', 'clear_info_cache',

    # Registry
    'get_condition_class_map', 'get_condition_metadata',
]
