"""
Cross-validation: our indicators vs `ta` library (TradingView-compatible).

This test compares the output of `discovery/indicators.py` against
the `ta` library, which uses the same formulas as TradingView.

Known differences:
  - RSI: Our code uses SMA smoothing; ta/TradingView uses Wilder's EWM.
    We test both and flag the divergence.
  - BB: Our code uses ddof=1 (sample std); ta/TradingView uses ddof=0
    (population std). Causes ~2-3% BB width divergence.

Run:
    python -m pytest tests/cross_validation/test_indicators_xval.py -v
"""

import sys
import os

import pytest
import pandas as pd

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from screener.indicators import calculate_indicators
from tests.cross_validation.reference import calculate_reference, ReferenceIndicators


# --- Tolerance thresholds ---
# MACD uses the same formula -> tight tolerance (floating-point only)
MACD_ABS_TOL = 1e-4        # absolute difference
BB_REL_TOL = 0.005          # 0.5% relative
# RSI: SMA vs EWM diverges over time -> separate thresholds
RSI_SMA_ABS_TOL = 0.5       # our SMA RSI vs reference SMA RSI
RSI_METHOD_MAX_DIFF = 8.0   # SMA vs EWM method divergence (informational)


def _assert_not_none(value, name: str):
    """Assert that a reference value is not None (NaN data detection)."""
    assert value is not None, f"{name}: reference returned None — possible NaN in source data"


class TestMACDCrossValidation:
    """MACD should match closely — both use EWM with identical params."""

    def test_macd_line(self, ticker_data):
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.macd_line, f"{ticker} MACD line")

        diff = abs(ours["macd"] - ref.macd_line)
        assert diff < MACD_ABS_TOL, (
            f"{ticker} MACD line: ours={ours['macd']:.6f}, "
            f"ref={ref.macd_line:.6f}, diff={diff:.6f}"
        )

    def test_macd_signal(self, ticker_data):
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.macd_signal, f"{ticker} MACD signal")

        diff = abs(ours["macd_signal"] - ref.macd_signal)
        assert diff < MACD_ABS_TOL, (
            f"{ticker} MACD signal: ours={ours['macd_signal']:.6f}, "
            f"ref={ref.macd_signal:.6f}, diff={diff:.6f}"
        )

    def test_macd_histogram(self, ticker_data):
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.macd_histogram, f"{ticker} MACD histogram")

        diff = abs(ours["macd_histogram"] - ref.macd_histogram)
        assert diff < MACD_ABS_TOL, (
            f"{ticker} MACD histogram: ours={ours['macd_histogram']:.6f}, "
            f"ref={ref.macd_histogram:.6f}, diff={diff:.6f}"
        )


class TestBollingerBandsCrossValidation:
    """BB should match exactly — both use 20-period SMA +/- 2 sigma."""

    def test_bb_upper(self, ticker_data):
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.bb_upper, f"{ticker} BB upper")

        rel_err = abs(ours["bb_upper"] - ref.bb_upper) / ref.bb_upper
        assert rel_err < BB_REL_TOL, (
            f"{ticker} BB upper: ours={ours['bb_upper']:.2f}, "
            f"ref={ref.bb_upper:.2f}, rel_err={rel_err:.4f}"
        )

    def test_bb_middle(self, ticker_data):
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.bb_middle, f"{ticker} BB middle")

        rel_err = abs(ours["bb_middle"] - ref.bb_middle) / ref.bb_middle
        assert rel_err < BB_REL_TOL, (
            f"{ticker} BB middle: ours={ours['bb_middle']:.2f}, "
            f"ref={ref.bb_middle:.2f}, rel_err={rel_err:.4f}"
        )

    def test_bb_lower(self, ticker_data):
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.bb_lower, f"{ticker} BB lower")

        rel_err = abs(ours["bb_lower"] - ref.bb_lower) / ref.bb_lower
        assert rel_err < BB_REL_TOL, (
            f"{ticker} BB lower: ours={ours['bb_lower']:.2f}, "
            f"ref={ref.bb_lower:.2f}, rel_err={rel_err:.4f}"
        )

    def test_bb_width(self, ticker_data):
        """BB width diverges due to ddof=1 (ours) vs ddof=0 (ta/TradingView).

        Our std is slightly larger -> our width is wider. The relative error
        should be bounded by ~1/sqrt(window-1) ~ 3% for window=20.
        """
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.bb_width, f"{ticker} BB width")

        if ref.bb_width == 0:
            rel_err = abs(ours["bb_width"])
        else:
            rel_err = abs(ours["bb_width"] - ref.bb_width) / abs(ref.bb_width)
        assert rel_err < 0.04, (
            f"{ticker} BB width: ours={ours['bb_width']:.2f}% (ddof=1), "
            f"ref={ref.bb_width:.2f}% (ddof=0), rel_err={rel_err:.2%}"
        )


