"""
L2: Differential tests — compare our indicator implementations against pandas_ta reference.

Tests verify numeric agreement within documented tolerances.

Known algorithmic differences:
- RSI: We use SMA smoothing; pandas_ta uses Wilder's EMA. Values diverge significantly.
  For RSI we verify self-consistency (our compute matches manual SMA reference).
- ATR: We use SMA of True Range; pandas_ta uses Wilder's EMA.
  For ATR we verify self-consistency.
- Bollinger Bands: We use ddof=0 (population std); pandas_ta uses ddof=1 (sample std).
  Verified by passing ddof=0 to pandas manually.
- Stochastic: We compute raw (fast) %K; pandas_ta smooth_k=3 by default.
  Matched exactly when using smooth_k=1.

For indicators that SHOULD match pandas_ta (SMA, EMA, MACD, Stochastic):
we assert tight numeric tolerances.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta
import pytest

from screener.conditions.momentum import _ema, _macd
from screener.conditions.quant_indicators import _atr
from screener.conditions.quant_oscillators import _stochastic_k
from screener.conditions.rsi import calculate_rsi
from tests.fixtures.synthetic_data import build_fixture

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_DATA = build_fixture("random_walk", 200, "price_volume", seed=42)
_CLOSE = _DATA["close"]
_HIGH = _DATA["high"]
_LOW = _DATA["low"]


# ---------------------------------------------------------------------------
# Exact-match indicators (SMA, EMA)
# ---------------------------------------------------------------------------


class TestSMADifferential:
    """SMA: our rolling mean must exactly match pandas_ta.sma."""

    @pytest.mark.parametrize("period", [5, 10, 20, 50, 100])
    def test_sma_matches_pandas_ta(self, period: int):
        ours = _CLOSE.rolling(period).mean()
        ref = ta.sma(_CLOSE, length=period)
        diff = (ours - ref).dropna().abs()
        assert diff.max() < 1e-10, f"SMA({period}) max diff: {diff.max()}"


class TestEMADifferential:
    """EMA: our ewm(adjust=False) converges to pandas_ta.ema at tail.

    Initialization differences cause divergence early on; convergence improves
    over time. Longer periods converge slower.
    """

    @pytest.mark.parametrize("period", [9, 12, 20, 26, 50])
    def test_ema_converges_at_tail(self, period: int):
        ours = _ema(_CLOSE, period)
        ref = ta.ema(_CLOSE, length=period)
        # Check last 10 values — these should be well-converged
        tail_diff = (ours.tail(10) - ref.tail(10)).abs()
        assert tail_diff.max() < 0.01, f"EMA({period}) tail-10 diff: {tail_diff.max()}"

    @pytest.mark.parametrize("period", [9, 12, 20])
    def test_ema_short_period_tight(self, period: int):
        """Short-period EMAs converge faster; tighter tolerance."""
        ours = _ema(_CLOSE, period)
        ref = ta.ema(_CLOSE, length=period)
        tail_diff = (ours.tail(50) - ref.tail(50)).abs()
        assert tail_diff.max() < 0.005, f"EMA({period}) tail-50 diff: {tail_diff.max()}"


# ---------------------------------------------------------------------------
# Near-exact indicators (MACD, Stochastic)
# ---------------------------------------------------------------------------


class TestMACDDifferential:
    """MACD: our implementation closely matches pandas_ta.

    EMA initialization differences cascade through MACD → Signal → Histogram.
    Tail values converge; we use last 50 bars for tighter checks.
    """

    def test_macd_line_converges(self):
        our_macd, _, _ = _macd(_CLOSE, 12, 26, 9)
        ref = ta.macd(_CLOSE, fast=12, slow=26, signal=9)
        ref_macd = ref[[c for c in ref.columns if "MACD_" in c][0]]
        diff = (our_macd.tail(50) - ref_macd.tail(50)).abs()
        assert diff.max() < 0.0002, f"MACD line tail-50 diff: {diff.max()}"

    def test_macd_signal_converges(self):
        _, our_signal, _ = _macd(_CLOSE, 12, 26, 9)
        ref = ta.macd(_CLOSE, fast=12, slow=26, signal=9)
        ref_signal = ref[[c for c in ref.columns if "MACDs" in c][0]]
        diff = (our_signal.tail(50) - ref_signal.tail(50)).abs()
        assert diff.max() < 0.0002, f"MACD signal tail-50 diff: {diff.max()}"

    def test_macd_histogram_converges(self):
        _, _, our_hist = _macd(_CLOSE, 12, 26, 9)
        ref = ta.macd(_CLOSE, fast=12, slow=26, signal=9)
        ref_hist = ref[[c for c in ref.columns if "MACDh" in c][0]]
        diff = (our_hist.tail(50) - ref_hist.tail(50)).abs()
        assert diff.max() < 0.0002, f"MACD hist tail-50 diff: {diff.max()}"


class TestStochasticDifferential:
    """Stochastic: raw %K and SMA %D must match pandas_ta (smooth_k=1)."""

    @pytest.mark.parametrize("k_period,d_period", [(14, 3), (5, 3), (21, 5)])
    def test_stochastic_k_matches(self, k_period: int, d_period: int):
        our_k = _stochastic_k(_DATA, k_period)
        ref = ta.stoch(_HIGH, _LOW, _CLOSE, k=k_period, d=d_period, smooth_k=1)
        ref_k = ref.iloc[:, 0]
        diff = (our_k - ref_k).dropna().abs()
        assert diff.max() < 1e-10, f"Stoch K({k_period}) diff: {diff.max()}"

    @pytest.mark.parametrize("k_period,d_period", [(14, 3), (5, 3)])
    def test_stochastic_d_matches(self, k_period: int, d_period: int):
        our_k = _stochastic_k(_DATA, k_period)
        our_d = our_k.rolling(d_period).mean()
        ref = ta.stoch(_HIGH, _LOW, _CLOSE, k=k_period, d=d_period, smooth_k=1)
        ref_d = ref.iloc[:, 1]
        diff = (our_d - ref_d).dropna().abs()
        assert diff.max() < 1e-10, f"Stoch D({k_period},{d_period}) diff: {diff.max()}"


# ---------------------------------------------------------------------------
# Self-consistency tests (RSI, ATR, Bollinger)
# These use SMA-based algorithms intentionally different from pandas_ta.
# We verify correctness against a manual reference with the SAME algorithm.
# ---------------------------------------------------------------------------


class TestRSISelfConsistency:
    """RSI: verify our SMA-based RSI matches manual SMA reference exactly."""

    @pytest.mark.parametrize("period", [7, 14, 21])
    def test_rsi_matches_manual_sma_reference(self, period: int):
        """Our calculate_rsi must match hand-coded SMA-based RSI."""
        ours = calculate_rsi(_CLOSE, period)
        # Manual reference (same SMA algorithm)
        delta = _CLOSE.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        manual = 100 - (100 / (1 + gain / loss))
        diff = (ours - manual).dropna().abs()
        assert diff.max() < 1e-12, f"RSI({period}) self-consistency diff: {diff.max()}"

    def test_rsi_diverges_from_wilder(self):
        """Document that SMA-based RSI differs from Wilder's (pandas_ta default)."""
        ours = calculate_rsi(_CLOSE, 14)
        ref = ta.rsi(_CLOSE, length=14)
        # They should NOT match — this proves the implementations differ
        diff = (ours - ref).dropna().abs()
        assert diff.max() > 1.0, (
            "RSI unexpectedly matches pandas_ta Wilder's — implementation may have changed"
        )

    @pytest.mark.parametrize("period", [7, 14, 21])
    def test_rsi_range_0_to_100(self, period: int):
        """RSI must always be in [0, 100]."""
        rsi = calculate_rsi(_CLOSE, period).dropna()
        assert (rsi >= 0).all(), f"RSI({period}) has values < 0"
        assert (rsi <= 100).all(), f"RSI({period}) has values > 100"


