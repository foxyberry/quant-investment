"""
Momentum & Trend Conditions
추세/모멘텀 기반 스크리닝 조건
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _macd(close: pd.Series, fast_period: int, slow_period: int, signal_period: int):
    macd_line = _ema(close, fast_period) - _ema(close, slow_period)
    signal_line = _ema(macd_line, signal_period)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _safe_float(value) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _insufficient(name: str) -> ConditionResult:
    return ConditionResult(
        matched=False,
        condition_name=name,
        details={"error": "Insufficient data"},
    )


def _crossed_up(a: pd.Series, b: pd.Series, lookback_days: int) -> int | None:
    for i in range(1, lookback_days + 1):
        prev_a, prev_b = a.iloc[-(i + 1)], b.iloc[-(i + 1)]
        curr_a, curr_b = a.iloc[-i], b.iloc[-i]
        if pd.isna(prev_a) or pd.isna(prev_b) or pd.isna(curr_a) or pd.isna(curr_b):
            continue
        if prev_a <= prev_b and curr_a > curr_b:
            return i
    return None


def _crossed_down(a: pd.Series, b: pd.Series, lookback_days: int) -> int | None:
    for i in range(1, lookback_days + 1):
        prev_a, prev_b = a.iloc[-(i + 1)], b.iloc[-(i + 1)]
        curr_a, curr_b = a.iloc[-i], b.iloc[-i]
        if pd.isna(prev_a) or pd.isna(prev_b) or pd.isna(curr_a) or pd.isna(curr_b):
            continue
        if prev_a >= prev_b and curr_a < curr_b:
            return i
    return None


def _cci(data: pd.DataFrame, period: int) -> pd.Series:
    typical = (data["high"] + data["low"] + data["close"]) / 3.0
    sma = typical.rolling(period).mean()
    md = (typical - sma).abs().rolling(period).mean()
    return (typical - sma) / (0.015 * md)


def _williams_r(data: pd.DataFrame, period: int) -> pd.Series:
    highest = data["high"].rolling(period).max()
    lowest = data["low"].rolling(period).min()
    denom = highest - lowest
    return -100 * (highest - data["close"]) / denom


def _trix(close: pd.Series, period: int) -> pd.Series:
    ema1 = _ema(close, period)
    ema2 = _ema(ema1, period)
    ema3 = _ema(ema2, period)
    return ema3.pct_change() * 100.0


def _aroon(data: pd.DataFrame, period: int):
    highs = data["high"]
    lows = data["low"]

    def _up(window: np.ndarray) -> float:
        idx = np.argmax(window)
        return ((idx + 1) / period) * 100.0

    def _down(window: np.ndarray) -> float:
        idx = np.argmin(window)
        return ((idx + 1) / period) * 100.0

    aroon_up = highs.rolling(period).apply(_up, raw=True)
    aroon_down = lows.rolling(period).apply(_down, raw=True)
    return aroon_up, aroon_down


def _money_flow_index(data: pd.DataFrame, period: int) -> pd.Series:
    typical = (data["high"] + data["low"] + data["close"]) / 3.0
    raw_money_flow = typical * data["volume"]
    direction = typical.diff()

    positive_flow = raw_money_flow.where(direction > 0, 0.0)
    negative_flow = raw_money_flow.where(direction < 0, 0.0).abs()

    pos_sum = positive_flow.rolling(period).sum()
    neg_sum = negative_flow.rolling(period).sum()
    money_ratio = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + money_ratio))


@register_condition(
    key="ema_cross",
    label="EMA Cross",
    description="EMA cross signal",
    category="momentum",
    params=[
        {"name": "fast_period", "type": "int", "default": 12, "description": "Fast EMA period"},
        {"name": "slow_period", "type": "int", "default": 26, "description": "Slow EMA period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
        {"name": "direction", "type": "str", "default": "bullish", "description": "bullish|bearish"},
    ],
)
class EMACrossCondition(BaseCondition):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, lookback_days: int = 5, direction: str = "bullish"):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.lookback_days = lookback_days
        self.direction = direction

    @property
    def name(self) -> str:
        return f"ema_cross_{self.fast_period}_{self.slow_period}_{self.direction}"

    @property
    def required_days(self) -> int:
        return self.slow_period + self.lookback_days + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)

        fast = _ema(data["close"], self.fast_period)
        slow = _ema(data["close"], self.slow_period)
        if self.direction == "bearish":
            cross_day = _crossed_down(fast, slow, self.lookback_days)
        else:
            cross_day = _crossed_up(fast, slow, self.lookback_days)

        return ConditionResult(
            matched=cross_day is not None,
            condition_name=self.name,
            details={
                "direction": self.direction,
                "fast": _safe_float(fast.iloc[-1]),
                "slow": _safe_float(slow.iloc[-1]),
                "cross_day": cross_day,
            },
        )


@register_condition(
    key="ema_slope",
    label="EMA Slope",
    description="EMA slope over lookback",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "EMA period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Slope lookback"},
        {"name": "min_slope_pct", "type": "float", "default": 0.0, "description": "Minimum slope %"},
    ],
)
class EMASlopeCondition(BaseCondition):
    def __init__(self, period: int = 20, lookback_days: int = 5, min_slope_pct: float = 0.0):
        self.period = period
        self.lookback_days = lookback_days
        self.min_slope_pct = min_slope_pct

    @property
    def name(self) -> str:
        return f"ema_slope_{self.period}"

    @property
    def required_days(self) -> int:
        return self.period + self.lookback_days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        ema = _ema(data["close"], self.period)
        prev = ema.iloc[-(self.lookback_days + 1)]
        curr = ema.iloc[-1]
        if pd.isna(prev) or prev == 0 or pd.isna(curr):
            return _insufficient(self.name)
        slope_pct = ((curr - prev) / prev) * 100.0
        return ConditionResult(
            matched=slope_pct >= self.min_slope_pct,
            condition_name=self.name,
            details={"slope_pct": float(slope_pct), "min_slope_pct": self.min_slope_pct},
        )


@register_condition(
    key="sma_slope",
    label="SMA Slope",
    description="SMA slope over lookback",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "SMA period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Slope lookback"},
        {"name": "min_slope_pct", "type": "float", "default": 0.0, "description": "Minimum slope %"},
    ],
)
class SMASlopeCondition(BaseCondition):
    def __init__(self, period: int = 20, lookback_days: int = 5, min_slope_pct: float = 0.0):
        self.period = period
        self.lookback_days = lookback_days
        self.min_slope_pct = min_slope_pct

    @property
    def name(self) -> str:
        return f"sma_slope_{self.period}"

    @property
    def required_days(self) -> int:
        return self.period + self.lookback_days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        sma = data["close"].rolling(self.period).mean()
        prev = sma.iloc[-(self.lookback_days + 1)]
        curr = sma.iloc[-1]
        if pd.isna(prev) or prev == 0 or pd.isna(curr):
            return _insufficient(self.name)
        slope_pct = ((curr - prev) / prev) * 100.0
        return ConditionResult(
            matched=slope_pct >= self.min_slope_pct,
            condition_name=self.name,
            details={"slope_pct": float(slope_pct), "min_slope_pct": self.min_slope_pct},
        )


@register_condition(
    key="macd_signal_cross",
    label="MACD Signal Cross",
    description="MACD line crossing signal line",
    category="momentum",
    params=[
        {"name": "fast_period", "type": "int", "default": 12, "description": "Fast EMA"},
        {"name": "slow_period", "type": "int", "default": 26, "description": "Slow EMA"},
        {"name": "signal_period", "type": "int", "default": 9, "description": "Signal EMA"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback"},
        {"name": "direction", "type": "str", "default": "bullish", "description": "bullish|bearish"},
    ],
)
class MACDSignalCrossCondition(BaseCondition):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, lookback_days: int = 5, direction: str = "bullish"):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.lookback_days = lookback_days
        self.direction = direction

    @property
    def name(self) -> str:
        return f"macd_signal_cross_{self.direction}"

    @property
    def required_days(self) -> int:
        return self.slow_period + self.signal_period + self.lookback_days + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        macd_line, signal_line, _ = _macd(data["close"], self.fast_period, self.slow_period, self.signal_period)
        if self.direction == "bearish":
            cross_day = _crossed_down(macd_line, signal_line, self.lookback_days)
        else:
            cross_day = _crossed_up(macd_line, signal_line, self.lookback_days)
        return ConditionResult(
            matched=cross_day is not None,
            condition_name=self.name,
            details={"macd": _safe_float(macd_line.iloc[-1]), "signal": _safe_float(signal_line.iloc[-1]), "cross_day": cross_day},
        )


@register_condition(
    key="macd_histogram_slope",
    label="MACD Histogram Slope",
    description="MACD histogram slope",
    category="momentum",
    params=[
        {"name": "fast_period", "type": "int", "default": 12, "description": "Fast EMA"},
        {"name": "slow_period", "type": "int", "default": 26, "description": "Slow EMA"},
        {"name": "signal_period", "type": "int", "default": 9, "description": "Signal EMA"},
        {"name": "lookback_days", "type": "int", "default": 3, "description": "Slope lookback"},
        {"name": "min_slope", "type": "float", "default": 0.0, "description": "Minimum histogram slope"},
    ],
)
class MACDHistogramSlopeCondition(BaseCondition):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, lookback_days: int = 3, min_slope: float = 0.0):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.lookback_days = lookback_days
        self.min_slope = min_slope

    @property
    def name(self) -> str:
        return "macd_histogram_slope"

    @property
    def required_days(self) -> int:
        return self.slow_period + self.signal_period + self.lookback_days + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        _, _, hist = _macd(data["close"], self.fast_period, self.slow_period, self.signal_period)
        prev = hist.iloc[-(self.lookback_days + 1)]
        curr = hist.iloc[-1]
        if pd.isna(prev) or pd.isna(curr):
            return _insufficient(self.name)
        slope = curr - prev
        return ConditionResult(
            matched=slope >= self.min_slope,
            condition_name=self.name,
            details={"hist": _safe_float(curr), "slope": _safe_float(slope), "min_slope": self.min_slope},
        )


@register_condition(
    key="cci_overbought_oversold",
    label="CCI Overbought/Oversold",
    description="CCI threshold filter",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "CCI period"},
        {"name": "mode", "type": "str", "default": "oversold", "description": "oversold|overbought"},
        {"name": "threshold", "type": "float", "default": 100, "description": "Absolute threshold"},
    ],
)
class CCIOverboughtOversoldCondition(BaseCondition):
    def __init__(self, period: int = 20, mode: str = "oversold", threshold: float = 100):
        self.period = period
        self.mode = mode
        self.threshold = threshold

    @property
    def name(self) -> str:
        return f"cci_{self.mode}"

    @property
    def required_days(self) -> int:
        return self.period + 20

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        cci = _cci(data, self.period)
        current = cci.iloc[-1]
        if pd.isna(current):
            return _insufficient(self.name)
        if self.mode == "overbought":
            matched = current >= self.threshold
        else:
            matched = current <= -abs(self.threshold)
        return ConditionResult(matched=matched, condition_name=self.name, details={"cci": _safe_float(current), "mode": self.mode})


@register_condition(
    key="williams_r_reversal",
    label="Williams %R Reversal",
    description="Williams %R reversal signal",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 14, "description": "Williams %R period"},
        {"name": "oversold", "type": "float", "default": -80, "description": "Oversold level"},
        {"name": "overbought", "type": "float", "default": -20, "description": "Overbought level"},
        {"name": "direction", "type": "str", "default": "bullish", "description": "bullish|bearish"},
    ],
)
class WilliamsRReversalCondition(BaseCondition):
    def __init__(self, period: int = 14, oversold: float = -80, overbought: float = -20, direction: str = "bullish"):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.direction = direction

    @property
    def name(self) -> str:
        return f"williams_r_{self.direction}"

    @property
    def required_days(self) -> int:
        return self.period + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        wr = _williams_r(data, self.period)
        prev = wr.iloc[-2]
        curr = wr.iloc[-1]
        if pd.isna(prev) or pd.isna(curr):
            return _insufficient(self.name)
        if self.direction == "bearish":
            matched = prev > self.overbought and curr <= self.overbought
        else:
            matched = prev < self.oversold and curr >= self.oversold
        return ConditionResult(matched=matched, condition_name=self.name, details={"williams_r": _safe_float(curr)})


@register_condition(
    key="trix_cross",
    label="TRIX Cross",
    description="TRIX crossing signal line",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 15, "description": "TRIX period"},
        {"name": "signal_period", "type": "int", "default": 9, "description": "Signal period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback"},
        {"name": "direction", "type": "str", "default": "bullish", "description": "bullish|bearish"},
    ],
)
class TRIXCrossCondition(BaseCondition):
    def __init__(self, period: int = 15, signal_period: int = 9, lookback_days: int = 5, direction: str = "bullish"):
        self.period = period
        self.signal_period = signal_period
        self.lookback_days = lookback_days
        self.direction = direction

    @property
    def name(self) -> str:
        return f"trix_cross_{self.direction}"

    @property
    def required_days(self) -> int:
        return self.period * 3 + self.signal_period + self.lookback_days + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        trix = _trix(data["close"], self.period)
        signal = trix.rolling(self.signal_period).mean()
        if self.direction == "bearish":
            cross_day = _crossed_down(trix, signal, self.lookback_days)
        else:
            cross_day = _crossed_up(trix, signal, self.lookback_days)
        return ConditionResult(matched=cross_day is not None, condition_name=self.name, details={"cross_day": cross_day})


@register_condition(
    key="aroon_trend_signal",
    label="Aroon Trend Signal",
    description="Aroon trend strength signal",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 25, "description": "Aroon period"},
        {"name": "min_aroon", "type": "float", "default": 70, "description": "Minimum trend level"},
        {"name": "direction", "type": "str", "default": "up", "description": "up|down"},
    ],
)
class AroonTrendSignalCondition(BaseCondition):
    def __init__(self, period: int = 25, min_aroon: float = 70, direction: str = "up"):
        self.period = period
        self.min_aroon = min_aroon
        self.direction = direction

    @property
    def name(self) -> str:
        return f"aroon_trend_{self.direction}"

    @property
    def required_days(self) -> int:
        return self.period + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        up, down = _aroon(data, self.period)
        curr_up = up.iloc[-1]
        curr_down = down.iloc[-1]
        if pd.isna(curr_up) or pd.isna(curr_down):
            return _insufficient(self.name)
        if self.direction == "down":
            matched = curr_down >= self.min_aroon and curr_down > curr_up
        else:
            matched = curr_up >= self.min_aroon and curr_up > curr_down
        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={"aroon_up": _safe_float(curr_up), "aroon_down": _safe_float(curr_down)},
        )


@register_condition(
    key="money_flow_index_signal",
    label="Money Flow Index",
    description="MFI threshold signal",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 14, "description": "MFI period"},
        {"name": "mode", "type": "str", "default": "oversold", "description": "oversold|overbought"},
        {"name": "oversold", "type": "float", "default": 20, "description": "Oversold threshold"},
        {"name": "overbought", "type": "float", "default": 80, "description": "Overbought threshold"},
    ],
)
class MoneyFlowIndexSignalCondition(BaseCondition):
    def __init__(self, period: int = 14, mode: str = "oversold", oversold: float = 20, overbought: float = 80):
        self.period = period
        self.mode = mode
        self.oversold = oversold
        self.overbought = overbought

    @property
    def name(self) -> str:
        return f"mfi_{self.mode}"

    @property
    def required_days(self) -> int:
        return self.period + 10

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        mfi = _money_flow_index(data, self.period)
        curr = mfi.iloc[-1]
        if pd.isna(curr):
            return _insufficient(self.name)
        if self.mode == "overbought":
            matched = curr >= self.overbought
        else:
            matched = curr <= self.oversold
        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={"mfi": _safe_float(curr), "mode": self.mode},
        )
