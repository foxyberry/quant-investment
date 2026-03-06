"""
Quant Indicator Conditions Batch 6
team:quant 지표 기반 조건
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseCondition, ConditionResult
from .registry import register_condition


def _insufficient(name: str) -> ConditionResult:
    return ConditionResult(matched=False, condition_name=name, details={"error": "Insufficient data"})


def _atr(data: pd.DataFrame, period: int) -> pd.Series:
    """ATR using Wilder's smoothing (industry standard)."""
    prev_close = data["close"].shift(1)
    tr = pd.concat(
        [
            (data["high"] - data["low"]).abs(),
            (data["high"] - prev_close).abs(),
            (data["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


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
    return plus_di, minus_di


def _vwap(data: pd.DataFrame, period: int) -> pd.Series:
    typical = (data["high"] + data["low"] + data["close"]) / 3.0
    pv = typical * data["volume"]
    return pv.rolling(period).sum() / data["volume"].rolling(period).sum().replace(0, np.nan)


def _cross_up(a: pd.Series, b: pd.Series, lookback_days: int) -> int | None:
    for i in range(1, lookback_days + 1):
        pa, pb = a.iloc[-(i + 1)], b.iloc[-(i + 1)]
        ca, cb = a.iloc[-i], b.iloc[-i]
        if any(pd.isna(v) for v in [pa, pb, ca, cb]):
            continue
        if pa <= pb and ca > cb:
            return i
    return None


@register_condition(
    key="vwap_cross_signal",
    label="VWAP Cross Signal",
    description="Close crossing above VWAP",
    category="volume",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "VWAP period"},
        {"name": "lookback_days", "type": "int", "default": 3, "description": "Lookback days"},
    ],
)
class VWAPCrossSignalCondition(BaseCondition):
    def __init__(self, period: int = 20, lookback_days: int = 3):
        self.period = period
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "vwap_cross_signal"

    @property
    def required_days(self) -> int:
        return self.period + self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        vwap = _vwap(data, self.period)
        close = data["close"]
        cross_day = None
        for i in range(1, self.lookback_days + 1):
            pc, pv = close.iloc[-(i + 1)], vwap.iloc[-(i + 1)]
            cc, cv = close.iloc[-i], vwap.iloc[-i]
            if any(pd.isna(v) for v in [pc, pv, cc, cv]):
                continue
            if pc <= pv and cc > cv:
                cross_day = i
                break
        return ConditionResult(matched=cross_day is not None, condition_name=self.name, details={"cross_day": cross_day})


@register_condition(
    key="vwap_distance_pct",
    label="VWAP Distance %",
    description="Distance between close and VWAP",
    category="volume",
    params=[
        {"name": "period", "type": "int", "default": 20, "description": "VWAP period"},
        {"name": "max_distance_pct", "type": "float", "default": 5.0, "description": "Max absolute distance %"},
    ],
)
class VWAPDistancePctCondition(BaseCondition):
    def __init__(self, period: int = 20, max_distance_pct: float = 5.0):
        self.period = period
        self.max_distance_pct = max_distance_pct

    @property
    def name(self) -> str:
        return "vwap_distance_pct"

    @property
    def required_days(self) -> int:
        return self.period + 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        vwap = _vwap(data, self.period).iloc[-1]
        close = data["close"].iloc[-1]
        if pd.isna(vwap) or pd.isna(close) or vwap == 0:
            return _insufficient(self.name)
        distance = float(abs((close - vwap) / vwap) * 100.0)
        return ConditionResult(matched=distance <= self.max_distance_pct, condition_name=self.name, details={"distance_pct": distance})


@register_condition(
    key="relative_volume_percentile",
    label="Relative Volume Percentile",
    description="Current volume percentile within lookback",
    category="volume",
    params=[
        {"name": "lookback_days", "type": "int", "default": 60, "description": "Lookback days"},
        {"name": "min_percentile", "type": "float", "default": 70.0, "description": "Min percentile"},
    ],
)
class RelativeVolumePercentileCondition(BaseCondition):
    def __init__(self, lookback_days: int = 60, min_percentile: float = 70.0):
        self.lookback_days = lookback_days
        self.min_percentile = min_percentile

    @property
    def name(self) -> str:
        return "relative_volume_percentile"

    @property
    def required_days(self) -> int:
        return self.lookback_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        vols = data["volume"].tail(self.lookback_days)
        curr = vols.iloc[-1]
        if pd.isna(curr):
            return _insufficient(self.name)
        percentile = float((vols <= curr).mean() * 100.0)
        return ConditionResult(matched=percentile >= self.min_percentile, condition_name=self.name, details={"percentile": percentile})


@register_condition(
    key="turnover_ratio_min",
    label="Turnover Ratio Min",
    description="Minimum turnover ratio",
    category="volume",
    params=[
        {"name": "min_turnover_ratio", "type": "float", "default": 0.01, "description": "Minimum turnover ratio"},
    ],
)
class TurnoverRatioMinCondition(BaseCondition):
    def __init__(self, min_turnover_ratio: float = 0.01):
        self.min_turnover_ratio = min_turnover_ratio

    @property
    def name(self) -> str:
        return "turnover_ratio_min"

    @property
    def required_days(self) -> int:
        return 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < 1:
            return _insufficient(self.name)
        vol = pd.to_numeric(data["volume"].iloc[-1], errors="coerce")
        if pd.isna(vol):
            return _insufficient(self.name)

        # Try DataFrame column first (for tests / pre-enriched data),
        # then fall back to yfinance info API (cached via @lru_cache).
        shares = None
        if "shares_outstanding" in data.columns:
            shares = pd.to_numeric(data["shares_outstanding"].iloc[-1], errors="coerce")

        if shares is None or pd.isna(shares) or shares <= 0:
            try:
                from .fundamental import _get_info
                info = _get_info(ticker)
                raw = info.get("sharesOutstanding")
                if raw is not None:
                    shares = pd.to_numeric(raw, errors="coerce")
            except Exception as exc:
                import logging
                logging.getLogger(__name__).debug(
                    "yfinance fallback failed for %s: %s", ticker, exc,
                )

        if shares is None or pd.isna(shares) or shares <= 0:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "No shares outstanding data"},
            )

        ratio = float(vol / shares)
        return ConditionResult(matched=ratio >= self.min_turnover_ratio, condition_name=self.name, details={"turnover_ratio": ratio})


