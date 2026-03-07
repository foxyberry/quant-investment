"""Tests for pairs trading conditions and screener integration."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from screener.conditions.base import BaseCondition, PairsCondition, ConditionResult
from screener.conditions.pairs_trading import (
    PairCorrelationCondition,
    PairSpreadZScoreCondition,
    PairCointegrationCondition,
)
from screener.conditions.price import MinPriceCondition
from screener.stock_screener import StockScreener


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_series(n: int, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    return np.cumsum(rng.randn(n)) + 100


def _make_df(close: np.ndarray, dates: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.random.randint(1000, 5000, len(close)),
        },
        index=dates,
    )


@pytest.fixture()
def correlated_pair():
    """Two tickers with perfect correlation (close_B = 0.5 * close_A + 3)."""
    n = 120
    dates = pd.date_range("2024-01-01", periods=n)
    base = _make_series(n, seed=42)
    d1 = _make_df(base, dates)
    d2 = _make_df(base * 0.5 + 3, dates)
    return d1, d2, dates


@pytest.fixture()
def uncorrelated_pair():
    """Two tickers with independent random walks."""
    n = 120
    dates = pd.date_range("2024-01-01", periods=n)
    d1 = _make_df(_make_series(n, seed=42), dates)
    d2 = _make_df(_make_series(n, seed=999), dates)
    return d1, d2, dates


@pytest.fixture()
def empty_df():
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])


# ---------------------------------------------------------------------------
# PairsCondition base class tests
# ---------------------------------------------------------------------------

class TestPairsConditionBase:
    def test_is_pairs_property(self):
        class DummyPairs(PairsCondition):
            @property
            def name(self):
                return "dummy"

            @property
            def required_days(self):
                return 10

            def evaluate_pair(self, t1, d1, t2, d2):
                return ConditionResult(matched=True, condition_name=self.name)

        p = DummyPairs()
        assert p.is_pairs is True

    def test_base_condition_no_is_pairs(self):
        class DummySingle(BaseCondition):
            @property
            def name(self):
                return "single"

            @property
            def required_days(self):
                return 5

            def evaluate(self, ticker, data):
                return ConditionResult(matched=True, condition_name=self.name)

        s = DummySingle()
        assert not getattr(s, "is_pairs", False)

    def test_evaluate_raises_not_implemented(self, empty_df):
        cond = PairCorrelationCondition(ticker2="B")
        with pytest.raises(NotImplementedError, match="pairs condition"):
            cond.evaluate("A", empty_df)


# ---------------------------------------------------------------------------
# PairCorrelationCondition tests
# ---------------------------------------------------------------------------

class TestPairCorrelation:
    def test_correlated_pair_matches(self, correlated_pair):
        d1, d2, _ = correlated_pair
        cond = PairCorrelationCondition(ticker2="B", period=60, min_correlation=0.7)
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert result.matched is True
        assert result.details["correlation"] >= 0.7

    def test_uncorrelated_pair_does_not_match(self, uncorrelated_pair):
        d1, d2, _ = uncorrelated_pair
        cond = PairCorrelationCondition(ticker2="B", period=60, min_correlation=0.7)
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert result.matched is False

    def test_empty_data(self, empty_df):
        cond = PairCorrelationCondition(ticker2="B", period=60)
        result = cond.evaluate_pair("A", empty_df, "B", empty_df)
        assert result.matched is False
        assert "error" in result.details

    def test_insufficient_overlap(self):
        dates1 = pd.date_range("2024-01-01", periods=30)
        dates2 = pd.date_range("2024-06-01", periods=30)
        d1 = _make_df(_make_series(30, seed=1), dates1)
        d2 = _make_df(_make_series(30, seed=2), dates2)
        cond = PairCorrelationCondition(ticker2="B", period=60)
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert result.matched is False


# ---------------------------------------------------------------------------
# PairSpreadZScoreCondition tests
# ---------------------------------------------------------------------------

class TestPairSpreadZScore:
    def test_normal_spread_no_match(self, correlated_pair):
        d1, d2, _ = correlated_pair
        cond = PairSpreadZScoreCondition(ticker2="B", period=60, zscore_entry=2.0)
        result = cond.evaluate_pair("A", d1, "B", d2)
        # Perfectly correlated pair → spread is nearly constant → z≈0
        assert "zscore" in result.details
        assert abs(result.details["zscore"]) < 2.0  # should not trigger at z=2

    def test_empty_data(self, empty_df):
        cond = PairSpreadZScoreCondition(ticker2="B", period=60)
        result = cond.evaluate_pair("A", empty_df, "B", empty_df)
        assert result.matched is False

    def test_direction_long_spread(self, correlated_pair):
        d1, d2, _ = correlated_pair
        cond = PairSpreadZScoreCondition(
            ticker2="B", period=60, zscore_entry=2.0, direction="long_spread"
        )
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert result.details["direction"] == "long_spread"

    def test_direction_short_spread(self, correlated_pair):
        d1, d2, _ = correlated_pair
        cond = PairSpreadZScoreCondition(
            ticker2="B", period=60, zscore_entry=2.0, direction="short_spread"
        )
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert result.details["direction"] == "short_spread"

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError, match="Invalid direction"):
            PairSpreadZScoreCondition(ticker2="B", direction="up")

    def test_invalid_direction_down_raises(self):
        with pytest.raises(ValueError, match="Invalid direction"):
            PairSpreadZScoreCondition(ticker2="B", direction="down")

    def test_long_spread_matches_negative_zscore(self):
        """long_spread triggers when z <= -threshold (spread is unusually low)."""
        n = 120
        dates = pd.date_range("2024-01-01", periods=n)
        base = _make_series(n, seed=42)
        d1 = _make_df(base, dates)
        # Make ticker2 diverge upward at the end → spread drops
        modified = base.copy()
        modified[-5:] = modified[-5:] + 30  # big jump in ticker2
        d2 = _make_df(modified, dates)
        cond = PairSpreadZScoreCondition(
            ticker2="B", period=60, zscore_entry=1.5, direction="long_spread"
        )
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert result.details["zscore"] < 0  # spread dropped

    def test_short_spread_matches_positive_zscore(self):
        """short_spread triggers when z >= threshold (spread is unusually high)."""
        n = 120
        dates = pd.date_range("2024-01-01", periods=n)
        base = _make_series(n, seed=42)
        # Make ticker1 diverge upward → spread rises
        modified = base.copy()
        modified[-5:] = modified[-5:] + 30
        d1 = _make_df(modified, dates)
        d2 = _make_df(base, dates)
        cond = PairSpreadZScoreCondition(
            ticker2="B", period=60, zscore_entry=1.5, direction="short_spread"
        )
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert result.details["zscore"] > 0  # spread rose


# ---------------------------------------------------------------------------
# PairCointegrationCondition tests
# ---------------------------------------------------------------------------

class TestPairCointegration:
    def test_cointegrated_pair(self, correlated_pair):
        d1, d2, _ = correlated_pair
        cond = PairCointegrationCondition(ticker2="B", period=80, pvalue_threshold=0.1)
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert "pvalue" in result.details

    def test_pvalue_approximate_flag(self, correlated_pair):
        d1, d2, _ = correlated_pair
        cond = PairCointegrationCondition(ticker2="B", period=80, pvalue_threshold=0.5)
        result = cond.evaluate_pair("A", d1, "B", d2)
        assert result.details.get("pvalue_approximate") is True

    def test_empty_data(self, empty_df):
        cond = PairCointegrationCondition(ticker2="B", period=60)
        result = cond.evaluate_pair("A", empty_df, "B", empty_df)
        assert result.matched is False

    def test_same_ticker(self, correlated_pair):
        d1, _, _ = correlated_pair
        cond = PairCointegrationCondition(ticker2="A", period=80)
        result = cond.evaluate_pair("A", d1, "A", d1)
        assert "pvalue" in result.details


# ---------------------------------------------------------------------------
# Registry metadata tests
# ---------------------------------------------------------------------------

class TestPairsRegistry:
    def test_pairs_conditions_registered(self):
        from screener.conditions.registry import get_condition_metadata

        meta = get_condition_metadata()
        for key in ("pair_correlation", "pair_spread_zscore", "pair_cointegration"):
            assert key in meta, f"{key} not registered"
            assert meta[key]["is_pairs"] is True
            assert meta[key]["category"] == "pairs"
            # Must have ticker2 param
            param_names = [p["name"] for p in meta[key]["params"]]
            assert "ticker2" in param_names, f"{key} missing ticker2 param"

    def test_existing_conditions_not_pairs(self):
        from screener.conditions.registry import get_condition_metadata

        meta = get_condition_metadata()
        for key, m in meta.items():
            if key.startswith("pair_"):
                continue
            assert m.get("is_pairs", False) is False, f"{key} unexpectedly is_pairs"


# ---------------------------------------------------------------------------
# Screener integration tests
# ---------------------------------------------------------------------------

class TestScreenerPairsIntegration:
    def test_mixed_single_and_pairs_conditions(self, correlated_pair):
        d1, d2, _ = correlated_pair
        universe_data = {"A": d1, "B": d2}

        screener = StockScreener(
            conditions=[
                MinPriceCondition(min_price=50),
                PairCorrelationCondition(ticker2="B", period=60, min_correlation=0.7),
            ],
            max_workers=1,
            use_full_universe=False,
            request_delay=0.0,
            use_cache=False,
        )
        screener._fetch_data = lambda ticker, days: universe_data.get(ticker)
        screener._get_stock_name = lambda t: t

        results = screener.run(tickers=["A"], show_progress=False, return_all=True)
        assert len(results) == 1
        assert results[0].matched is True

    def test_pairs_condition_missing_ticker2_data(self, correlated_pair):
        d1, _, _ = correlated_pair

        screener = StockScreener(
            conditions=[
                PairCorrelationCondition(ticker2="NONEXISTENT", period=60),
            ],
            max_workers=1,
            use_full_universe=False,
            request_delay=0.0,
            use_cache=False,
        )
        screener._fetch_data = lambda ticker, days: d1 if ticker == "A" else None
        screener._get_stock_name = lambda t: t

        results = screener.run(tickers=["A"], show_progress=False, return_all=True)
        assert len(results) == 1
        assert results[0].matched is False

    def test_pairs_condition_empty_ticker2(self, correlated_pair):
        d1, _, _ = correlated_pair

        screener = StockScreener(
            conditions=[
                PairCorrelationCondition(ticker2="", period=60),
            ],
            max_workers=1,
            use_full_universe=False,
            request_delay=0.0,
            use_cache=False,
        )
        screener._fetch_data = lambda ticker, days: d1
        screener._get_stock_name = lambda t: t

        results = screener.run(tickers=["A"], show_progress=False, return_all=True)
        assert len(results) == 1
        assert results[0].matched is False
        assert "error" in results[0].condition_results[0].details

    def test_companion_cache_reset_between_runs(self, correlated_pair):
        """Cache is reset on each run(), so companion data is re-fetched."""
        d1, d2, _ = correlated_pair
        fetch_calls = []

        def tracking_fetch(ticker, days):
            fetch_calls.append((ticker, days))
            return d2 if ticker == "B" else d1

        screener = StockScreener(
            conditions=[
                PairCorrelationCondition(ticker2="B", period=60, min_correlation=0.7),
            ],
            max_workers=1,
            use_full_universe=False,
            request_delay=0.0,
            use_cache=False,
        )
        screener._fetch_data = tracking_fetch
        screener._get_stock_name = lambda t: t

        # Run 1
        screener.run(tickers=["A"], show_progress=False, return_all=True)
        companion_fetches_run1 = [c for c in fetch_calls if c[0] == "B"]
        assert len(companion_fetches_run1) == 1

        # Run 2 — cache should be reset, so B is fetched again
        fetch_calls.clear()
        screener.run(tickers=["A"], show_progress=False, return_all=True)
        companion_fetches_run2 = [c for c in fetch_calls if c[0] == "B"]
        assert len(companion_fetches_run2) == 1  # re-fetched, not cached

    def test_single_conditions_still_work(self):
        """Regression: existing single-ticker conditions unaffected."""
        from tests.fixtures.synthetic_data import build_fixture

        data = build_fixture("strong_uptrend", 200, "price_volume")
        screener = StockScreener(
            conditions=[MinPriceCondition(min_price=1)],
            max_workers=1,
            use_full_universe=False,
            request_delay=0.0,
            use_cache=False,
        )
        screener._fetch_data = lambda ticker, days: data
        screener._get_stock_name = lambda t: t

        results = screener.run(tickers=["TEST"], show_progress=False, return_all=True)
        assert len(results) == 1
        assert results[0].matched is True
