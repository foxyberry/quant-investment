"""
Regression tests for edge cases found during the condition logic audit.

Each test targets a specific zero-value or boundary-case bug that was identified
and fixed.  These tests ensure the fixes are not accidentally reverted.

Covers:
- MA conditions with zero MA values (division-by-zero guard)
- PriceChangeCondition with zero past price
- CalmarRatioFilterCondition annualization correctness
- RoicCondition with legitimately zero operating income
- BollingerSqueezeBreakoutCondition with zero MA
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from screener.conditions.ma import (
    AboveMACondition,
    BelowMACondition,
    MATouchCondition,
)
from screener.conditions.price import PriceChangeCondition
from screener.conditions.risk import CalmarRatioFilterCondition
from screener.conditions.fundamental import RoicCondition
from screener.conditions.quant_oscillators import BollingerSqueezeBreakoutCondition


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(
    close: list[float] | np.ndarray,
    *,
    days: int | None = None,
) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from a list of close prices.

    open/high/low mirror close; volume is constant 1000.
    Index is a DatetimeIndex ending today.
    """
    if days is not None and isinstance(close, (int, float)):
        close = [float(close)] * days
    n = len(close)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": [1000] * n,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConditionAuditRegression:
    """Regression tests for edge cases found during the condition logic audit."""

    def test_ma_touch_zero_ma(self):
        """MATouchCondition must return matched=False when all close prices
        are zero (MA value becomes 0), instead of raising ZeroDivisionError.

        Before the fix, ``abs(price - ma) / ma`` would crash when ma == 0.
        """
        cond = MATouchCondition(period=5, threshold=0.02)
        data = _make_ohlcv([0.0] * 30)

        result = cond.evaluate("ZERO", data)

        assert result.matched is False
        assert "error" in result.details

    def test_above_ma_zero_ma(self):
        """AboveMACondition must return matched=False when MA value is 0,
        not crash with a division-by-zero error.

        The guard ``ma_value == 0`` on line 133 of ma.py prevents
        ``(price - ma) / ma`` from blowing up.
        """
        cond = AboveMACondition(period=5, min_distance_pct=0)
        data = _make_ohlcv([0.0] * 30)

        result = cond.evaluate("ZERO", data)

        assert result.matched is False
        assert "error" in result.details

    def test_below_ma_zero_ma(self):
        """BelowMACondition must return matched=False when MA value is 0,
        not crash with a division-by-zero error.

        Same guard as AboveMACondition (line 202 of ma.py).
        """
        cond = BelowMACondition(period=5, max_distance_pct=0)
        data = _make_ohlcv([0.0] * 30)

        result = cond.evaluate("ZERO", data)

        assert result.matched is False
        assert "error" in result.details

    def test_price_change_zero_past_price(self):
        """PriceChangeCondition must return matched=False when the past price
        is 0, rather than producing inf or nan from ``(cur - 0) / 0``.

        The guard on line 212 of price.py catches ``past_price == 0``.
        """
        # 11 rows: past price (index -2) is 0, current price (index -1) is 10
        prices = [0.0] * 10 + [10.0]
        cond = PriceChangeCondition(min_change_pct=0, days=1)
        data = _make_ohlcv(prices)

        result = cond.evaluate("ZERO_PAST", data)

        assert result.matched is False
        assert "error" in result.details
        # Confirm no inf/nan leaked into details
        for v in result.details.values():
            if isinstance(v, float):
                assert np.isfinite(v), f"Non-finite value in details: {v}"

    def test_calmar_ratio_annualization_formula(self):
        """CalmarRatioFilterCondition must use ``len(close) - 1`` for the
        annualization exponent, not ``len(close)``.

        We use a short window (20 bars) where the difference between the two
        formulas is large, then compute both expected values and verify the
        result matches the correct one.

        With 20 bars and 10% total return:
        - Correct:  (1.10)^(252/19) = ~3.47 = 347% annualized
        - Wrong:    (1.10)^(252/20) = ~3.12 = 312% annualized
        """
        n = 20
        start_price = 100.0
        total_return = 0.10  # 10%
        end_price = start_price * (1 + total_return)

        # Build series with a 2% dip to create non-zero max_dd
        half = n // 2
        part1 = np.linspace(start_price, start_price * 1.05, half)
        part2_dip = np.array([start_price * 1.05, start_price * 1.029])  # ~2% dip
        part3 = np.linspace(start_price * 1.04, end_price, n - half - 2)
        prices = np.concatenate([part1, part2_dip, part3])
        assert len(prices) == n
        data = _make_ohlcv(prices.tolist())

        close = data["close"].tail(n)
        actual_total_return = float(close.iloc[-1] / close.iloc[0] - 1.0)

        # Expected annualized return with correct formula: 252/(n-1)
        expected_correct = (1.0 + actual_total_return) ** (252 / (n - 1)) - 1.0
        # Wrong formula would use 252/n
        expected_wrong = (1.0 + actual_total_return) ** (252 / n) - 1.0

        cond = CalmarRatioFilterCondition(lookback_days=n, min_calmar=0.0)
        result = cond.evaluate("CALMAR_TEST", data)

        calmar = result.details.get("calmar", 0.0)
        assert np.isfinite(calmar), f"Calmar is not finite: {calmar}"

        # Compute max_dd from the data to back out ann_return
        rolling_peak = close.cummax()
        max_dd = float(abs((close / rolling_peak - 1.0).min()))
        assert max_dd > 0, "Need non-zero drawdown for this test"

        # Back out ann_return from calmar
        actual_ann_return = calmar * max_dd

        # Verify it matches the correct formula, NOT the wrong one
        assert actual_ann_return == pytest.approx(expected_correct, rel=0.01), (
            f"Annualized return {actual_ann_return} doesn't match correct formula {expected_correct}"
        )
        # Sanity: the two formulas should differ meaningfully for n=20
        assert abs(expected_correct - expected_wrong) > 0.01, (
            "Test setup issue: correct and wrong formulas too close to distinguish"
        )

    def test_roic_zero_operating_income(self):
        """RoicCondition must use operating_income=0 when it is legitimately 0,
        and NOT fall back to EBITDA.

        Before the audit fix, the condition checked ``if not operating_income``
        which is True for 0, causing it to be treated as missing data.  The
        correct behavior is to proceed with ROIC = 0 / invested_capital = 0%.

        We monkeypatch ``_get_info`` to return controlled data.
        """
        fake_info = {
            "operatingIncome": 0,  # legitimately zero
            "ebitda": 500_000_000,  # should NOT be used as fallback
            "effectiveTaxRate": 0.21,
            "totalDebt": 1_000_000_000,
            "totalStockholderEquity": 2_000_000_000,
        }

        cond = RoicCondition(min_roic=15.0)
        data = _make_ohlcv([100.0] * 5)

        with patch("screener.conditions.fundamental._get_info", return_value=fake_info):
            result = cond.evaluate("ROIC_ZERO", data)

        # operating_income=0 means NOPAT=0, so ROIC=0%.
        # This should NOT match min_roic=15%.
        # Crucially, it should NOT return an error about missing data.
        assert result.matched is False
        # If the bug is present, details would contain {"error": "No operating income data"}
        # After the fix, it should contain the computed roic_pct = 0.0
        assert "error" not in result.details, (
            f"operating_income=0 was treated as missing: {result.details}"
        )
        assert result.details.get("roic_pct") == pytest.approx(0.0, abs=0.01)

    def test_roic_none_operating_income_falls_back_to_ebitda(self):
        """When operatingIncome is None, RoicCondition should fall back to EBITDA.

        This is the intended fallback path (not a bug), tested here to ensure
        the zero-vs-None distinction is correct.
        """
        fake_info = {
            "operatingIncome": None,
            "ebitda": 500_000_000,
            "effectiveTaxRate": 0.21,
            "totalDebt": 1_000_000_000,
            "totalStockholderEquity": 2_000_000_000,
        }

        cond = RoicCondition(min_roic=0.0)
        data = _make_ohlcv([100.0] * 5)

        with patch("screener.conditions.fundamental._get_info", return_value=fake_info):
            result = cond.evaluate("ROIC_FALLBACK", data)

        # NOPAT = 500M * (1 - 0.21) = 395M
        # Invested capital = 1B + 2B = 3B
        # ROIC = 395M / 3B * 100 = 13.17%
        expected_roic = (500_000_000 * (1 - 0.21)) / 3_000_000_000 * 100
        assert "error" not in result.details
        assert result.details.get("roic_pct") == pytest.approx(expected_roic, rel=0.01)

    def test_roic_missing_both_operating_and_ebitda(self):
        """When both operatingIncome and ebitda are absent, RoicCondition should
        return 'No operating income data' error."""
        fake_info = {
            "effectiveTaxRate": 0.21,
            "totalDebt": 1_000_000_000,
            "totalStockholderEquity": 2_000_000_000,
        }

        cond = RoicCondition(min_roic=15.0)
        data = _make_ohlcv([100.0] * 5)

        with patch("screener.conditions.fundamental._get_info", return_value=fake_info):
            result = cond.evaluate("ROIC_MISSING", data)

        assert result.matched is False
        assert result.details.get("error") == "No operating income data"

    def test_bollinger_squeeze_zero_ma(self):
        """BollingerSqueezeBreakoutCondition must handle zero MA without
        crashing (e.g., when all prices are 0).

        The guard ``ma.iloc[-2] != 0`` on line 82 of quant_oscillators.py
        prevents division by zero in the bandwidth calculation.
        """
        cond = BollingerSqueezeBreakoutCondition(period=5, std_mult=2.0, max_width_pct=10.0)
        data = _make_ohlcv([0.0] * 30)

        result = cond.evaluate("BB_ZERO", data)

        assert result.matched is False
        # Should gracefully handle zero MA, not raise an exception
