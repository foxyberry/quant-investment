"""
Quant Special Conditions Batch 11
team:quant 남은 특수 지표 조건
"""

from __future__ import annotations

import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


def _insufficient(name: str) -> ConditionResult:
    return ConditionResult(matched=False, condition_name=name, details={"error": "Insufficient data"})


def _last_value(data: pd.DataFrame, col: str) -> float | None:
    if col not in data.columns or len(data) < 1:
        return None
    v = data[col].iloc[-1]
    if pd.isna(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@register_condition(
    key="short_float_pct_filter",
    label="Short Float % Filter",
    description="Short float percentage threshold",
    category="sentiment",
    params=[{"name": "max_short_float_pct", "type": "float", "default": 15.0, "description": "Maximum short float %"}],
)
class ShortFloatPctFilterCondition(BaseCondition):
    def __init__(self, max_short_float_pct: float = 15.0):
        self.max_short_float_pct = max_short_float_pct

    @property
    def name(self) -> str:
        return "short_float_pct_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        short_float = _last_value(data, "short_float_pct")
        if short_float is None:
            return _insufficient(self.name)
        return ConditionResult(matched=short_float <= self.max_short_float_pct, condition_name=self.name, details={"short_float_pct": short_float})


@register_condition(
    key="short_interest_ratio_filter",
    label="Short Interest Ratio Filter",
    description="Days-to-cover threshold",
    category="sentiment",
    params=[{"name": "max_ratio", "type": "float", "default": 5.0, "description": "Maximum short interest ratio"}],
)
class ShortInterestRatioFilterCondition(BaseCondition):
    def __init__(self, max_ratio: float = 5.0):
        self.max_ratio = max_ratio

    @property
    def name(self) -> str:
        return "short_interest_ratio_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        ratio = _last_value(data, "short_interest_ratio")
        if ratio is None:
            return _insufficient(self.name)
        return ConditionResult(matched=ratio <= self.max_ratio, condition_name=self.name, details={"short_interest_ratio": ratio})


@register_condition(
    key="earnings_surprise_filter",
    label="Earnings Surprise Filter",
    description="Quarterly earnings surprise threshold",
    category="event",
    params=[{"name": "min_surprise_pct", "type": "float", "default": 0.0, "description": "Minimum surprise %"}],
)
class EarningsSurpriseFilterCondition(BaseCondition):
    def __init__(self, min_surprise_pct: float = 0.0):
        self.min_surprise_pct = min_surprise_pct

    @property
    def name(self) -> str:
        return "earnings_surprise_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        surprise = _last_value(data, "earnings_surprise_pct")
        if surprise is None:
            return _insufficient(self.name)
        return ConditionResult(matched=surprise >= self.min_surprise_pct, condition_name=self.name, details={"surprise_pct": surprise})


@register_condition(
    key="post_earnings_drift",
    label="Post Earnings Drift",
    description="Post-earnings drift threshold",
    category="event",
    params=[{"name": "min_return_pct", "type": "float", "default": 0.0, "description": "Minimum post-earnings return %"}],
)
class PostEarningsDriftCondition(BaseCondition):
    def __init__(self, min_return_pct: float = 0.0):
        self.min_return_pct = min_return_pct

    @property
    def name(self) -> str:
        return "post_earnings_drift"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        drift = _last_value(data, "post_earnings_return_pct")
        if drift is None:
            return _insufficient(self.name)
        return ConditionResult(matched=drift >= self.min_return_pct, condition_name=self.name, details={"return_pct": drift})


@register_condition(
    key="pre_earnings_drift",
    label="Pre Earnings Drift",
    description="Pre-earnings drift threshold",
    category="event",
    params=[{"name": "min_return_pct", "type": "float", "default": 0.0, "description": "Minimum pre-earnings return %"}],
)
class PreEarningsDriftCondition(BaseCondition):
    def __init__(self, min_return_pct: float = 0.0):
        self.min_return_pct = min_return_pct

    @property
    def name(self) -> str:
        return "pre_earnings_drift"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        drift = _last_value(data, "pre_earnings_return_pct")
        if drift is None:
            return _insufficient(self.name)
        return ConditionResult(matched=drift >= self.min_return_pct, condition_name=self.name, details={"return_pct": drift})


@register_condition(
    key="accruals_ratio",
    label="Accruals Ratio",
    description="Accruals ratio from income and cash flow",
    category="quality",
    params=[{"name": "max_ratio", "type": "float", "default": 0.1, "description": "Maximum accruals ratio"}],
)
class AccrualsRatioCondition(BaseCondition):
    def __init__(self, max_ratio: float = 0.1):
        self.max_ratio = max_ratio

    @property
    def name(self) -> str:
        return "accruals_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        net_income = _last_value(data, "net_income_ttm")
        cfo = _last_value(data, "operating_cash_flow_ttm")
        assets = _last_value(data, "total_assets")
        if net_income is None or cfo is None or assets in (None, 0.0):
            return _insufficient(self.name)
        ratio = (net_income - cfo) / assets
        return ConditionResult(matched=ratio <= self.max_ratio, condition_name=self.name, details={"accruals_ratio": ratio})


@register_condition(
    key="asset_growth_rate",
    label="Asset Growth Rate",
    description="Total asset growth rate",
    category="quality",
    params=[{"name": "max_growth_pct", "type": "float", "default": 15.0, "description": "Maximum asset growth %"}],
)
class AssetGrowthRateCondition(BaseCondition):
    def __init__(self, max_growth_pct: float = 15.0):
        self.max_growth_pct = max_growth_pct

    @property
    def name(self) -> str:
        return "asset_growth_rate"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        assets_now = _last_value(data, "total_assets")
        assets_prev = _last_value(data, "total_assets_prev_year")
        if assets_now is None or assets_prev in (None, 0.0):
            return _insufficient(self.name)
        growth = ((assets_now - assets_prev) / abs(assets_prev)) * 100.0
        return ConditionResult(matched=growth <= self.max_growth_pct, condition_name=self.name, details={"growth_pct": growth})


@register_condition(
    key="gross_profitability",
    label="Gross Profitability",
    description="Gross profit to total assets",
    category="quality",
    params=[{"name": "min_ratio", "type": "float", "default": 0.2, "description": "Minimum gross profitability"}],
)
class GrossProfitabilityCondition(BaseCondition):
    def __init__(self, min_ratio: float = 0.2):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "gross_profitability"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        gross_profit = _last_value(data, "gross_profit_ttm")
        assets = _last_value(data, "total_assets")
        if gross_profit is None or assets in (None, 0.0):
            return _insufficient(self.name)
        ratio = gross_profit / assets
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="quality_score",
    label="Quality Score",
    description="Composite quality score from ROA, gross profitability and accruals",
    category="quality",
    params=[{"name": "min_score", "type": "float", "default": 0.5, "description": "Minimum quality score"}],
)
class QualityScoreCondition(BaseCondition):
    def __init__(self, min_score: float = 0.5):
        self.min_score = min_score

    @property
    def name(self) -> str:
        return "quality_score"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        net_income = _last_value(data, "net_income_ttm")
        gross_profit = _last_value(data, "gross_profit_ttm")
        cfo = _last_value(data, "operating_cash_flow_ttm")
        assets = _last_value(data, "total_assets")
        if net_income is None or gross_profit is None or cfo is None or assets in (None, 0.0):
            return _insufficient(self.name)
        roa = net_income / assets
        gross_prof = gross_profit / assets
        accrual = (net_income - cfo) / assets
        score = (roa + gross_prof - accrual)
        return ConditionResult(matched=score >= self.min_score, condition_name=self.name, details={"score": score})
