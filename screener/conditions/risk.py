"""
Risk & Performance Conditions
리스크/성과 기반 스크리닝 조건
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


def _insufficient(name: str) -> ConditionResult:
    return ConditionResult(matched=False, condition_name=name, details={"error": "Insufficient data"})


def _returns(close: pd.Series) -> pd.Series:
    return close.pct_change().dropna()


@register_condition(
    key="downside_volatility_filter",
    label="Downside Volatility",
    description="Annualized downside volatility filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "max_downside_vol_pct", "type": "float", "default": 20.0, "description": "Max downside volatility %"},
    ],
)
class DownsideVolatilityFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, max_downside_vol_pct: float = 20.0):
        self.lookback_days = lookback_days
        self.max_downside_vol_pct = max_downside_vol_pct

    @property
    def name(self) -> str:
        return "downside_volatility_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        r = _returns(data["close"]).tail(self.lookback_days)
        downside = r[r < 0]
        if len(downside) == 0:
            downside_vol = 0.0
        else:
            downside_vol = float(downside.std(ddof=0) * np.sqrt(252) * 100)
        return ConditionResult(
            matched=downside_vol <= self.max_downside_vol_pct,
            condition_name=self.name,
            details={"downside_vol_pct": downside_vol, "max_downside_vol_pct": self.max_downside_vol_pct},
        )


@register_condition(
    key="semivariance_filter",
    label="Semivariance",
    description="Downside semivariance filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "max_semivariance", "type": "float", "default": 0.0004, "description": "Max semivariance"},
    ],
)
class SemivarianceFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, max_semivariance: float = 0.0004):
        self.lookback_days = lookback_days
        self.max_semivariance = max_semivariance

    @property
    def name(self) -> str:
        return "semivariance_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        r = _returns(data["close"]).tail(self.lookback_days)
        downside = np.minimum(r, 0)
        semivariance = float(np.mean(np.square(downside)))
        return ConditionResult(
            matched=semivariance <= self.max_semivariance,
            condition_name=self.name,
            details={"semivariance": semivariance, "max_semivariance": self.max_semivariance},
        )


@register_condition(
    key="rolling_sharpe_filter",
    label="Rolling Sharpe",
    description="Rolling Sharpe ratio filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "min_sharpe", "type": "float", "default": 1.0, "description": "Minimum Sharpe"},
    ],
)
class RollingSharpeFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, min_sharpe: float = 1.0):
        self.lookback_days = lookback_days
        self.min_sharpe = min_sharpe

    @property
    def name(self) -> str:
        return "rolling_sharpe_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        r = _returns(data["close"]).tail(self.lookback_days)
        std = r.std(ddof=0)
        sharpe = 0.0 if std == 0 else float((r.mean() / std) * np.sqrt(252))
        return ConditionResult(matched=sharpe >= self.min_sharpe, condition_name=self.name, details={"sharpe": sharpe})


@register_condition(
    key="rolling_sortino_filter",
    label="Rolling Sortino",
    description="Rolling Sortino ratio filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "min_sortino", "type": "float", "default": 1.0, "description": "Minimum Sortino"},
    ],
)
class RollingSortinoFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, min_sortino: float = 1.0):
        self.lookback_days = lookback_days
        self.min_sortino = min_sortino

    @property
    def name(self) -> str:
        return "rolling_sortino_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        r = _returns(data["close"]).tail(self.lookback_days)
        downside = r[r < 0]
        downside_std = downside.std(ddof=0)
        sortino = 0.0 if (pd.isna(downside_std) or downside_std == 0) else float((r.mean() / downside_std) * np.sqrt(252))
        return ConditionResult(matched=sortino >= self.min_sortino, condition_name=self.name, details={"sortino": sortino})


@register_condition(
    key="ulcer_index_filter",
    label="Ulcer Index",
    description="Ulcer index filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "max_ulcer_index", "type": "float", "default": 10.0, "description": "Max Ulcer Index"},
    ],
)
class UlcerIndexFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, max_ulcer_index: float = 10.0):
        self.lookback_days = lookback_days
        self.max_ulcer_index = max_ulcer_index

    @property
    def name(self) -> str:
        return "ulcer_index_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        close = data["close"].tail(self.lookback_days)
        rolling_peak = close.cummax()
        drawdown_pct = (close / rolling_peak - 1.0) * 100
        ulcer = float(np.sqrt(np.mean(np.square(drawdown_pct))))
        return ConditionResult(matched=ulcer <= self.max_ulcer_index, condition_name=self.name, details={"ulcer_index": ulcer})


@register_condition(
    key="calmar_ratio_filter",
    label="Calmar Ratio",
    description="Calmar ratio filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 252, "description": "Lookback days"},
        {"name": "min_calmar", "type": "float", "default": 0.5, "description": "Minimum Calmar"},
    ],
)
class CalmarRatioFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 252, min_calmar: float = 0.5):
        self.lookback_days = lookback_days
        self.min_calmar = min_calmar

    @property
    def name(self) -> str:
        return "calmar_ratio_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        close = data["close"].tail(self.lookback_days)
        total_return = close.iloc[-1] / close.iloc[0] - 1.0
        ann_return = float((1.0 + total_return) ** (252 / max(1, len(close) - 1)) - 1.0)
        rolling_peak = close.cummax()
        max_dd = float(abs((close / rolling_peak - 1.0).min()))
        calmar = 0.0 if max_dd == 0 else ann_return / max_dd
        return ConditionResult(matched=calmar >= self.min_calmar, condition_name=self.name, details={"calmar": calmar})


@register_condition(
    key="max_drawdown_window_filter",
    label="Max Drawdown Window",
    description="Window max drawdown filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 120, "description": "Lookback days"},
        {"name": "max_drawdown_pct", "type": "float", "default": 20.0, "description": "Maximum drawdown %"},
    ],
)
class MaxDrawdownWindowFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 120, max_drawdown_pct: float = 20.0):
        self.lookback_days = lookback_days
        self.max_drawdown_pct = max_drawdown_pct

    @property
    def name(self) -> str:
        return "max_drawdown_window_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        close = data["close"].tail(self.lookback_days)
        dd = (close / close.cummax() - 1.0) * 100
        max_drawdown_pct = float(abs(dd.min()))
        return ConditionResult(
            matched=max_drawdown_pct <= self.max_drawdown_pct,
            condition_name=self.name,
            details={"max_drawdown_pct": max_drawdown_pct, "threshold": self.max_drawdown_pct},
        )


@register_condition(
    key="return_skewness_filter",
    label="Return Skewness",
    description="Return skewness filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "min_skewness", "type": "float", "default": -1.0, "description": "Minimum skewness"},
    ],
)
class ReturnSkewnessFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, min_skewness: float = -1.0):
        self.lookback_days = lookback_days
        self.min_skewness = min_skewness

    @property
    def name(self) -> str:
        return "return_skewness_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        skew = float(_returns(data["close"]).tail(self.lookback_days).skew())
        return ConditionResult(matched=skew >= self.min_skewness, condition_name=self.name, details={"skewness": skew})


@register_condition(
    key="return_kurtosis_filter",
    label="Return Kurtosis",
    description="Return kurtosis filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "max_kurtosis", "type": "float", "default": 10.0, "description": "Maximum kurtosis"},
    ],
)
class ReturnKurtosisFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, max_kurtosis: float = 10.0):
        self.lookback_days = lookback_days
        self.max_kurtosis = max_kurtosis

    @property
    def name(self) -> str:
        return "return_kurtosis_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        kurt = float(_returns(data["close"]).tail(self.lookback_days).kurt())
        return ConditionResult(matched=kurt <= self.max_kurtosis, condition_name=self.name, details={"kurtosis": kurt})


@register_condition(
    key="intraday_return_filter",
    label="Intraday Return",
    description="Intraday return filter",
    category="risk",
    params=[
        {"name": "min_intraday_return_pct", "type": "float", "default": 0.0, "description": "Minimum intraday return %"},
    ],
)
class IntradayReturnFilterCondition(BaseCondition):
    def __init__(self, min_intraday_return_pct: float = 0.0):
        self.min_intraday_return_pct = min_intraday_return_pct

    @property
    def name(self) -> str:
        return "intraday_return_filter"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 1 or "open" not in data.columns:
            return _insufficient(self.name)
        o = data["open"].iloc[-1]
        c = data["close"].iloc[-1]
        if pd.isna(o) or pd.isna(c) or o == 0:
            return _insufficient(self.name)
        intraday_pct = float(((c - o) / o) * 100.0)
        return ConditionResult(
            matched=intraday_pct >= self.min_intraday_return_pct,
            condition_name=self.name,
            details={"intraday_return_pct": intraday_pct, "threshold": self.min_intraday_return_pct},
        )
