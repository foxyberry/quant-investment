"""
Quant Trend Conditions Batch 4
team:quant 이슈 기반 추세/모멘텀 조건
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


def _insufficient(name: str) -> ConditionResult:
    return ConditionResult(matched=False, condition_name=name, details={"error": "Insufficient data"})


def _cross_up(a: pd.Series, b: pd.Series, lookback_days: int) -> int | None:
    for i in range(1, lookback_days + 1):
        pa, pb = a.iloc[-(i + 1)], b.iloc[-(i + 1)]
        ca, cb = a.iloc[-i], b.iloc[-i]
        if pd.isna(pa) or pd.isna(pb) or pd.isna(ca) or pd.isna(cb):
            continue
        if pa <= pb and ca > cb:
            return i
    return None


def _cross_down(a: pd.Series, b: pd.Series, lookback_days: int) -> int | None:
    for i in range(1, lookback_days + 1):
        pa, pb = a.iloc[-(i + 1)], b.iloc[-(i + 1)]
        ca, cb = a.iloc[-i], b.iloc[-i]
        if pd.isna(pa) or pd.isna(pb) or pd.isna(ca) or pd.isna(cb):
            continue
        if pa >= pb and ca < cb:
            return i
    return None


def _ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def _atr(data: pd.DataFrame, period: int) -> pd.Series:
    h = data["high"]
    l = data["low"]
    c = data["close"]
    prev_close = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _adx(data: pd.DataFrame, period: int = 14):
    high = data["high"]
    low = data["low"]
    close = data["close"]

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr = pd.concat([(high - low).abs(), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr.replace(0, np.nan))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(period).mean()
    return adx, plus_di, minus_di


@register_condition(
    key="momentum_12_1",
    label="Momentum 12-1",
    description="12-month momentum excluding recent 1 month",
    category="momentum",
    params=[
        {"name": "lookback_months", "type": "int", "default": 12, "description": "Lookback months"},
        {"name": "skip_recent_months", "type": "int", "default": 1, "description": "Skip recent months"},
        {"name": "min_return_pct", "type": "float", "default": 20.0, "description": "Minimum return %"},
    ],
)
class Momentum121Condition(BaseCondition):
    def __init__(self, lookback_months: int = 12, skip_recent_months: int = 1, min_return_pct: float = 20.0):
        self.lookback_months = lookback_months
        self.skip_recent_months = skip_recent_months
        self.min_return_pct = min_return_pct

    @property
    def name(self) -> str:
        return "momentum_12_1"

    @property
    def required_days(self) -> int:
        return (self.lookback_months * 21) + (self.skip_recent_months * 21) + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        skip = self.skip_recent_months * 21
        lookback = self.lookback_months * 21
        end_price = data["close"].iloc[-(skip + 1)]
        start_price = data["close"].iloc[-(skip + lookback)]
        if pd.isna(start_price) or pd.isna(end_price) or start_price == 0:
            return _insufficient(self.name)
        ret = float(((end_price / start_price) - 1.0) * 100.0)
        return ConditionResult(matched=ret >= self.min_return_pct, condition_name=self.name, details={"return_pct": ret})


@register_condition(
    key="volatility_n_day",
    label="Volatility N Day",
    description="Annualized N-day volatility filter",
    category="risk",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "max_annualized_vol_pct", "type": "float", "default": 25.0, "description": "Max annualized volatility %"},
    ],
)
class VolatilityNDayCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, max_annualized_vol_pct: float = 25.0):
        self.lookback_days = lookback_days
        self.max_annualized_vol_pct = max_annualized_vol_pct

    @property
    def name(self) -> str:
        return "volatility_n_day"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        r = data["close"].pct_change().dropna().tail(self.lookback_days)
        if len(r) == 0:
            return _insufficient(self.name)
        vol = float(r.std(ddof=0) * np.sqrt(252) * 100.0)
        return ConditionResult(matched=vol <= self.max_annualized_vol_pct, condition_name=self.name, details={"annualized_vol_pct": vol})


@register_condition(
    key="distance_from_52w_high",
    label="Distance From 52W High",
    description="Distance below 52-week high",
    category="price",
    params=[
        {"name": "lookback_days", "type": "int", "default": 252, "description": "Lookback days"},
        {"name": "max_distance_pct", "type": "float", "default": 10.0, "description": "Maximum distance %"},
    ],
)
class DistanceFrom52WHighCondition(BaseCondition):
    def __init__(self, lookback_days: int = 252, max_distance_pct: float = 10.0):
        self.lookback_days = lookback_days
        self.max_distance_pct = max_distance_pct

    @property
    def name(self) -> str:
        return "distance_from_52w_high"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        high = data["high"].tail(self.lookback_days).max()
        close = data["close"].iloc[-1]
        if pd.isna(high) or pd.isna(close) or high == 0:
            return _insufficient(self.name)
        distance = float(((high - close) / high) * 100.0)
        return ConditionResult(matched=distance <= self.max_distance_pct, condition_name=self.name, details={"distance_pct": distance})


@register_condition(
    key="relative_strength_vs_benchmark",
    label="Relative Strength Vs Benchmark",
    description="Stock return minus benchmark return",
    category="momentum",
    params=[
        {"name": "lookback_days", "type": "int", "default": 63, "description": "Lookback days"},
        {"name": "min_excess_return_pct", "type": "float", "default": 5.0, "description": "Minimum excess return %"},
    ],
)
class RelativeStrengthVsBenchmarkCondition(BaseCondition):
    def __init__(self, lookback_days: int = 63, min_excess_return_pct: float = 5.0):
        self.lookback_days = lookback_days
        self.min_excess_return_pct = min_excess_return_pct

    @property
    def name(self) -> str:
        return "relative_strength_vs_benchmark"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days or "benchmark_close" not in data.columns:
            return _insufficient(self.name)
        s0 = data["close"].iloc[-(self.lookback_days + 1)]
        s1 = data["close"].iloc[-1]
        b0 = data["benchmark_close"].iloc[-(self.lookback_days + 1)]
        b1 = data["benchmark_close"].iloc[-1]
        if min(s0, b0) == 0 or any(pd.isna(v) for v in [s0, s1, b0, b1]):
            return _insufficient(self.name)
        stock_ret = ((s1 / s0) - 1.0) * 100.0
        bench_ret = ((b1 / b0) - 1.0) * 100.0
        excess = float(stock_ret - bench_ret)
        return ConditionResult(matched=excess >= self.min_excess_return_pct, condition_name=self.name, details={"excess_return_pct": excess})


@register_condition(
    key="adx_trend_strength",
    label="ADX Trend Strength",
    description="ADX trend strength filter",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 14, "description": "ADX period"},
        {"name": "min_adx", "type": "float", "default": 25.0, "description": "Minimum ADX"},
        {"name": "di_direction", "type": "str", "default": "any", "description": "any|plus|minus"},
    ],
)
class ADXTrendStrengthCondition(BaseCondition):
    def __init__(self, period: int = 14, min_adx: float = 25.0, di_direction: str = "any"):
        self.period = period
        self.min_adx = min_adx
        self.di_direction = di_direction

    @property
    def name(self) -> str:
        return "adx_trend_strength"

    @property
    def required_days(self) -> int:
        return self.period * 3

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        adx, plus_di, minus_di = _adx(data, self.period)
        a = adx.iloc[-1]
        p = plus_di.iloc[-1]
        m = minus_di.iloc[-1]
        if any(pd.isna(v) for v in [a, p, m]):
            return _insufficient(self.name)
        matched = a >= self.min_adx
        if self.di_direction == "plus":
            matched = matched and (p > m)
        elif self.di_direction == "minus":
            matched = matched and (m > p)
        return ConditionResult(matched=bool(matched), condition_name=self.name, details={"adx": float(a), "+di": float(p), "-di": float(m)})


@register_condition(
    key="ma_ribbon_alignment",
    label="MA Ribbon Alignment",
    description="Short>Mid>Long MA alignment",
    category="movingAverage",
    params=[
        {"name": "short_period", "type": "int", "default": 20, "description": "Short MA"},
        {"name": "mid_period", "type": "int", "default": 50, "description": "Mid MA"},
        {"name": "long_period", "type": "int", "default": 200, "description": "Long MA"},
    ],
)
class MARibbonAlignmentCondition(BaseCondition):
    def __init__(self, short_period: int = 20, mid_period: int = 50, long_period: int = 200):
        self.short_period = short_period
        self.mid_period = mid_period
        self.long_period = long_period

    @property
    def name(self) -> str:
        return "ma_ribbon_alignment"

    @property
    def required_days(self) -> int:
        return self.long_period + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        close = data["close"]
        s = close.rolling(self.short_period).mean().iloc[-1]
        m = close.rolling(self.mid_period).mean().iloc[-1]
        l = close.rolling(self.long_period).mean().iloc[-1]
        if any(pd.isna(v) for v in [s, m, l]):
            return _insufficient(self.name)
        matched = s > m > l
        return ConditionResult(matched=matched, condition_name=self.name, details={"short": float(s), "mid": float(m), "long": float(l)})


@register_condition(
    key="golden_cross_50_200",
    label="Golden Cross 50/200",
    description="50MA crossing above 200MA",
    category="movingAverage",
    params=[
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
    ],
)
class GoldenCross50200Condition(BaseCondition):
    def __init__(self, lookback_days: int = 5):
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "golden_cross_50_200"

    @property
    def required_days(self) -> int:
        return 205

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        ma50 = data["close"].rolling(50).mean()
        ma200 = data["close"].rolling(200).mean()
        day = _cross_up(ma50, ma200, self.lookback_days)
        return ConditionResult(matched=day is not None, condition_name=self.name, details={"cross_day": day})


@register_condition(
    key="death_cross_50_200",
    label="Death Cross 50/200",
    description="50MA crossing below 200MA",
    category="movingAverage",
    params=[
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
    ],
)
class DeathCross50200Condition(BaseCondition):
    def __init__(self, lookback_days: int = 5):
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "death_cross_50_200"

    @property
    def required_days(self) -> int:
        return 205

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        ma50 = data["close"].rolling(50).mean()
        ma200 = data["close"].rolling(200).mean()
        day = _cross_down(ma50, ma200, self.lookback_days)
        return ConditionResult(matched=day is not None, condition_name=self.name, details={"cross_day": day})


@register_condition(
    key="donchian_channel_breakout",
    label="Donchian Channel Breakout",
    description="Breakout above Donchian upper band",
    category="breakout",
    params=[
        {"name": "lookback_days", "type": "int", "default": 20, "description": "Channel period"},
    ],
)
class DonchianChannelBreakoutCondition(BaseCondition):
    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "donchian_channel_breakout"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        upper_prev = data["high"].shift(1).rolling(self.lookback_days).max().iloc[-1]
        close = data["close"].iloc[-1]
        if pd.isna(upper_prev) or pd.isna(close):
            return _insufficient(self.name)
        return ConditionResult(matched=bool(close > upper_prev), condition_name=self.name, details={"upper_prev": float(upper_prev), "close": float(close)})


@register_condition(
    key="keltner_channel_breakout",
    label="Keltner Channel Breakout",
    description="Breakout above EMA + ATR band",
    category="breakout",
    params=[
        {"name": "ema_period", "type": "int", "default": 20, "description": "EMA period"},
        {"name": "atr_period", "type": "int", "default": 20, "description": "ATR period"},
        {"name": "atr_multiplier", "type": "float", "default": 2.0, "description": "ATR multiplier"},
    ],
)
class KeltnerChannelBreakoutCondition(BaseCondition):
    def __init__(self, ema_period: int = 20, atr_period: int = 20, atr_multiplier: float = 2.0):
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier

    @property
    def name(self) -> str:
        return "keltner_channel_breakout"

    @property
    def required_days(self) -> int:
        return max(self.ema_period, self.atr_period) + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        mid = _ema(data["close"], self.ema_period).iloc[-1]
        atr = _atr(data, self.atr_period).iloc[-1]
        close = data["close"].iloc[-1]
        if any(pd.isna(v) for v in [mid, atr, close]):
            return _insufficient(self.name)
        upper = float(mid + (self.atr_multiplier * atr))
        return ConditionResult(matched=bool(close > upper), condition_name=self.name, details={"upper": upper, "close": float(close)})
