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
        AltmanZScoreCondition, RoicCondition, DsoTrendFilterCondition, clear_info_cache,
    )
"""

from .base import BaseCondition, ConditionResult, ConditionError, PairsCondition

from .price import (
    MinPriceCondition,
    MaxPriceCondition,
    PriceRangeCondition,
    PriceChangeCondition,
    ReturnTurnaroundCondition,
    DrawdownFromHighCondition,
)

from .basic_catalog import PriceLagCompareCondition, VolumeLagCompareCondition

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

from .time_price import (
    OvernightReturnFilterCondition,
    DistanceFrom52WLowCondition,
    DistanceFrom200DHighCondition,
    GapUpBreakawayCondition,
    GapDownExhaustionCondition,
    OpeningRangeBreakoutCondition,
    PivotPointBreakoutCondition,
    MonthOfYearSeasonalityCondition,
    TurnOfMonthEffectCondition,
    DayOfWeekSeasonalityCondition,
)

from .quant_trend import (
    Momentum121Condition,
    VolatilityNDayCondition,
    DistanceFrom52WHighCondition,
    RelativeStrengthVsBenchmarkCondition,
    ADXTrendStrengthCondition,
    MARibbonAlignmentCondition,
    GoldenCross50200Condition,
    DeathCross50200Condition,
    DonchianChannelBreakoutCondition,
    KeltnerChannelBreakoutCondition,
    SupertrendSignalCondition,
)

from .quant_oscillators import (
    BollingerSqueezeBreakoutCondition,
    BollingerPercentBCondition,
    PPOSignalCrossCondition,
    StochasticCrossSignalCondition,
    StochRSISignalCondition,
    AroonOscillatorSignalCondition,
    UltimateOscillatorSignalCondition,
    ChaikinMoneyFlowSignalCondition,
    ChaikinOscillatorSignalCondition,
    ADLineTrendCondition,
)

from .quant_indicators import (
    VWAPCrossSignalCondition,
    VWAPDistancePctCondition,
    RelativeVolumePercentileCondition,
    TurnoverRatioMinCondition,
    ATRPercentileFilterCondition,
    ATRExpansionBreakoutCondition,
    NATRFilterCondition,
    DMIDirectionalCrossCondition,
    IchimokuCloudBreakoutCondition,
    IchimokuTenkanKijunCrossCondition,
)

from .quant_statistical import (
    ParabolicSARFlipCondition,
    LinearRegressionSlopeFilterCondition,
    LinearRegressionAngleFilterCondition,
    LinearRegressionR2FilterCondition,
    BetaToBenchmarkCondition,
    CorrelationToBenchmarkCondition,
    SupportRetestSignalCondition,
    ResistanceRetestSignalCondition,
    AnalystRevision1MCondition,
    AnalystRevision3MCondition,
)

from .quant_fundamental_batch8 import (
    ReceivablesTurnoverRatioCondition,
    InventoryTurnoverRatioCondition,
    AssetTurnoverRatioCondition,
    CashflowToDebtRatioCondition,
    PriceToTangibleBookCondition,
    EVToSalesRatioCondition,
    EVToEbitdaRatioCondition,
    BookToMarketRatioCondition,
    EPSCAGR3YCondition,
    EPSGrowthYoYCondition,
)

from .quant_fundamental_batch9 import (
    RevenueCAGR3YCondition,
    RevenueGrowthYoYCondition,
    RevenueStabilityScoreCondition,
    EarningsStabilityScoreCondition,
    DebtServiceCoverageRatioCondition,
    NetDebtToEbitdaCondition,
    InterestCoverageRatioCondition,
    CashConversionRatioCondition,
    ROCEFilterCondition,
    ROAFilterCondition,
)

from .quant_shareholder_batch10 import (
    NetMarginCondition,
    GrossMarginCondition,
    OperatingMarginCondition,
    FreeCashFlowMarginCondition,
    PayoutRatioFilterCondition,
    DividendGrowth5YCondition,
    ShareholderYieldFilterCondition,
    NetShareIssuanceFilterCondition,
    BuybackYieldFilterCondition,
    InsiderNetBuyingCondition,
)

from .quant_special_batch11 import (
    ShortFloatPctFilterCondition,
    ShortInterestRatioFilterCondition,
    EarningsSurpriseFilterCondition,
    PostEarningsDriftCondition,
    PreEarningsDriftCondition,
    AccrualsRatioCondition,
    AssetGrowthRateCondition,
    GrossProfitabilityCondition,
    QualityScoreCondition,
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
    DsoTrendFilterCondition,
    clear_info_cache,
)

# Register bulk basic lag/ratio/range conditions.
from . import basic_catalog  # noqa: F401

# Registry accessors (populated by @register_condition decorators above)
from .registry import get_condition_class_map, get_condition_metadata, register_alias

__all__ = [
    # Base
    'BaseCondition', 'ConditionResult', 'ConditionError', 'PairsCondition',

    # Price
    'MinPriceCondition', 'MaxPriceCondition', 'PriceRangeCondition', 'PriceChangeCondition',
    'PriceLagCompareCondition', 'VolumeLagCompareCondition',
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

    # Time/Price
    'OvernightReturnFilterCondition', 'DistanceFrom52WLowCondition',
    'DistanceFrom200DHighCondition', 'GapUpBreakawayCondition',
    'GapDownExhaustionCondition', 'OpeningRangeBreakoutCondition',
    'PivotPointBreakoutCondition', 'MonthOfYearSeasonalityCondition',
    'TurnOfMonthEffectCondition', 'DayOfWeekSeasonalityCondition',

    # Quant Trend Batch 4
    'Momentum121Condition', 'VolatilityNDayCondition',
    'DistanceFrom52WHighCondition', 'RelativeStrengthVsBenchmarkCondition',
    'ADXTrendStrengthCondition', 'MARibbonAlignmentCondition',
    'GoldenCross50200Condition', 'DeathCross50200Condition',
    'DonchianChannelBreakoutCondition', 'KeltnerChannelBreakoutCondition',
    'SupertrendSignalCondition',

    # Quant Oscillator Batch 5
    'BollingerSqueezeBreakoutCondition', 'BollingerPercentBCondition',
    'PPOSignalCrossCondition', 'StochasticCrossSignalCondition',
    'StochRSISignalCondition', 'AroonOscillatorSignalCondition',
    'UltimateOscillatorSignalCondition', 'ChaikinMoneyFlowSignalCondition',
    'ChaikinOscillatorSignalCondition', 'ADLineTrendCondition',

    # Quant Indicator Batch 6
    'VWAPCrossSignalCondition', 'VWAPDistancePctCondition',
    'RelativeVolumePercentileCondition', 'TurnoverRatioMinCondition',
    'ATRPercentileFilterCondition', 'ATRExpansionBreakoutCondition',
    'NATRFilterCondition', 'DMIDirectionalCrossCondition',
    'IchimokuCloudBreakoutCondition', 'IchimokuTenkanKijunCrossCondition',

    # Quant Statistical Batch 7
    'ParabolicSARFlipCondition', 'LinearRegressionSlopeFilterCondition',
    'LinearRegressionAngleFilterCondition', 'LinearRegressionR2FilterCondition',
    'BetaToBenchmarkCondition', 'CorrelationToBenchmarkCondition',
    'SupportRetestSignalCondition', 'ResistanceRetestSignalCondition',
    'AnalystRevision1MCondition', 'AnalystRevision3MCondition',

    # Quant Fundamental Batch 8
    'ReceivablesTurnoverRatioCondition', 'InventoryTurnoverRatioCondition',
    'AssetTurnoverRatioCondition', 'CashflowToDebtRatioCondition',
    'PriceToTangibleBookCondition', 'EVToSalesRatioCondition',
    'EVToEbitdaRatioCondition', 'BookToMarketRatioCondition',
    'EPSCAGR3YCondition', 'EPSGrowthYoYCondition',

    # Quant Fundamental Batch 9
    'RevenueCAGR3YCondition', 'RevenueGrowthYoYCondition',
    'RevenueStabilityScoreCondition', 'EarningsStabilityScoreCondition',
    'DebtServiceCoverageRatioCondition', 'NetDebtToEbitdaCondition',
    'InterestCoverageRatioCondition', 'CashConversionRatioCondition',
    'ROCEFilterCondition', 'ROAFilterCondition',

    # Quant Shareholder Batch 10
    'NetMarginCondition', 'GrossMarginCondition', 'OperatingMarginCondition',
    'FreeCashFlowMarginCondition', 'PayoutRatioFilterCondition',
    'DividendGrowth5YCondition', 'ShareholderYieldFilterCondition',
    'NetShareIssuanceFilterCondition', 'BuybackYieldFilterCondition',
    'InsiderNetBuyingCondition',

    # Quant Special Batch 11
    'ShortFloatPctFilterCondition', 'ShortInterestRatioFilterCondition',
    'EarningsSurpriseFilterCondition', 'PostEarningsDriftCondition',
    'PreEarningsDriftCondition', 'AccrualsRatioCondition',
    'AssetGrowthRateCondition', 'GrossProfitabilityCondition',
    'QualityScoreCondition',

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
    'PiotroskiFScoreCondition', 'AltmanZScoreCondition', 'RoicCondition',
    'DsoTrendFilterCondition', 'clear_info_cache',

    # Registry
    'get_condition_class_map', 'get_condition_metadata', 'register_alias',
]
