"""
Quant Shareholder/Margin Conditions Batch 10
team:quant 마진/주주환원 지표 조건
"""

from __future__ import annotations

import math

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
    key="net_margin",
    label="Net Margin",
    description="Net income margin",
    category="fundamental",
    params=[{"name": "min_margin_pct", "type": "float", "default": 5.0, "description": "Minimum net margin %"}],
)
class NetMarginCondition(BaseCondition):
    def __init__(self, min_margin_pct: float = 5.0):
        self.min_margin_pct = min_margin_pct

    @property
    def name(self) -> str:
        return "net_margin"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        net_income = _last_value(data, "net_income_ttm")
        revenue = _last_value(data, "revenue_ttm")
        if net_income is None or revenue in (None, 0.0):
            return _insufficient(self.name)
        margin = (net_income / revenue) * 100.0
        return ConditionResult(matched=margin >= self.min_margin_pct, condition_name=self.name, details={"margin_pct": margin})


@register_condition(
    key="gross_margin",
    label="Gross Margin",
    description="Gross profit margin",
    category="fundamental",
    params=[{"name": "min_margin_pct", "type": "float", "default": 20.0, "description": "Minimum gross margin %"}],
)
class GrossMarginCondition(BaseCondition):
    def __init__(self, min_margin_pct: float = 20.0):
        self.min_margin_pct = min_margin_pct

    @property
    def name(self) -> str:
        return "gross_margin"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        gross_profit = _last_value(data, "gross_profit_ttm")
        revenue = _last_value(data, "revenue_ttm")
        if gross_profit is None or revenue in (None, 0.0):
            return _insufficient(self.name)
        margin = (gross_profit / revenue) * 100.0
        return ConditionResult(matched=margin >= self.min_margin_pct, condition_name=self.name, details={"margin_pct": margin})


@register_condition(
    key="operating_margin",
    label="Operating Margin",
    description="Operating income margin",
    category="fundamental",
    params=[{"name": "min_margin_pct", "type": "float", "default": 10.0, "description": "Minimum operating margin %"}],
)
class OperatingMarginCondition(BaseCondition):
    def __init__(self, min_margin_pct: float = 10.0):
        self.min_margin_pct = min_margin_pct

    @property
    def name(self) -> str:
        return "operating_margin"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        op_income = _last_value(data, "operating_income_ttm")
        revenue = _last_value(data, "revenue_ttm")
        if op_income is None or revenue in (None, 0.0):
            return _insufficient(self.name)
        margin = (op_income / revenue) * 100.0
        return ConditionResult(matched=margin >= self.min_margin_pct, condition_name=self.name, details={"margin_pct": margin})


@register_condition(
    key="free_cash_flow_margin",
    label="Free Cash Flow Margin",
    description="Free cash flow margin",
    category="fundamental",
    params=[{"name": "min_margin_pct", "type": "float", "default": 5.0, "description": "Minimum FCF margin %"}],
)
class FreeCashFlowMarginCondition(BaseCondition):
    def __init__(self, min_margin_pct: float = 5.0):
        self.min_margin_pct = min_margin_pct

    @property
    def name(self) -> str:
        return "free_cash_flow_margin"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        fcf = _last_value(data, "free_cash_flow_ttm")
        revenue = _last_value(data, "revenue_ttm")
        if fcf is None or revenue in (None, 0.0):
            return _insufficient(self.name)
        margin = (fcf / revenue) * 100.0
        return ConditionResult(matched=margin >= self.min_margin_pct, condition_name=self.name, details={"margin_pct": margin})


@register_condition(
    key="payout_ratio_filter",
    label="Payout Ratio Filter",
    description="Dividend payout ratio",
    category="fundamental",
    params=[{"name": "max_payout_pct", "type": "float", "default": 70.0, "description": "Maximum payout ratio %"}],
)
class PayoutRatioFilterCondition(BaseCondition):
    def __init__(self, max_payout_pct: float = 70.0):
        self.max_payout_pct = max_payout_pct

    @property
    def name(self) -> str:
        return "payout_ratio_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        dividends = _last_value(data, "dividends_paid_ttm")
        net_income = _last_value(data, "net_income_ttm")
        if dividends is None or net_income in (None, 0.0):
            return _insufficient(self.name)
        payout = (abs(dividends) / abs(net_income)) * 100.0
        return ConditionResult(matched=payout <= self.max_payout_pct, condition_name=self.name, details={"payout_pct": payout})