class TestATRSelfConsistency:
    """ATR: verify our SMA-based ATR matches manual SMA of True Range."""

    @pytest.mark.parametrize("period", [7, 14, 21])
    def test_atr_matches_manual_sma_reference(self, period: int):
        ours = _atr(_DATA, period)
        # Manual reference: SMA of True Range
        prev_close = _CLOSE.shift(1)
        tr = pd.concat(
            [
                (_HIGH - _LOW).abs(),
                (_HIGH - prev_close).abs(),
                (_LOW - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        manual = tr.rolling(period).mean()
        diff = (ours - manual).dropna().abs()
        assert diff.max() < 1e-12, f"ATR({period}) self-consistency diff: {diff.max()}"

    def test_atr_diverges_from_wilder(self):
        """Document that SMA-based ATR differs from Wilder's (pandas_ta default)."""
        ours = _atr(_DATA, 14)
        ref = ta.atr(_HIGH, _LOW, _CLOSE, length=14)
        diff = (ours - ref).dropna().abs()
        assert diff.max() > 0.05, (
            "ATR unexpectedly matches pandas_ta Wilder's — implementation may have changed"
        )

    @pytest.mark.parametrize("period", [7, 14, 21])
    def test_atr_always_positive(self, period: int):
        atr = _atr(_DATA, period).dropna()
        assert (atr > 0).all(), f"ATR({period}) has non-positive values"


class TestBollingerSelfConsistency:
    """Bollinger Bands: verify our ddof=0 implementation."""

    @pytest.mark.parametrize("period,std_mult", [(20, 2.0), (10, 1.5), (50, 2.5)])
    def test_bollinger_percent_b_matches_manual(self, period: int, std_mult: float):
        """Verify BollingerPercentBCondition.evaluate() matches manual ddof=0 calc."""
        from screener.conditions.quant_oscillators import BollingerPercentBCondition

        cond = BollingerPercentBCondition(
            period=period, std_mult=std_mult, min_percent_b=-1.0, max_percent_b=2.0
        )
        result = cond.evaluate("TEST", _DATA)

        # Manual reference using same ddof=0
        ma = _CLOSE.rolling(period).mean().iloc[-1]
        std = _CLOSE.rolling(period).std(ddof=0).iloc[-1]
        upper = ma + std_mult * std
        lower = ma - std_mult * std
        expected_pct_b = float((_CLOSE.iloc[-1] - lower) / (upper - lower))

        assert abs(result.details["percent_b"] - expected_pct_b) < 1e-9, (
            f"BollingerPercentB({period},{std_mult}): "
            f"got {result.details['percent_b']}, expected {expected_pct_b}"
        )

    def test_bollinger_ddof0_differs_from_ddof1(self):
        """Document that our ddof=0 differs from pandas_ta's ddof=1."""
        std_pop = _CLOSE.rolling(20).std(ddof=0)
        std_sample = _CLOSE.rolling(20).std(ddof=1)
        # They must differ (population vs sample std)
        diff = (std_pop - std_sample).dropna().abs()
        assert diff.max() > 0.001, "ddof=0 and ddof=1 unexpectedly identical"

    def test_percent_b_range(self):
        """In normal conditions, %B is roughly in [-0.5, 1.5]."""
        ma = _CLOSE.rolling(20).mean()
        std = _CLOSE.rolling(20).std(ddof=0)
        upper = ma + 2 * std
        lower = ma - 2 * std
        pct_b = (_CLOSE - lower) / (upper - lower)
        pct_b_valid = pct_b.dropna()
        assert pct_b_valid.min() > -1.0, "Bollinger %B unexpectedly low"
        assert pct_b_valid.max() < 2.0, "Bollinger %B unexpectedly high"


# ---------------------------------------------------------------------------
# Cross-shape robustness: same indicator, different data shapes
# ---------------------------------------------------------------------------


class TestCrossShapeDifferential:
    """Verify indicator agreement across different data shapes."""

    _SHAPES = ["strong_uptrend", "strong_downtrend", "flat", "v_recovery"]

    @pytest.mark.parametrize("shape", _SHAPES)
    def test_sma_consistent_across_shapes(self, shape: str):
        data = build_fixture(shape, 200, "price_volume")
        close = data["close"]
        ours = close.rolling(20).mean()
        ref = ta.sma(close, length=20)
        diff = (ours - ref).dropna().abs()
        assert diff.max() < 1e-10, f"SMA on {shape} diff: {diff.max()}"

    @pytest.mark.parametrize("shape", _SHAPES)
    def test_stochastic_consistent_across_shapes(self, shape: str):
        data = build_fixture(shape, 200, "price_volume")
        our_k = _stochastic_k(data, 14)
        ref = ta.stoch(data["high"], data["low"], data["close"], k=14, d=3, smooth_k=1)
        ref_k = ref.iloc[:, 0]
        diff = (our_k - ref_k).dropna().abs()
        assert diff.max() < 1e-10, f"Stoch K on {shape} diff: {diff.max()}"

    @pytest.mark.parametrize("shape", _SHAPES)
    def test_rsi_self_consistent_across_shapes(self, shape: str):
        data = build_fixture(shape, 200, "price_volume")
        close = data["close"]
        ours = calculate_rsi(close, 14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        manual = 100 - (100 / (1 + gain / loss))
        diff = (ours - manual).dropna().abs()
        assert diff.max() < 1e-12, f"RSI self-check on {shape} diff: {diff.max()}"
