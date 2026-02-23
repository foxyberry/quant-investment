"""
Quant Oscillator Conditions Batch 5
team:quant 이슈 기반 오실레이터/자금흐름 조건
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


def _insufficient(name: str) -> ConditionResult:
    return ConditionResult(matched=False, condition_name=name, details={"error": "Insufficient data"})


def _ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def _cross_up(a: pd.Series, b: pd.Series, lookback_days: int) -> int | None:
    for i in range(1, lookback_days + 1):
        pa, pb = a.iloc[-(i + 1)], b.iloc[-(i + 1)]
        ca, cb = a.iloc[-i], b.iloc[-i]
        if pd.isna(pa) or pd.isna(pb) or pd.isna(ca) or pd.isna(cb):
            continue
        if pa <= pb and ca > cb:
            return i
    return None


def _typical_price(data: pd.DataFrame) -> pd.Series:
    return (data["high"] + data["low"] + data["close"]) / 3.0


def _money_flow_multiplier(data: pd.DataFrame) -> pd.Series:
    denom = (data["high"] - data["low"]).replace(0, np.nan)
    return ((data["close"] - data["low"]) - (data["high"] - data["close"])) / denom


def _stochastic_k(data: pd.DataFrame, period: int = 14) -> pd.Series:
    ll = data["low"].rolling(period).min()
    hh = data["high"].rolling(period).max()
    return 100 * (data["close"] - ll) / (hh - ll).replace(0, np.nan)


@register_condition(
    key="bollinger_squeeze_breakout",
    label="Bollinger Squeeze Breakout",
    description="Low BB width followed by upper band breakout",
    category="oscillator",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "Bollinger period"},
        {"name": "std_mult", "type": "float", "default": 2.0, "description": "Std multiplier"},
        {"name": "max_width_pct", "type": "float", "default": 10.0, "description": "Max squeeze width %"},
    ],
)
class BollingerSqueezeBreakoutCondition(BaseCondition):
    def __init__(self, period: int = 20, std_mult: float = 2.0, max_width_pct: float = 10.0):
        self.period = period
        self.std_mult = std_mult
        self.max_width_pct = max_width_pct

    @property
    def name(self) -> str:
        return "bollinger_squeeze_breakout"

    @property
    def required_days(self) -> int:
        return self.period + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        ma = data["close"].rolling(self.period).mean()
        std = data["close"].rolling(self.period).std(ddof=0)
        upper = ma + (self.std_mult * std)
        lower = ma - (self.std_mult * std)
        prev_width_pct = ((upper.iloc[-2] - lower.iloc[-2]) / ma.iloc[-2]) * 100.0 if ma.iloc[-2] else np.nan
        breakout = data["close"].iloc[-1] > upper.iloc[-1]
        if pd.isna(prev_width_pct) or pd.isna(upper.iloc[-1]):
            return _insufficient(self.name)
        matched = (prev_width_pct <= self.max_width_pct) and breakout
        return ConditionResult(matched=bool(matched), condition_name=self.name, details={"prev_width_pct": float(prev_width_pct), "breakout": bool(breakout)})


@register_condition(
    key="bollinger_percent_b",
    label="Bollinger Percent B",
    description="Price position within Bollinger bands",
    category="oscillator",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "Bollinger period"},
        {"name": "std_mult", "type": "float", "default": 2.0, "description": "Std multiplier"},
        {"name": "min_percent_b", "type": "float", "default": 0.0, "description": "Min %B"},
        {"name": "max_percent_b", "type": "float", "default": 1.0, "description": "Max %B"},
    ],
)
class BollingerPercentBCondition(BaseCondition):
    def __init__(self, period: int = 20, std_mult: float = 2.0, min_percent_b: float = 0.0, max_percent_b: float = 1.0):
        self.period = period
        self.std_mult = std_mult
        self.min_percent_b = min_percent_b
        self.max_percent_b = max_percent_b

    @property
    def name(self) -> str:
        return "bollinger_percent_b"

    @property
    def required_days(self) -> int:
        return self.period + 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        ma = data["close"].rolling(self.period).mean().iloc[-1]
        std = data["close"].rolling(self.period).std(ddof=0).iloc[-1]
        close = data["close"].iloc[-1]
        upper = ma + self.std_mult * std
        lower = ma - self.std_mult * std
        denom = upper - lower
        if pd.isna(denom) or denom == 0:
            return _insufficient(self.name)
        percent_b = float((close - lower) / denom)
        matched = self.min_percent_b <= percent_b <= self.max_percent_b
        return ConditionResult(matched=bool(matched), condition_name=self.name, details={"percent_b": percent_b})


@register_condition(
    key="ppo_signal_cross",
    label="PPO Signal Cross",
    description="PPO line crossing signal line",
    category="oscillator",
    params=[
        {"name": "fast_period", "type": "int", "default": 12, "description": "Fast EMA"},
        {"name": "slow_period", "type": "int", "default": 26, "description": "Slow EMA"},
        {"name": "signal_period", "type": "int", "default": 9, "description": "Signal EMA"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
    ],
)
class PPOSignalCrossCondition(BaseCondition):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, lookback_days: int = 5):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "ppo_signal_cross"

    @property
    def required_days(self) -> int:
        return self.slow_period + self.signal_period + self.lookback_days + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        fast = _ema(data["close"], self.fast_period)
        slow = _ema(data["close"], self.slow_period)
        ppo = ((fast - slow) / slow.replace(0, np.nan)) * 100.0
        signal = _ema(ppo, self.signal_period)
        day = _cross_up(ppo, signal, self.lookback_days)
        return ConditionResult(matched=day is not None, condition_name=self.name, details={"cross_day": day})


@register_condition(
    key="stochastic_cross_signal",
    label="Stochastic Cross Signal",
    description="%K crossing above %D",
    category="oscillator",
    params=[
        {"name": "k_period", "type": "int", "default": 14, "description": "K period"},
        {"name": "d_period", "type": "int", "default": 3, "description": "D period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
    ],
)
class StochasticCrossSignalCondition(BaseCondition):
    def __init__(self, k_period: int = 14, d_period: int = 3, lookback_days: int = 5):
        self.k_period = k_period
        self.d_period = d_period
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "stochastic_cross_signal"

    @property
    def required_days(self) -> int:
        return self.k_period + self.d_period + self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        k = _stochastic_k(data, self.k_period)
        d = k.rolling(self.d_period).mean()
        day = _cross_up(k, d, self.lookback_days)
        return ConditionResult(matched=day is not None, condition_name=self.name, details={"cross_day": day})


@register_condition(
    key="stochrsi_signal",
    label="StochRSI Signal",
    description="StochRSI threshold signal",
    category="oscillator",
    params=[
        {"name": "rsi_period", "type": "int", "default": 14, "description": "RSI period"},
        {"name": "stoch_period", "type": "int", "default": 14, "description": "Stoch period"},
        {"name": "mode", "type": "str", "default": "oversold", "description": "oversold|overbought"},
    ],
)
class StochRSISignalCondition(BaseCondition):
    def __init__(self, rsi_period: int = 14, stoch_period: int = 14, mode: str = "oversold"):
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.mode = mode

    @property
    def name(self) -> str:
        return "stochrsi_signal"

    @property
    def required_days(self) -> int:
        return self.rsi_period + self.stoch_period + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        delta = data["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        min_rsi = rsi.rolling(self.stoch_period).min()
        max_rsi = rsi.rolling(self.stoch_period).max()
        stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi).replace(0, np.nan)
        curr = stoch_rsi.iloc[-1]
        if pd.isna(curr):
            return _insufficient(self.name)
        matched = curr >= 0.8 if self.mode == "overbought" else curr <= 0.2
        return ConditionResult(matched=bool(matched), condition_name=self.name, details={"stochrsi": float(curr)})


@register_condition(
    key="aroon_oscillator_signal",
    label="Aroon Oscillator Signal",
    description="Aroon up-down oscillator filter",
    category="oscillator",
    params=[
        {"name": "period", "type": "int", "default": 25, "description": "Aroon period"},
        {"name": "min_oscillator", "type": "float", "default": 30.0, "description": "Minimum oscillator"},
    ],
)
class AroonOscillatorSignalCondition(BaseCondition):
    def __init__(self, period: int = 25, min_oscillator: float = 30.0):
        self.period = period
        self.min_oscillator = min_oscillator

    @property
    def name(self) -> str:
        return "aroon_oscillator_signal"

    @property
    def required_days(self) -> int:
        return self.period + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        highs = data["high"]
        lows = data["low"]

        def up(w):
            return ((np.argmax(w) + 1) / self.period) * 100.0

        def down(w):
            return ((np.argmin(w) + 1) / self.period) * 100.0

        a_up = highs.rolling(self.period).apply(up, raw=True)
        a_down = lows.rolling(self.period).apply(down, raw=True)
        osc = a_up.iloc[-1] - a_down.iloc[-1]
        if pd.isna(osc):
            return _insufficient(self.name)
        return ConditionResult(matched=bool(osc >= self.min_oscillator), condition_name=self.name, details={"oscillator": float(osc)})


@register_condition(
    key="ultimate_oscillator_signal",
    label="Ultimate Oscillator Signal",
    description="Ultimate oscillator threshold",
    category="oscillator",
    params=[
        {"name": "min_value", "type": "float", "default": 50.0, "description": "Minimum value"},
    ],
)
class UltimateOscillatorSignalCondition(BaseCondition):
    def __init__(self, min_value: float = 50.0):
        self.min_value = min_value

    @property
    def name(self) -> str:
        return "ultimate_oscillator_signal"

    @property
    def required_days(self) -> int:
        return 30

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        prev_close = data["close"].shift(1)
        bp = data["close"] - pd.concat([data["low"], prev_close], axis=1).min(axis=1)
        tr = pd.concat([data["high"], prev_close], axis=1).max(axis=1) - pd.concat([data["low"], prev_close], axis=1).min(axis=1)
        avg7 = bp.rolling(7).sum() / tr.rolling(7).sum().replace(0, np.nan)
        avg14 = bp.rolling(14).sum() / tr.rolling(14).sum().replace(0, np.nan)
        avg28 = bp.rolling(28).sum() / tr.rolling(28).sum().replace(0, np.nan)
        uo = 100.0 * ((4 * avg7) + (2 * avg14) + avg28) / 7.0
        curr = uo.iloc[-1]
        if pd.isna(curr):
            return _insufficient(self.name)
        return ConditionResult(matched=bool(curr >= self.min_value), condition_name=self.name, details={"ultimate_oscillator": float(curr)})


@register_condition(
    key="chaikin_money_flow_signal",
    label="Chaikin Money Flow",
    description="CMF threshold signal",
    category="moneyflow",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "CMF period"},
        {"name": "min_cmf", "type": "float", "default": 0.0, "description": "Minimum CMF"},
    ],
)
class ChaikinMoneyFlowSignalCondition(BaseCondition):
    def __init__(self, period: int = 20, min_cmf: float = 0.0):
        self.period = period
        self.min_cmf = min_cmf

    @property
    def name(self) -> str:
        return "chaikin_money_flow_signal"

    @property
    def required_days(self) -> int:
        return self.period + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        mfm = _money_flow_multiplier(data)
        mfv = mfm * data["volume"]
        cmf = mfv.rolling(self.period).sum() / data["volume"].rolling(self.period).sum().replace(0, np.nan)
        curr = cmf.iloc[-1]
        if pd.isna(curr):
            return _insufficient(self.name)
        return ConditionResult(matched=bool(curr >= self.min_cmf), condition_name=self.name, details={"cmf": float(curr)})


@register_condition(
    key="chaikin_oscillator_signal",
    label="Chaikin Oscillator",
    description="Chaikin oscillator above threshold",
    category="moneyflow",
    params=[
        {"name": "fast_period", "type": "int", "default": 3, "description": "Fast EMA"},
        {"name": "slow_period", "type": "int", "default": 10, "description": "Slow EMA"},
        {"name": "min_value", "type": "float", "default": 0.0, "description": "Minimum oscillator"},
    ],
)
class ChaikinOscillatorSignalCondition(BaseCondition):
    def __init__(self, fast_period: int = 3, slow_period: int = 10, min_value: float = 0.0):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.min_value = min_value

    @property
    def name(self) -> str:
        return "chaikin_oscillator_signal"

    @property
    def required_days(self) -> int:
        return self.slow_period + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        mfm = _money_flow_multiplier(data).fillna(0.0)
        ad_line = (mfm * data["volume"]).cumsum()
        osc = _ema(ad_line, self.fast_period) - _ema(ad_line, self.slow_period)
        curr = osc.iloc[-1]
        if pd.isna(curr):
            return _insufficient(self.name)
        return ConditionResult(matched=bool(curr >= self.min_value), condition_name=self.name, details={"chaikin_oscillator": float(curr)})


@register_condition(
    key="ad_line_trend",
    label="A/D Line Trend",
    description="Accumulation/distribution line trend",
    category="moneyflow",
    params=[
        {"name": "lookback_days", "type": "int", "default": 20, "description": "Lookback days"},
    ],
)
class ADLineTrendCondition(BaseCondition):
    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "ad_line_trend"

    @property
    def required_days(self) -> int:
        return self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        mfm = _money_flow_multiplier(data).fillna(0.0)
        ad_line = (mfm * data["volume"]).cumsum()
        prev = ad_line.iloc[-(self.lookback_days + 1)]
        curr = ad_line.iloc[-1]
        if pd.isna(prev) or pd.isna(curr):
            return _insufficient(self.name)
        slope = float(curr - prev)
        return ConditionResult(matched=bool(slope > 0), condition_name=self.name, details={"ad_slope": slope})
