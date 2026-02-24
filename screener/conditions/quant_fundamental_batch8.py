"""
Quant Fundamental Conditions Batch 8
team:quant 재무/가치 지표 조건
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
    key="receivables_turnover_ratio",
    label="Receivables Turnover Ratio",
    description="Revenue to receivables turnover ratio",
    category="fundamental",
    params=[
        {"name": "min_ratio", "type": "float", "default": 4.0, "description": "Minimum receivables turnover"},
    ],
)
class ReceivablesTurnoverRatioCondition(BaseCondition):
    def __init__(self, min_ratio: float = 4.0):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "receivables_turnover_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        revenue = _last_value(data, "revenue_ttm")
        receivables = _last_value(data, "receivables")
        if revenue is None or receivables in (None, 0.0):
            return _insufficient(self.name)
        ratio = revenue / receivables
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="inventory_turnover_ratio",
    label="Inventory Turnover Ratio",
    description="COGS to inventory turnover ratio",
    category="fundamental",
    params=[
        {"name": "min_ratio", "type": "float", "default": 3.0, "description": "Minimum inventory turnover"},
    ],
)
class InventoryTurnoverRatioCondition(BaseCondition):
    def __init__(self, min_ratio: float = 3.0):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "inventory_turnover_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        cogs = _last_value(data, "cogs_ttm")
        inventory = _last_value(data, "inventory")
        if cogs is None or inventory in (None, 0.0):
            return _insufficient(self.name)
        ratio = cogs / inventory
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="asset_turnover_ratio",
    label="Asset Turnover Ratio",
    description="Revenue to total assets turnover ratio",
    category="fundamental",
    params=[
        {"name": "min_ratio", "type": "float", "default": 0.5, "description": "Minimum asset turnover"},
    ],
)
class AssetTurnoverRatioCondition(BaseCondition):
    def __init__(self, min_ratio: float = 0.5):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "asset_turnover_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        revenue = _last_value(data, "revenue_ttm")
        assets = _last_value(data, "total_assets")
        if revenue is None or assets in (None, 0.0):
            return _insufficient(self.name)
        ratio = revenue / assets
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="cashflow_to_debt_ratio",
    label="Cashflow to Debt Ratio",
    description="Operating cash flow to debt ratio",
    category="fundamental",
    params=[
        {"name": "min_ratio", "type": "float", "default": 0.2, "description": "Minimum cashflow/debt ratio"},
    ],
)
class CashflowToDebtRatioCondition(BaseCondition):
    def __init__(self, min_ratio: float = 0.2):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "cashflow_to_debt_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        cfo = _last_value(data, "operating_cash_flow_ttm")
        debt = _last_value(data, "total_debt")
        if cfo is None or debt in (None, 0.0):
            return _insufficient(self.name)
        ratio = cfo / debt
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="price_to_tangible_book",
    label="Price to Tangible Book",
    description="Market cap to tangible book ratio",
    category="fundamental",
    params=[
        {"name": "max_ratio", "type": "float", "default": 3.0, "description": "Maximum P/TB"},
    ],
)
class PriceToTangibleBookCondition(BaseCondition):
    def __init__(self, max_ratio: float = 3.0):
        self.max_ratio = max_ratio

    @property
    def name(self) -> str:
        return "price_to_tangible_book"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        market_cap = _last_value(data, "market_cap")
        tangible_book = _last_value(data, "tangible_book_value")
        if market_cap is None or tangible_book in (None, 0.0):
            return _insufficient(self.name)
        ratio = market_cap / tangible_book
        return ConditionResult(matched=ratio <= self.max_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="ev_to_sales_ratio",
    label="EV to Sales Ratio",
    description="Enterprise value to sales ratio",
    category="fundamental",
    params=[
        {"name": "max_ratio", "type": "float", "default": 4.0, "description": "Maximum EV/Sales"},
    ],
)
class EVToSalesRatioCondition(BaseCondition):
    def __init__(self, max_ratio: float = 4.0):
        self.max_ratio = max_ratio

    @property
    def name(self) -> str:
        return "ev_to_sales_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        ev = _last_value(data, "enterprise_value")
        sales = _last_value(data, "revenue_ttm")
        if ev is None or sales in (None, 0.0):
            return _insufficient(self.name)
        ratio = ev / sales
        return ConditionResult(matched=ratio <= self.max_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="ev_to_ebitda_ratio",
    label="EV to EBITDA Ratio",
    description="Enterprise value to EBITDA ratio",
    category="fundamental",
    params=[
        {"name": "max_ratio", "type": "float", "default": 12.0, "description": "Maximum EV/EBITDA"},
    ],
)
class EVToEbitdaRatioCondition(BaseCondition):
    def __init__(self, max_ratio: float = 12.0):
        self.max_ratio = max_ratio

    @property
    def name(self) -> str:
        return "ev_to_ebitda_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        ev = _last_value(data, "enterprise_value")
        ebitda = _last_value(data, "ebitda_ttm")
        if ev is None or ebitda in (None, 0.0):
            return _insufficient(self.name)
        ratio = ev / ebitda
        return ConditionResult(matched=ratio <= self.max_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="book_to_market_ratio",
    label="Book to Market Ratio",
    description="Book value divided by market cap",
    category="fundamental",
    params=[
        {"name": "min_ratio", "type": "float", "default": 0.3, "description": "Minimum B/M ratio"},
    ],
)
class BookToMarketRatioCondition(BaseCondition):
    def __init__(self, min_ratio: float = 0.3):
        self.min_ratio = min_ratio

    @property
    def name(self) -> str:
        return "book_to_market_ratio"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        book = _last_value(data, "book_value")
        market_cap = _last_value(data, "market_cap")
        if book is None or market_cap in (None, 0.0):
            return _insufficient(self.name)
        ratio = book / market_cap
        return ConditionResult(matched=ratio >= self.min_ratio, condition_name=self.name, details={"ratio": ratio})


@register_condition(
    key="eps_cagr_3y",
    label="EPS CAGR 3Y",
    description="3-year EPS CAGR",
    category="fundamental",
    params=[
        {"name": "min_cagr_pct", "type": "float", "default": 5.0, "description": "Minimum CAGR %"},
    ],
)
class EPSCAGR3YCondition(BaseCondition):
    def __init__(self, min_cagr_pct: float = 5.0):
        self.min_cagr_pct = min_cagr_pct

    @property
    def name(self) -> str:
        return "eps_cagr_3y"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        eps_now = _last_value(data, "eps_ttm")
        eps_3y_ago = _last_value(data, "eps_3y_ago")
        if eps_now is None or eps_3y_ago is None or eps_3y_ago <= 0 or eps_now <= 0:
            return _insufficient(self.name)
        cagr = (math.pow(eps_now / eps_3y_ago, 1.0 / 3.0) - 1.0) * 100.0
        return ConditionResult(matched=cagr >= self.min_cagr_pct, condition_name=self.name, details={"cagr_pct": cagr})


@register_condition(
    key="eps_growth_yoy",
    label="EPS Growth YoY",
    description="Year-over-year EPS growth",
    category="fundamental",
    params=[
        {"name": "min_growth_pct", "type": "float", "default": 5.0, "description": "Minimum YoY growth %"},
    ],
)
class EPSGrowthYoYCondition(BaseCondition):
    def __init__(self, min_growth_pct: float = 5.0):
        self.min_growth_pct = min_growth_pct

    @property
    def name(self) -> str:
        return "eps_growth_yoy"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        eps_now = _last_value(data, "eps_ttm")
        eps_prev = _last_value(data, "eps_prev_year")
        if eps_now is None or eps_prev is None or eps_prev == 0:
            return _insufficient(self.name)
        growth = ((eps_now - eps_prev) / abs(eps_prev)) * 100.0
        return ConditionResult(matched=growth >= self.min_growth_pct, condition_name=self.name, details={"growth_pct": growth})
