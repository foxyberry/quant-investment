"""
Quant Fundamental Conditions Batch 9
team:quant 성장/안정성/수익성 지표 조건
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
    key="revenue_cagr_3y",
    label="Revenue CAGR 3Y",
    description="3-year revenue CAGR",
    category="fundamental",
    params=[{"name": "min_cagr_pct", "type": "float", "default": 5.0, "description": "Minimum CAGR %"}],
)
class RevenueCAGR3YCondition(BaseCondition):
    def __init__(self, min_cagr_pct: float = 5.0):
        self.min_cagr_pct = min_cagr_pct

    @property
    def name(self) -> str:
        return "revenue_cagr_3y"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        revenue_now = _last_value(data, "revenue_ttm")
        revenue_3y_ago = _last_value(data, "revenue_3y_ago")
        if revenue_now is None or revenue_3y_ago is None or revenue_3y_ago <= 0:
            return _insufficient(self.name)
        cagr = (math.pow(revenue_now / revenue_3y_ago, 1.0 / 3.0) - 1.0) * 100.0
        return ConditionResult(matched=cagr >= self.min_cagr_pct, condition_name=self.name, details={"cagr_pct": cagr})


@register_condition(
    key="revenue_growth_yoy",
    label="Revenue Growth YoY",
    description="Year-over-year revenue growth",
    category="fundamental",
    params=[{"name": "min_growth_pct", "type": "float", "default": 5.0, "description": "Minimum growth %"}],
)
class RevenueGrowthYoYCondition(BaseCondition):
    def __init__(self, min_growth_pct: float = 5.0):
        self.min_growth_pct = min_growth_pct

    @property
    def name(self) -> str:
        return "revenue_growth_yoy"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        revenue_now = _last_value(data, "revenue_ttm")
        revenue_prev = _last_value(data, "revenue_prev_year")
        if revenue_now is None or revenue_prev in (None, 0.0):
            return _insufficient(self.name)
        growth = ((revenue_now - revenue_prev) / abs(revenue_prev)) * 100.0
        return ConditionResult(matched=growth >= self.min_growth_pct, condition_name=self.name, details={"growth_pct": growth})


@register_condition(
    key="revenue_stability_score",
    label="Revenue Stability Score",
    description="Revenue stability based on coefficient of variation",
    category="fundamental",
    params=[
        {"name": "lookback_years", "type": "int", "default": 5, "description": "Years to evaluate"},
        {"name": "max_cv", "type": "float", "default": 0.25, "description": "Maximum coefficient of variation"},
    ],
)
class RevenueStabilityScoreCondition(BaseCondition):
    def __init__(self, lookback_years: int = 5, max_cv: float = 0.25):
        self.lookback_years = lookback_years
        self.max_cv = max_cv

    @property
    def name(self) -> str:
        return "revenue_stability_score"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        cols = [f"revenue_y{i}" for i in range(self.lookback_years)]
        if not all(col in data.columns for col in cols):
            return _insufficient(self.name)
        vals = pd.Series([data[col].iloc[-1] for col in cols], dtype=float)
        if vals.isna().any() or vals.mean() == 0:
            return _insufficient(self.name)
        cv = float(vals.std(ddof=0) / abs(vals.mean()))
        score = float(max(0.0, 1.0 - cv))
        return ConditionResult(matched=cv <= self.max_cv, condition_name=self.name, details={"cv": cv, "score": score})


@register_condition(
    key="earnings_stability_score",
    label="Earnings Stability Score",
    description="Earnings stability based on coefficient of variation",
    category="fundamental",
    params=[
        {"name": "lookback_years", "type": "int", "default": 5, "description": "Years to evaluate"},
        {"name": "max_cv", "type": "float", "default": 0.35, "description": "Maximum coefficient of variation"},
    ],
)
class EarningsStabilityScoreCondition(BaseCondition):
    def __init__(self, lookback_years: int = 5, max_cv: float = 0.35):
        self.lookback_years = lookback_years
        self.max_cv = max_cv

    @property
    def name(self) -> str:
        return "earnings_stability_score"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        cols = [f"net_income_y{i}" for i in range(self.lookback_years)]
        if not all(col in data.columns for col in cols):
            return _insufficient(self.name)
        vals = pd.Series([data[col].iloc[-1] for col in cols], dtype=float)
        if vals.isna().any() or vals.mean() == 0:
            return _insufficient(self.name)
        cv = float(vals.std(ddof=0) / abs(vals.mean()))
        score = float(max(0.0, 1.0 - cv))
        return ConditionResult(matched=cv <= self.max_cv, condition_name=self.name, details={"cv": cv, "score": score})


@register_condition(
    key="debt_service_coverage_ratio",
    label="Debt Service Coverage Ratio",
    description="Operating income over debt service",
    category="fundamental",
    params=[{"name": "min_ratio", "type": "float", "default": 1.2, "description": "Minimum DSCR"}],
)
class DebtServiceCoverageRatioCondition(BaseCondition):
    def __init__(self, min_ratio: float = 1.2):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "debt_service_coverage_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        op_income = _last_value(data, "operating_income_ttm")
        debt_service = _last_value(data, "debt_service_ttm")
        if op_income is None or debt_service in (None, 0.0):
            return _insufficient(self.name)
        ratio = op_income / debt_service
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="net_debt_to_ebitda",
    label="Net Debt to EBITDA",
    description="Net debt divided by EBITDA",
    category="fundamental",
    params=[{"name": "max_ratio", "type": "float", "default": 3.0, "description": "Maximum net debt/EBITDA"}],
)
class NetDebtToEbitdaCondition(BaseCondition):
    def __init__(self, max_ratio: float = 3.0):
        self.max_ratio = max_ratio

    @property
    def name(self) -> str:
        return "net_debt_to_ebitda"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        debt = _last_value(data, "total_debt")
        cash = _last_value(data, "cash_and_equivalents")
        ebitda = _last_value(data, "ebitda_ttm")
        if debt is None or cash is None or ebitda in (None, 0.0):
            return _insufficient(self.name)
        ratio = (debt - cash) / ebitda
        return ConditionResult(matched=ratio <= self.max_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="interest_coverage_ratio",
    label="Interest Coverage Ratio",
    description="EBIT over interest expense",
    category="fundamental",
    params=[{"name": "min_ratio", "type": "float", "default": 3.0, "description": "Minimum interest coverage"}],
)
class InterestCoverageRatioCondition(BaseCondition):
    def __init__(self, min_ratio: float = 3.0):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "interest_coverage_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        ebit = _last_value(data, "ebit_ttm")
        interest = _last_value(data, "interest_expense_ttm")
        if ebit is None or interest in (None, 0.0):
            return _insufficient(self.name)
        ratio = ebit / abs(interest)
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="cash_conversion_ratio",
    label="Cash Conversion Ratio",
    description="Operating cash flow over net income",
    category="fundamental",
    params=[{"name": "min_ratio", "type": "float", "default": 0.8, "description": "Minimum cash conversion ratio"}],
)
class CashConversionRatioCondition(BaseCondition):
    def __init__(self, min_ratio: float = 0.8):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "cash_conversion_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        cfo = _last_value(data, "operating_cash_flow_ttm")
        net_income = _last_value(data, "net_income_ttm")
        if cfo is None or net_income in (None, 0.0):
            return _insufficient(self.name)
        ratio = cfo / net_income
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="roce_filter",
    label="ROCE Filter",
    description="Return on capital employed",
    category="fundamental",
    params=[{"name": "min_roce_pct", "type": "float", "default": 10.0, "description": "Minimum ROCE %"}],
)
class ROCEFilterCondition(BaseCondition):
    def __init__(self, min_roce_pct: float = 10.0):
        self.min_roce_pct = min_roce_pct

    @property
    def name(self) -> str:
        return "roce_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        ebit = _last_value(data, "ebit_ttm")
        assets = _last_value(data, "total_assets")
        current_liabilities = _last_value(data, "current_liabilities")
        if ebit is None or assets is None or current_liabilities is None:
            return _insufficient(self.name)
        capital_employed = assets - current_liabilities
        if capital_employed == 0:
            return _insufficient(self.name)
        roce = (ebit / capital_employed) * 100.0
        return ConditionResult(matched=roce >= self.min_roce_pct, condition_name=self.name, details={"roce_pct": roce})


@register_condition(
    key="roa_filter",
    label="ROA Filter",
    description="Return on assets",
    category="fundamental",
    params=[{"name": "min_roa_pct", "type": "float", "default": 5.0, "description": "Minimum ROA %"}],
)
class ROAFilterCondition(BaseCondition):
    def __init__(self, min_roa_pct: float = 5.0):
        self.min_roa_pct = min_roa_pct

    @property
    def name(self) -> str:
        return "roa_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        net_income = _last_value(data, "net_income_ttm")
        assets = _last_value(data, "total_assets")
        if net_income is None or assets in (None, 0.0):
            return _insufficient(self.name)
        roa = (net_income / assets) * 100.0
        return ConditionResult(matched=roa >= self.min_roa_pct, condition_name=self.name, details={"roa_pct": roa})
