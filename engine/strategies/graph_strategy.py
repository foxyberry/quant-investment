"""
Graph-based backtesting strategy.

Converts QuantCanvas condition graphs into a Backtesting.py Strategy.
Uses a single GraphBacktestStrategy with compiled signal functions.

Each compiled condition stores indicators in strategy._ind[key] to avoid
attribute name collisions when the same condition type is used multiple times.

Supported condition types (1st release):
  - MA: ma_touch, above_ma, below_ma, ma_cross_up, ma_cross_down
  - RSI: rsi_oversold, rsi_overbought, rsi_range
  - MACD: macd_cross_up, macd_cross_down
  - BB: bb_lower_touch, bb_upper_touch
  - Volume: min_volume, volume_above_avg

Unsupported conditions (fundamental, pairs, etc.) are skipped with warnings.
"""

import uuid
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover


# ---------------------------------------------------------------------------
# Indicator helper functions (used with Strategy.I())
# ---------------------------------------------------------------------------

def SMA(values: pd.Series, n: int) -> pd.Series:
    return values.rolling(n).mean()


def EMA(values: pd.Series, n: int) -> pd.Series:
    return values.ewm(span=n, adjust=False).mean()


def RSI(values: pd.Series, period: int = 14) -> pd.Series:
    """RSI using Wilder's smoothing (industry standard)."""
    delta = values.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def MACD_LINE(values: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
    return EMA(values, fast) - EMA(values, slow)


def MACD_SIGNAL(values: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    macd = MACD_LINE(values, fast, slow)
    return EMA(macd, signal)


def BB_UPPER(values: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    sma = values.rolling(period).mean()
    std = values.rolling(period).std()
    return sma + std_dev * std


def BB_LOWER(values: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    sma = values.rolling(period).mean()
    std = values.rolling(period).std()
    return sma - std_dev * std


def VOLUME_SMA(volume: pd.Series, period: int = 20) -> pd.Series:
    return volume.rolling(period).mean()


# ---------------------------------------------------------------------------
# Signal compilers: condition_type + params -> (init_fn, entry_fn, exit_fn)
# Each compiler receives a unique `key` to store indicators without collision.
# ---------------------------------------------------------------------------

class SignalSpec:
    """Compiled signal specification for a single condition."""

    def __init__(
        self,
        condition_type: str,
        init_fn: Callable,
        entry_fn: Callable,
        exit_fn: Optional[Callable] = None,
    ):
        self.condition_type = condition_type
        self.init_fn = init_fn
        self.entry_fn = entry_fn
        self.exit_fn = exit_fn


def _unique_key() -> str:
    return uuid.uuid4().hex[:8]


def _safe_int(value: Any, default: int, min_val: int = 1, max_val: int = 1000) -> int:
    """Safely parse an integer parameter with bounds."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_val, min(v, max_val))


def _safe_float(value: Any, default: float, min_val: float = 0.0, max_val: float = 1e6) -> float:
    """Safely parse a float parameter with bounds."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(v) or np.isinf(v):
        return default
    return max(min_val, min(v, max_val))


def compile_condition(condition_type: str, params: Dict[str, Any]) -> Optional[SignalSpec]:
    """Compile a condition_type + params into a SignalSpec.

    Returns None if the condition is not supported for backtesting.
    Parameters are validated and clamped to safe ranges.
    """
    compiler = CONDITION_COMPILERS.get(condition_type)
    if compiler is None:
        return None
    return compiler(params)


# --- MA conditions ---

def _compile_ma_cross_up(params: Dict[str, Any]) -> SignalSpec:
    short_p = _safe_int(params.get("short_period", 20), 20, min_val=2)
    long_p = _safe_int(params.get("long_period", 60), 60, min_val=2)
    if short_p >= long_p:
        short_p, long_p = min(short_p, long_p), max(short_p, long_p) + 1
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[f"short_{k}"] = strategy.I(SMA, close, short_p, name=f"SMA_{short_p}_{k}")
        strategy._ind[f"long_{k}"] = strategy.I(SMA, close, long_p, name=f"SMA_{long_p}_{k}")

    def entry_fn(strategy) -> bool:
        return crossover(strategy._ind[f"short_{k}"], strategy._ind[f"long_{k}"])

    def exit_fn(strategy) -> bool:
        return crossover(strategy._ind[f"long_{k}"], strategy._ind[f"short_{k}"])

    return SignalSpec("ma_cross_up", init_fn, entry_fn, exit_fn)


def _compile_ma_cross_down(params: Dict[str, Any]) -> SignalSpec:
    short_p = _safe_int(params.get("short_period", 20), 20, min_val=2)
    long_p = _safe_int(params.get("long_period", 60), 60, min_val=2)
    if short_p >= long_p:
        short_p, long_p = min(short_p, long_p), max(short_p, long_p) + 1
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[f"short_{k}"] = strategy.I(SMA, close, short_p, name=f"SMA_d_{short_p}_{k}")
        strategy._ind[f"long_{k}"] = strategy.I(SMA, close, long_p, name=f"SMA_d_{long_p}_{k}")

    def entry_fn(strategy) -> bool:
        return crossover(strategy._ind[f"long_{k}"], strategy._ind[f"short_{k}"])

    def exit_fn(strategy) -> bool:
        return crossover(strategy._ind[f"short_{k}"], strategy._ind[f"long_{k}"])

    return SignalSpec("ma_cross_down", init_fn, entry_fn, exit_fn)


def _compile_above_ma(params: Dict[str, Any]) -> SignalSpec:
    period = _safe_int(params.get("period", 20), 20, min_val=2)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[k] = strategy.I(SMA, close, period, name=f"MA_{period}_{k}")

    def entry_fn(strategy) -> bool:
        return strategy.data.Close[-1] > strategy._ind[k][-1]

    def exit_fn(strategy) -> bool:
        return strategy.data.Close[-1] < strategy._ind[k][-1]

    return SignalSpec("above_ma", init_fn, entry_fn, exit_fn)


def _compile_below_ma(params: Dict[str, Any]) -> SignalSpec:
    period = _safe_int(params.get("period", 20), 20, min_val=2)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[k] = strategy.I(SMA, close, period, name=f"MA_below_{period}_{k}")

    def entry_fn(strategy) -> bool:
        return strategy.data.Close[-1] < strategy._ind[k][-1]

    def exit_fn(strategy) -> bool:
        return strategy.data.Close[-1] > strategy._ind[k][-1]

    return SignalSpec("below_ma", init_fn, entry_fn, exit_fn)


def _compile_ma_touch(params: Dict[str, Any]) -> SignalSpec:
    period = _safe_int(params.get("period", 20), 20, min_val=2)
    threshold = _safe_float(params.get("threshold", 0.02), 0.02, min_val=0.001, max_val=0.5)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[k] = strategy.I(SMA, close, period, name=f"MA_touch_{period}_{k}")

    def entry_fn(strategy) -> bool:
        price = strategy.data.Close[-1]
        ma = strategy._ind[k][-1]
        if np.isnan(ma) or ma == 0:
            return False
        if len(strategy.data.Close) < 2:
            return False
        prev_price = strategy.data.Close[-2]
        prev_ma = strategy._ind[k][-2]
        if np.isnan(prev_ma):
            return False
        return prev_price < prev_ma and abs(price - ma) / ma < threshold

    return SignalSpec("ma_touch", init_fn, entry_fn, None)


# --- RSI conditions ---

def _compile_rsi_oversold(params: Dict[str, Any]) -> SignalSpec:
    threshold = _safe_float(params.get("threshold", 30), 30, min_val=1, max_val=99)
    period = _safe_int(params.get("period", 14), 14, min_val=2)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[k] = strategy.I(RSI, close, period, name=f"RSI_{period}_{k}")

    def entry_fn(strategy) -> bool:
        v = strategy._ind[k][-1]
        return not np.isnan(v) and v <= threshold

    def exit_fn(strategy) -> bool:
        v = strategy._ind[k][-1]
        return not np.isnan(v) and v >= 70

    return SignalSpec("rsi_oversold", init_fn, entry_fn, exit_fn)


def _compile_rsi_overbought(params: Dict[str, Any]) -> SignalSpec:
    threshold = _safe_float(params.get("threshold", 70), 70, min_val=1, max_val=99)
    period = _safe_int(params.get("period", 14), 14, min_val=2)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[k] = strategy.I(RSI, close, period, name=f"RSI_ob_{period}_{k}")

    def entry_fn(strategy) -> bool:
        return False  # Overbought is exit-only for long strategies

    def exit_fn(strategy) -> bool:
        v = strategy._ind[k][-1]
        return not np.isnan(v) and v >= threshold

    return SignalSpec("rsi_overbought", init_fn, entry_fn, exit_fn)


def _compile_rsi_range(params: Dict[str, Any]) -> SignalSpec:
    lower = _safe_float(params.get("lower", 30), 30, min_val=0, max_val=100)
    upper = _safe_float(params.get("upper", 70), 70, min_val=0, max_val=100)
    if lower > upper:
        lower, upper = upper, lower
    period = _safe_int(params.get("period", 14), 14, min_val=2)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[k] = strategy.I(RSI, close, period, name=f"RSI_range_{period}_{k}")

    def entry_fn(strategy) -> bool:
        v = strategy._ind[k][-1]
        return not np.isnan(v) and lower <= v <= upper

    return SignalSpec("rsi_range", init_fn, entry_fn, None)


# --- MACD conditions ---

def _compile_macd_cross_up(params: Dict[str, Any]) -> SignalSpec:
    fast = _safe_int(params.get("fast_period", 12), 12, min_val=2)
    slow = _safe_int(params.get("slow_period", 26), 26, min_val=2)
    signal = _safe_int(params.get("signal_period", 9), 9, min_val=2)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[f"ml_{k}"] = strategy.I(MACD_LINE, close, fast, slow, name=f"MACD_{k}")
        strategy._ind[f"ms_{k}"] = strategy.I(MACD_SIGNAL, close, fast, slow, signal, name=f"MACD_Sig_{k}")

    def entry_fn(strategy) -> bool:
        return crossover(strategy._ind[f"ml_{k}"], strategy._ind[f"ms_{k}"])

    def exit_fn(strategy) -> bool:
        return crossover(strategy._ind[f"ms_{k}"], strategy._ind[f"ml_{k}"])

    return SignalSpec("macd_cross_up", init_fn, entry_fn, exit_fn)


def _compile_macd_cross_down(params: Dict[str, Any]) -> SignalSpec:
    fast = _safe_int(params.get("fast_period", 12), 12, min_val=2)
    slow = _safe_int(params.get("slow_period", 26), 26, min_val=2)
    signal = _safe_int(params.get("signal_period", 9), 9, min_val=2)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[f"ml_{k}"] = strategy.I(MACD_LINE, close, fast, slow, name=f"MACD_d_{k}")
        strategy._ind[f"ms_{k}"] = strategy.I(MACD_SIGNAL, close, fast, slow, signal, name=f"MACD_Sig_d_{k}")

    def entry_fn(strategy) -> bool:
        return crossover(strategy._ind[f"ms_{k}"], strategy._ind[f"ml_{k}"])

    def exit_fn(strategy) -> bool:
        return crossover(strategy._ind[f"ml_{k}"], strategy._ind[f"ms_{k}"])

    return SignalSpec("macd_cross_down", init_fn, entry_fn, exit_fn)


# --- BB conditions ---

def _compile_bb_lower_touch(params: Dict[str, Any]) -> SignalSpec:
    period = _safe_int(params.get("period", 20), 20, min_val=2)
    std_dev = _safe_float(params.get("std_dev", 2.0), 2.0, min_val=0.1, max_val=5.0)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[f"bbl_{k}"] = strategy.I(BB_LOWER, close, period, std_dev, name=f"BB_Lower_{k}")
        strategy._ind[f"bbu_{k}"] = strategy.I(BB_UPPER, close, period, std_dev, name=f"BB_Upper_{k}")

    def entry_fn(strategy) -> bool:
        return strategy.data.Close[-1] <= strategy._ind[f"bbl_{k}"][-1]

    def exit_fn(strategy) -> bool:
        return strategy.data.Close[-1] >= strategy._ind[f"bbu_{k}"][-1]

    return SignalSpec("bb_lower_touch", init_fn, entry_fn, exit_fn)


def _compile_bb_upper_touch(params: Dict[str, Any]) -> SignalSpec:
    period = _safe_int(params.get("period", 20), 20, min_val=2)
    std_dev = _safe_float(params.get("std_dev", 2.0), 2.0, min_val=0.1, max_val=5.0)
    k = _unique_key()

    def init_fn(strategy):
        close = pd.Series(strategy.data.Close)
        strategy._ind[f"bbu_{k}"] = strategy.I(BB_UPPER, close, period, std_dev, name=f"BB_Upper_t_{k}")

    def entry_fn(strategy) -> bool:
        return False  # Upper touch is exit-only for long strategies

    def exit_fn(strategy) -> bool:
        return strategy.data.Close[-1] >= strategy._ind[f"bbu_{k}"][-1]

    return SignalSpec("bb_upper_touch", init_fn, entry_fn, exit_fn)


# --- Volume conditions ---

def _compile_min_volume(params: Dict[str, Any]) -> SignalSpec:
    min_vol = _safe_int(params.get("min_volume", 100000), 100000, min_val=0, max_val=10**9)

    def init_fn(strategy):
        pass

    def entry_fn(strategy) -> bool:
        return strategy.data.Volume[-1] >= min_vol

    return SignalSpec("min_volume", init_fn, entry_fn, None)


def _compile_volume_above_avg(params: Dict[str, Any]) -> SignalSpec:
    period = _safe_int(params.get("period", 20), 20, min_val=2)
    multiplier = _safe_float(params.get("multiplier", 1.5), 1.5, min_val=0.1, max_val=100.0)
    k = _unique_key()

    def init_fn(strategy):
        vol = pd.Series(strategy.data.Volume, dtype=float)
        strategy._ind[k] = strategy.I(VOLUME_SMA, vol, period, name=f"Vol_SMA_{period}_{k}")

    def entry_fn(strategy) -> bool:
        avg = strategy._ind[k][-1]
        if np.isnan(avg) or avg == 0:
            return False
        return strategy.data.Volume[-1] >= avg * multiplier

    return SignalSpec("volume_above_avg", init_fn, entry_fn, None)


# ---------------------------------------------------------------------------
# Condition compiler registry
# ---------------------------------------------------------------------------

CONDITION_COMPILERS: Dict[str, Callable] = {
    "ma_cross_up": _compile_ma_cross_up,
    "ma_cross_down": _compile_ma_cross_down,
    "above_ma": _compile_above_ma,
    "below_ma": _compile_below_ma,
    "ma_touch": _compile_ma_touch,
    "rsi_oversold": _compile_rsi_oversold,
    "rsi_overbought": _compile_rsi_overbought,
    "rsi_range": _compile_rsi_range,
    "macd_cross_up": _compile_macd_cross_up,
    "macd_cross_down": _compile_macd_cross_down,
    "bb_lower_touch": _compile_bb_lower_touch,
    "bb_upper_touch": _compile_bb_upper_touch,
    "min_volume": _compile_min_volume,
    "volume_above_avg": _compile_volume_above_avg,
}

SUPPORTED_CONDITION_TYPES = set(CONDITION_COMPILERS.keys())


# ---------------------------------------------------------------------------
# GraphBacktestStrategy — single fixed Strategy class with injected signals
# ---------------------------------------------------------------------------

class GraphBacktestStrategy(Strategy):
    """Backtesting strategy compiled from a QuantCanvas condition graph.

    Class attributes are injected before running:
      - _signal_specs: List[SignalSpec]
      - _logic_operator: str — 'and' or 'or'
      - _take_profit: Optional[float]
      - _stop_loss: Optional[float]
    """

    _signal_specs: List[SignalSpec] = []
    _logic_operator: str = "and"
    _take_profit: Optional[float] = None
    _stop_loss: Optional[float] = None

    def init(self):
        self._ind: Dict[str, Any] = {}
        for spec in self._signal_specs:
            spec.init_fn(self)
        self._entry_price = None

    def next(self):
        if len(self.data.Close) < 2:
            return

        # Compute entry signals
        entry_signals = []
        for spec in self._signal_specs:
            try:
                entry_signals.append(spec.entry_fn(self))
            except (IndexError, ValueError):
                entry_signals.append(False)

        if not entry_signals:
            return

        if self._logic_operator == "or":
            should_enter = any(entry_signals)
        else:  # "and"
            should_enter = all(entry_signals)

        if not self.position:
            if should_enter:
                self.buy()
                self._entry_price = self.data.Close[-1]
        else:
            # Check TP/SL first
            if self._entry_price is not None:
                price = self.data.Close[-1]
                pnl = (price - self._entry_price) / self._entry_price

                if self._take_profit is not None and pnl >= self._take_profit:
                    self.position.close()
                    self._entry_price = None
                    return
                if self._stop_loss is not None and pnl <= -self._stop_loss:
                    self.position.close()
                    self._entry_price = None
                    return

            # Check exit signals (any exit triggers close)
            exit_signals = []
            for spec in self._signal_specs:
                if spec.exit_fn is not None:
                    try:
                        exit_signals.append(spec.exit_fn(self))
                    except (IndexError, ValueError):
                        exit_signals.append(False)

            if exit_signals and any(exit_signals):
                self.position.close()
                self._entry_price = None