@register_condition(
    key="atr_percentile_filter",
    label="ATR Percentile",
    description="ATR percentile within lookback",
    category="risk",
    params=[
        {"name": "atr_period", "type": "int", "default": 14, "description": "ATR period"},
        {"name": "lookback_days", "type": "int", "default": 120, "description": "Lookback days"},
        {"name": "max_percentile", "type": "float", "default": 80.0, "description": "Max percentile"},
    ],
)
class ATRPercentileFilterCondition(BaseCondition):
    def __init__(self, atr_period: int = 14, lookback_days: int = 120, max_percentile: float = 80.0):
        self.atr_period = atr_period
        self.lookback_days = lookback_days
        self.max_percentile = max_percentile

    @property
    def name(self) -> str:
        return "atr_percentile_filter"

    @property
    def required_days(self) -> int:
        return self.lookback_days + self.atr_period + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        atr = _atr(data, self.atr_period).tail(self.lookback_days)
        curr = atr.iloc[-1]
        if pd.isna(curr):
            return _insufficient(self.name)
        percentile = float((atr <= curr).mean() * 100.0)
        return ConditionResult(matched=percentile <= self.max_percentile, condition_name=self.name, details={"percentile": percentile})


@register_condition(
    key="atr_expansion_breakout",
    label="ATR Expansion Breakout",
    description="ATR expansion and price breakout",
    category="risk",
    params=[
        {"name": "atr_period", "type": "int", "default": 14, "description": "ATR period"},
        {"name": "atr_multiplier", "type": "float", "default": 1.2, "description": "ATR expansion multiple"},
        {"name": "breakout_lookback", "type": "int", "default": 20, "description": "Breakout lookback"},
    ],
)
class ATRExpansionBreakoutCondition(BaseCondition):
    def __init__(self, atr_period: int = 14, atr_multiplier: float = 1.2, breakout_lookback: int = 20):
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.breakout_lookback = breakout_lookback

    @property
    def name(self) -> str:
        return "atr_expansion_breakout"

    @property
    def required_days(self) -> int:
        return self.atr_period + self.breakout_lookback + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        atr = _atr(data, self.atr_period)
        curr_atr = atr.iloc[-1]
        prev_atr_avg = atr.iloc[-(self.breakout_lookback + 1):-1].mean()
        prev_high = data["high"].iloc[-(self.breakout_lookback + 1):-1].max()
        close = data["close"].iloc[-1]
        if any(pd.isna(v) for v in [curr_atr, prev_atr_avg, prev_high, close]):
            return _insufficient(self.name)
        atr_expanded = curr_atr >= (prev_atr_avg * self.atr_multiplier)
        breakout = close > prev_high
        return ConditionResult(matched=bool(atr_expanded and breakout), condition_name=self.name, details={"atr_expanded": bool(atr_expanded), "breakout": bool(breakout)})