class TestRSICrossValidation:
    """RSI: known method difference (SMA vs EWM).

    - test_rsi_sma_match: our SMA RSI vs reference SMA RSI -> should be identical
    - test_rsi_method_divergence: SMA vs EWM -> informational, flagged but not failed
    """

    def test_rsi_sma_match(self, ticker_data):
        """Our RSI (SMA) should exactly match the reference SMA RSI."""
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.rsi_sma, f"{ticker} RSI SMA")

        diff = abs(ours["rsi"] - ref.rsi_sma)
        assert diff < RSI_SMA_ABS_TOL, (
            f"{ticker} RSI (SMA): ours={ours['rsi']:.2f}, "
            f"ref_sma={ref.rsi_sma:.2f}, diff={diff:.2f}"
        )

    def test_rsi_method_divergence(self, ticker_data):
        """Document the SMA vs EWM divergence (informational).

        This test does NOT fail on divergence — it reports the difference
        between our SMA-based RSI and TradingView's EWM-based RSI.
        If the divergence exceeds the threshold, it issues a warning.
        """
        ticker, _, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None
        _assert_not_none(ref.rsi_ema, f"{ticker} RSI EMA")

        sma_rsi = ours["rsi"]
        ewm_rsi = ref.rsi_ema
        diff = abs(sma_rsi - ewm_rsi)

        # Always print for visibility
        print(
            f"\n  {ticker} RSI method comparison:"
            f"\n    Our RSI (SMA):        {sma_rsi:.2f}"
            f"\n    TradingView RSI (EWM): {ewm_rsi:.2f}"
            f"\n    Divergence:            {diff:.2f}"
            f"\n    {'WARNING: SIGNIFICANT' if diff > 3 else 'acceptable'}"
        )

        if diff > RSI_METHOD_MAX_DIFF:
            pytest.fail(
                f"{ticker} RSI SMA vs EWM divergence too large: "
                f"{diff:.2f} > {RSI_METHOD_MAX_DIFF}"
            )


class TestCrossValidationReport:
    """Generate a summary report of all indicator comparisons."""

    def test_full_report(self, ticker_data):
        """Print a full comparison table for the ticker."""
        ticker, market, df = ticker_data
        ours = calculate_indicators(ticker, data=df)
        ref = calculate_reference(df["close"])
        assert ref is not None

        print(f"\n{'='*60}")
        print(f"  Cross-Validation Report: {ticker} ({market})")
        print(f"  Data points: {len(df)}")
        print(f"  Date range: {df.index[0].date()} -> {df.index[-1].date()}")
        print(f"{'='*60}")
        print(f"  {'Indicator':<20} {'Ours':>12} {'Reference':>12} {'Diff':>10} {'Status':>8}")
        print(f"  {'-'*62}")

        checks = [
            ("RSI (SMA)", ours["rsi"], ref.rsi_sma, RSI_SMA_ABS_TOL, "abs"),
            ("RSI (EWM/TV)", ours["rsi"], ref.rsi_ema, RSI_METHOD_MAX_DIFF, "abs"),
            ("MACD Line", ours["macd"], ref.macd_line, MACD_ABS_TOL, "abs"),
            ("MACD Signal", ours["macd_signal"], ref.macd_signal, MACD_ABS_TOL, "abs"),
            ("MACD Histogram", ours["macd_histogram"], ref.macd_histogram, MACD_ABS_TOL, "abs"),
            ("BB Upper", ours["bb_upper"], ref.bb_upper, BB_REL_TOL, "rel"),
            ("BB Middle", ours["bb_middle"], ref.bb_middle, BB_REL_TOL, "rel"),
            ("BB Lower", ours["bb_lower"], ref.bb_lower, BB_REL_TOL, "rel"),
            ("BB Width %", ours["bb_width"], ref.bb_width, 0.04, "rel"),
        ]

        all_pass = True
        for name, our_val, ref_val, tol, mode in checks:
            if our_val is None or ref_val is None:
                status = "SKIP"
                diff_str = "N/A"
            elif mode == "abs":
                diff = abs(our_val - ref_val)
                diff_str = f"{diff:.4f}"
                status = "PASS" if diff < tol else "FAIL"
            else:  # rel
                if ref_val == 0:
                    diff = abs(our_val)
                else:
                    diff = abs(our_val - ref_val) / abs(ref_val)
                diff_str = f"{diff:.4%}"
                status = "PASS" if diff < tol else "FAIL"

            if status == "FAIL":
                all_pass = False

            our_str = f"{our_val:>12.4f}" if our_val is not None else f"{'N/A':>12}"
            ref_str = f"{ref_val:>12.4f}" if ref_val is not None else f"{'N/A':>12}"
            print(f"  {name:<20} {our_str} {ref_str} {diff_str:>10} {status:>8}")

        print(f"  {'-'*62}")
        print(f"  Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
        print(f"{'='*60}\n")

        assert all_pass, "Cross-validation report has failures — see output above"
