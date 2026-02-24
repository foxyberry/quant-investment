"""
Quant Statistical/Structure Conditions Batch 7
team:quant 통계/구조 기반 조건
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


def _insufficient(name: str) -> ConditionResult:
    return ConditionResult(matched=False, condition_name=name, details={"error": "Insufficient data"})


def _regression_metrics(series: pd.Series, lookback_days: int) -> tuple[float, float, float] | None:
    if len(series) < lookback_days:
        return None
    y = series.tail(lookback_days).astype(float).values
    if np.isnan(y).any():
        return None
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    angle = float(np.degrees(np.arctan(slope)))
    return float(slope), angle, float(r2)


def _parabolic_sar(data: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    high = data["high"].astype(float).values
    low = data["low"].astype(float).values
    close = data["close"].astype(float).values
    n = len(data)
    if n < 2:
        return pd.Series(np.full(n, np.nan), index=data.index)

    sar = np.zeros(n, dtype=float)
    bull = close[1] >= close[0]
    ep = high[0] if bull else low[0]
    af = af_step
    sar[0] = low[0] if bull else high[0]

    for i in range(1, n):
        prev = sar[i - 1]
        sar_i = prev + af * (ep - prev)

        if bull:
            sar_i = min(sar_i, low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if low[i] < sar_i:
                bull = False
                sar_i = ep
                ep = low[i]
                af = af_step
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            sar_i = max(sar_i, high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if high[i] > sar_i:
                bull = True
                sar_i = ep
                ep = high[i]
                af = af_step
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

        sar[i] = sar_i

    return pd.Series(sar, index=data.index)


@register_condition(
    key="parabolic_sar_flip",
    label="Parabolic SAR Flip",
    description="Bullish SAR flip within lookback",
    category="momentum",
    params=[
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
        {"name": "af_step", "type": "float", "default": 0.02, "description": "SAR acceleration step"},
        {"name": "af_max", "type": "float", "default": 0.2, "description": "SAR acceleration max"},
    ],
)
class ParabolicSARFlipCondition(BaseCondition):
    def __init__(self, lookback_days: int = 5, af_step: float = 0.02, af_max: float = 0.2):
        self.lookback_days = lookback_days
        self.af_step = af_step
        self.af_max = af_max

    @property
    def name(self) -> str:
        return "parabolic_sar_flip"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        sar = _parabolic_sar(data, self.af_step, self.af_max)
        close = data["close"]
        flip_day = None
        for i in range(1, self.lookback_days + 1):
            prev_close, prev_sar = close.iloc[-(i + 1)], sar.iloc[-(i + 1)]
            curr_close, curr_sar = close.iloc[-i], sar.iloc[-i]
            if any(pd.isna(v) for v in [prev_close, prev_sar, curr_close, curr_sar]):
                continue
            if prev_close <= prev_sar and curr_close > curr_sar:
                flip_day = i
                break
        return ConditionResult(matched=flip_day is not None, condition_name=self.name, details={"flip_day": flip_day})


@register_condition(
    key="linear_regression_slope_filter",
    label="Linear Regression Slope",
    description="Linear regression slope threshold",
    category="momentum",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "min_slope", "type": "float", "default": 0.0, "description": "Minimum slope"},
    ],
)
class LinearRegressionSlopeFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, min_slope: float = 0.0):
        self.lookback_days = lookback_days
        self.min_slope = min_slope

    @property
    def name(self) -> str:
        return "linear_regression_slope_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        m = _regression_metrics(data["close"], self.lookback_days)
        if m is None:
            return _insufficient(self.name)
        slope, _, _ = m
        return ConditionResult(matched=slope >= self.min_slope, condition_name=self.name, details={"slope": slope})


@register_condition(
    key="linear_regression_angle_filter",
    label="Linear Regression Angle",
    description="Linear regression angle threshold",
    category="momentum",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "min_angle_deg", "type": "float", "default": 0.0, "description": "Minimum angle (deg)"},
    ],
)
class LinearRegressionAngleFilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, min_angle_deg: float = 0.0):
        self.lookback_days = lookback_days
        self.min_angle_deg = min_angle_deg

    @property
    def name(self) -> str:
        return "linear_regression_angle_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        m = _regression_metrics(data["close"], self.lookback_days)
        if m is None:
            return _insufficient(self.name)
        _, angle, _ = m
        return ConditionResult(matched=angle >= self.min_angle_deg, condition_name=self.name, details={"angle_deg": angle})


@register_condition(
    key="linear_regression_r2_filter",
    label="Linear Regression R2",
    description="Linear regression R2 threshold",
    category="momentum",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "min_r2", "type": "float", "default": 0.5, "description": "Minimum R2"},
    ],
)
class LinearRegressionR2FilterCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, min_r2: float = 0.5):
        self.lookback_days = lookback_days
        self.min_r2 = min_r2

    @property
    def name(self) -> str:
        return "linear_regression_r2_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        m = _regression_metrics(data["close"], self.lookback_days)
        if m is None:
            return _insufficient(self.name)
        _, _, r2 = m
        return ConditionResult(matched=r2 >= self.min_r2, condition_name=self.name, details={"r2": r2})


@register_condition(
    key="beta_to_benchmark",
    label="Beta to Benchmark",
    description="Rolling beta versus benchmark",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "max_beta", "type": "float", "default": 1.2, "description": "Maximum beta"},
    ],
)
class BetaToBenchmarkCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, max_beta: float = 1.2):
        self.lookback_days = lookback_days
        self.max_beta = max_beta

    @property
    def name(self) -> str:
        return "beta_to_benchmark"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days or "benchmark_close" not in data.columns:
            return _insufficient(self.name)
        stock_ret = data["close"].pct_change().tail(self.lookback_days).dropna()
        bm_ret = data["benchmark_close"].pct_change().tail(self.lookback_days).dropna()
        joined = pd.concat([stock_ret, bm_ret], axis=1).dropna()
        if len(joined) < 2:
            return _insufficient(self.name)
        var = float(joined.iloc[:, 1].var())
        if var == 0:
            return _insufficient(self.name)
        beta = float(joined.iloc[:, 0].cov(joined.iloc[:, 1]) / var)
        return ConditionResult(matched=beta <= self.max_beta, condition_name=self.name, details={"beta": beta})


@register_condition(
    key="correlation_to_benchmark",
    label="Correlation to Benchmark",
    description="Rolling correlation versus benchmark",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "max_corr", "type": "float", "default": 0.8, "description": "Maximum correlation"},
    ],
)
class CorrelationToBenchmarkCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, max_corr: float = 0.8):
        self.lookback_days = lookback_days
        self.max_corr = max_corr

    @property
    def name(self) -> str:
        return "correlation_to_benchmark"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days or "benchmark_close" not in data.columns:
            return _insufficient(self.name)
        stock_ret = data["close"].pct_change().tail(self.lookback_days).dropna()
        bm_ret = data["benchmark_close"].pct_change().tail(self.lookback_days).dropna()
        joined = pd.concat([stock_ret, bm_ret], axis=1).dropna()
        if len(joined) < 2:
            return _insufficient(self.name)
        corr = float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))
        if np.isnan(corr):
            return _insufficient(self.name)
        return ConditionResult(matched=corr <= self.max_corr, condition_name=self.name, details={"correlation": corr})


@register_condition(
    key="support_retest_signal",
    label="Support Retest Signal",
    description="Price retests support and closes above",
    category="price_action",
    params=[
        {"name": "support_lookback", "type": "int", "default": 40, "description": "Support lookback days"},
        {"name": "tolerance_pct", "type": "float", "default": 1.0, "description": "Retest tolerance %"},
    ],
)
class SupportRetestSignalCondition(BaseCondition):
    def __init__(self, support_lookback: int = 40, tolerance_pct: float = 1.0):
        self.support_lookback = support_lookback
        self.tolerance_pct = tolerance_pct

    @property
    def name(self) -> str:
        return "support_retest_signal"

    @property
    def required_days(self) -> int:
        return self.support_lookback + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        support = float(data["low"].iloc[-(self.support_lookback + 1):-1].min())
        low = float(data["low"].iloc[-1])
        close = float(data["close"].iloc[-1])
        tol = support * (self.tolerance_pct / 100.0)
        retested = abs(low - support) <= tol
        reclaimed = close > support
        return ConditionResult(
            matched=bool(retested and reclaimed),
            condition_name=self.name,
            details={"support": support, "low": low, "close": close, "retested": bool(retested)},
        )


@register_condition(
    key="resistance_retest_signal",
    label="Resistance Retest Signal",
    description="Price retests resistance and closes below",
    category="price_action",
    params=[
        {"name": "resistance_lookback", "type": "int", "default": 40, "description": "Resistance lookback days"},
        {"name": "tolerance_pct", "type": "float", "default": 1.0, "description": "Retest tolerance %"},
    ],
)
class ResistanceRetestSignalCondition(BaseCondition):
    def __init__(self, resistance_lookback: int = 40, tolerance_pct: float = 1.0):
        self.resistance_lookback = resistance_lookback
        self.tolerance_pct = tolerance_pct

    @property
    def name(self) -> str:
        return "resistance_retest_signal"

    @property
    def required_days(self) -> int:
        return self.resistance_lookback + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        resistance = float(data["high"].iloc[-(self.resistance_lookback + 1):-1].max())
        high = float(data["high"].iloc[-1])
        close = float(data["close"].iloc[-1])
        tol = resistance * (self.tolerance_pct / 100.0)
        retested = abs(high - resistance) <= tol
        rejected = close < resistance
        return ConditionResult(
            matched=bool(retested and rejected),
            condition_name=self.name,
            details={"resistance": resistance, "high": high, "close": close, "retested": bool(retested)},
        )


@register_condition(
    key="analyst_revision_1m",
    label="Analyst Revision 1M",
    description="One-month analyst estimate revision",
    category="fundamental",
    params=[
        {"name": "min_revision_pct", "type": "float", "default": 0.0, "description": "Minimum revision %"},
    ],
)
class AnalystRevision1MCondition(BaseCondition):
    def __init__(self, min_revision_pct: float = 0.0):
        self.min_revision_pct = min_revision_pct

    @property
    def name(self) -> str:
        return "analyst_revision_1m"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 1:
            return _insufficient(self.name)
        if "analyst_revision_1m" not in data.columns:
            return _insufficient(self.name)
        revision = data["analyst_revision_1m"].iloc[-1]
        if pd.isna(revision):
            return _insufficient(self.name)
        revision = float(revision)
        return ConditionResult(matched=revision >= self.min_revision_pct, condition_name=self.name, details={"revision_pct": revision})


@register_condition(
    key="analyst_revision_3m",
    label="Analyst Revision 3M",
    description="Three-month analyst estimate revision",
    category="fundamental",
    params=[
        {"name": "min_revision_pct", "type": "float", "default": 0.0, "description": "Minimum revision %"},
    ],
)
class AnalystRevision3MCondition(BaseCondition):
    def __init__(self, min_revision_pct: float = 0.0):
        self.min_revision_pct = min_revision_pct

    @property
    def name(self) -> str:
        return "analyst_revision_3m"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 1:
            return _insufficient(self.name)
        if "analyst_revision_3m" not in data.columns:
            return _insufficient(self.name)
        revision = data["analyst_revision_3m"].iloc[-1]
        if pd.isna(revision):
            return _insufficient(self.name)
        revision = float(revision)
        return ConditionResult(matched=revision >= self.min_revision_pct, condition_name=self.name, details={"revision_pct": revision})
