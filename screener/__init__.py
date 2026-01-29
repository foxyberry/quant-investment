# screener/__init__.py

from .base import SmartStockScreener
from .basic_filter import BasicInfoScreener
from .technical_filter import TechnicalScreener
from .external_filter import ExternalScreener
from .screening_criteria import ScreeningCriteria
from .kospi_fetcher import KospiListFetcher

# New extensible screening system
from .stock_screener import StockScreener, ScreeningResult
from .presets import get_preset, list_presets, PRESET_REGISTRY

# Condition classes
from .conditions import (
    # Base
    BaseCondition, ConditionResult, ConditionError,
    # Price
    MinPriceCondition, MaxPriceCondition, PriceRangeCondition, PriceChangeCondition,
    # Volume
    MinVolumeCondition, VolumeAboveAvgCondition, VolumeSpikeCondition,
    # MA
    MATouchCondition, AboveMACondition, BelowMACondition,
    MACrossUpCondition, MACrossDownCondition,
    # RSI
    RSIOversoldCondition, RSIOverboughtCondition, RSIRangeCondition,
    # Composite
    AndCondition, OrCondition, NotCondition,
)

__all__ = [
    # Legacy
    "SmartStockScreener",
    "BasicInfoScreener",
    "TechnicalScreener",
    "ExternalScreener",
    "ScreeningCriteria",
    "KospiListFetcher",

    # New extensible system
    "StockScreener",
    "ScreeningResult",
    "get_preset",
    "list_presets",
    "PRESET_REGISTRY",

    # Conditions
    "BaseCondition", "ConditionResult", "ConditionError",
    "MinPriceCondition", "MaxPriceCondition", "PriceRangeCondition", "PriceChangeCondition",
    "MinVolumeCondition", "VolumeAboveAvgCondition", "VolumeSpikeCondition",
    "MATouchCondition", "AboveMACondition", "BelowMACondition",
    "MACrossUpCondition", "MACrossDownCondition",
    "RSIOversoldCondition", "RSIOverboughtCondition", "RSIRangeCondition",
    "AndCondition", "OrCondition", "NotCondition",
]