@register_condition(
    key="natr_filter",
    label="NATR Filter",
    description="Normalized ATR filter",
    category="risk",
    params=[
        {"name": "period", "type": "int", "default": 14, "description": "ATR period"},
        {"name": "max_natr_pct", "type": "float", "default": 5.0, "description": "Max NATR %"},
    ],
)
class NATRFilterCondition(BaseCondition):
    def __init__(self, period: int = 14, max_natr_pct: float = 5.0):
        self.period = period
        self.max_natr_pct = max_natr_pct

    @property
    def name(self) -> str:
        return "natr_filter"

    @property
    def required_days(self) -> int:
        return self.period + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        atr = _atr(data, self.period).iloc[-1]
        close = data["close"].iloc[-1]
        if pd.isna(atr) or pd.isna(close) or close == 0:
            return _insufficient(self.name)
        natr = float((atr / close) * 100.0)
        return ConditionResult(matched=natr <= self.max_natr_pct, condition_name=self.name, details={"natr_pct": natr})


@register_condition(
    key="dmi_directional_cross",
    label="DMI Directional Cross",
    description="+DI crosses above -DI",
    category="momentum",
    params=[
        {"name": "period", "type": "int", "default": 14, "description": "DMI period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
    ],
)
class DMIDirectionalCrossCondition(BaseCondition):
    def __init__(self, period: int = 14, lookback_days: int = 5):
        self.period = period
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "dmi_directional_cross"

    @property
    def required_days(self) -> int:
        return self.period + self.lookback_days + 5

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        plus_di, minus_di = _adx(data, self.period)
        day = _cross_up(plus_di, minus_di, self.lookback_days)
        return ConditionResult(matched=day is not None, condition_name=self.name, details={"cross_day": day})


@register_condition(
    key="ichimoku_cloud_breakout",
    label="Ichimoku Cloud Breakout",
    description="Close above cloud upper",
    category="momentum",
    params=[
        {"name": "conversion_period", "type": "int", "default": 9, "description": "Tenkan period"},
        {"name": "base_period", "type": "int", "default": 26, "description": "Kijun period"},
        {"name": "span_b_period", "type": "int", "default": 52, "description": "Senkou B period"},
    ],
)
class IchimokuCloudBreakoutCondition(BaseCondition):
    def __init__(self, conversion_period: int = 9, base_period: int = 26, span_b_period: int = 52):
        self.conversion_period = conversion_period
        self.base_period = base_period
        self.span_b_period = span_b_period

    @property
    def name(self) -> str:
        return "ichimoku_cloud_breakout"

    @property
    def required_days(self) -> int:
        return self.span_b_period + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        tenkan = (data["high"].rolling(self.conversion_period).max() + data["low"].rolling(self.conversion_period).min()) / 2
        kijun = (data["high"].rolling(self.base_period).max() + data["low"].rolling(self.base_period).min()) / 2
        span_a = (tenkan + kijun) / 2
        span_b = (data["high"].rolling(self.span_b_period).max() + data["low"].rolling(self.span_b_period).min()) / 2
        cloud_top = max(span_a.iloc[-1], span_b.iloc[-1])
        close = data["close"].iloc[-1]
        if pd.isna(cloud_top) or pd.isna(close):
            return _insufficient(self.name)
        return ConditionResult(matched=bool(close > cloud_top), condition_name=self.name, details={"cloud_top": float(cloud_top), "close": float(close)})


@register_condition(
    key="ichimoku_tenkan_kijun_cross",
    label="Ichimoku Tenkan/Kijun Cross",
    description="Tenkan crosses above Kijun",
    category="momentum",
    params=[
        {"name": "conversion_period", "type": "int", "default": 9, "description": "Tenkan period"},
        {"name": "base_period", "type": "int", "default": 26, "description": "Kijun period"},
        {"name": "lookback_days", "type": "int", "default": 5, "description": "Lookback days"},
    ],
)
class IchimokuTenkanKijunCrossCondition(BaseCondition):
    def __init__(self, conversion_period: int = 9, base_period: int = 26, lookback_days: int = 5):
        self.conversion_period = conversion_period
        self.base_period = base_period
        self.lookback_days = lookback_days

    @property
    def name(self) -> str:
        return "ichimoku_tenkan_kijun_cross"

    @property
    def required_days(self) -> int:
        return self.base_period + self.lookback_days + 2

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        if len(data) < self.required_days:
            return _insufficient(self.name)
        tenkan = (data["high"].rolling(self.conversion_period).max() + data["low"].rolling(self.conversion_period).min()) / 2
        kijun = (data["high"].rolling(self.base_period).max() + data["low"].rolling(self.base_period).min()) / 2
        day = _cross_up(tenkan, kijun, self.lookback_days)
        return ConditionResult(matched=day is not None, condition_name=self.name, details={"cross_day": day})