@register_condition(
    key="dividend_growth_5y",
    label="Dividend Growth 5Y",
    description="5-year dividend CAGR",
    category="fundamental",
    params=[{"name": "min_growth_pct", "type": "float", "default": 3.0, "description": "Minimum dividend growth %"}],
)
class DividendGrowth5YCondition(BaseCondition):
    def __init__(self, min_growth_pct: float = 3.0):
        self.min_growth_pct = min_growth_pct

    @property
    def name(self) -> str:
        return "dividend_growth_5y"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        dps_now = _last_value(data, "dividend_per_share_ttm")
        dps_5y_ago = _last_value(data, "dividend_per_share_5y_ago")
        if dps_now is None or dps_5y_ago is None or dps_5y_ago <= 0:
            return _insufficient(self.name)
        growth = (math.pow(dps_now / dps_5y_ago, 1.0 / 5.0) - 1.0) * 100.0
        return ConditionResult(matched=growth >= self.min_growth_pct, condition_name=self.name, details={"growth_pct": growth})


@register_condition(
    key="shareholder_yield_filter",
    label="Shareholder Yield Filter",
    description="Dividend + buyback - issuance yield",
    category="fundamental",
    params=[{"name": "min_yield_pct", "type": "float", "default": 2.0, "description": "Minimum shareholder yield %"}],
)
class ShareholderYieldFilterCondition(BaseCondition):
    def __init__(self, min_yield_pct: float = 2.0):
        self.min_yield_pct = min_yield_pct

    @property
    def name(self) -> str:
        return "shareholder_yield_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        div_yield = _last_value(data, "dividend_yield_pct")
        buyback_yield = _last_value(data, "buyback_yield_pct")
        issuance = _last_value(data, "net_share_issuance_pct")
        if div_yield is None or buyback_yield is None or issuance is None:
            return _insufficient(self.name)
        total_yield = div_yield + buyback_yield - issuance
        return ConditionResult(matched=total_yield >= self.min_yield_pct, condition_name=self.name, details={"shareholder_yield_pct": total_yield})


@register_condition(
    key="net_share_issuance_filter",
    label="Net Share Issuance Filter",
    description="Limit net share issuance",
    category="fundamental",
    params=[{"name": "max_issuance_pct", "type": "float", "default": 1.0, "description": "Maximum net issuance %"}],
)
class NetShareIssuanceFilterCondition(BaseCondition):
    def __init__(self, max_issuance_pct: float = 1.0):
        self.max_issuance_pct = max_issuance_pct

    @property
    def name(self) -> str:
        return "net_share_issuance_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        issuance = _last_value(data, "net_share_issuance_pct")
        if issuance is None:
            return _insufficient(self.name)
        return ConditionResult(matched=issuance <= self.max_issuance_pct, condition_name=self.name, details={"issuance_pct": issuance})


@register_condition(
    key="buyback_yield_filter",
    label="Buyback Yield Filter",
    description="Minimum buyback yield",
    category="fundamental",
    params=[{"name": "min_yield_pct", "type": "float", "default": 1.0, "description": "Minimum buyback yield %"}],
)
class BuybackYieldFilterCondition(BaseCondition):
    def __init__(self, min_yield_pct: float = 1.0):
        self.min_yield_pct = min_yield_pct

    @property
    def name(self) -> str:
        return "buyback_yield_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        buyback_yield = _last_value(data, "buyback_yield_pct")
        if buyback_yield is None:
            return _insufficient(self.name)
        return ConditionResult(matched=buyback_yield >= self.min_yield_pct, condition_name=self.name, details={"buyback_yield_pct": buyback_yield})


@register_condition(
    key="insider_net_buying",
    label="Insider Net Buying",
    description="Insider net buying ratio",
    category="fundamental",
    params=[{"name": "min_net_buying_pct", "type": "float", "default": 0.0, "description": "Minimum insider net buying %"}],
)
class InsiderNetBuyingCondition(BaseCondition):
    def __init__(self, min_net_buying_pct: float = 0.0):
        self.min_net_buying_pct = min_net_buying_pct

    @property
    def name(self) -> str:
        return "insider_net_buying"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        net_buying = _last_value(data, "insider_net_buying_pct")
        if net_buying is None:
            return _insufficient(self.name)
        return ConditionResult(matched=net_buying >= self.min_net_buying_pct, condition_name=self.name, details={"net_buying_pct": net_buying})
