"""L4 integration smoke tests for condition composition and screener wiring."""

from __future__ import annotations

from typing import Dict

import pandas as pd

from screener.conditions.composite import AndCondition, OrCondition
from screener.conditions.ma import AboveMACondition
from screener.conditions.price import MaxPriceCondition, MinPriceCondition, PriceChangeCondition
from screener.conditions.rsi import RSIOverboughtCondition, RSIOversoldCondition
from screener.stock_screener import StockScreener
from tests.fixtures.synthetic_data import build_fixture


def _scale_prices(data: pd.DataFrame, scale: float) -> pd.DataFrame:
    scaled = data.copy()
    scaled[["open", "high", "low", "close"]] *= scale
    return scaled


def _apply_condition(condition, universe_data: Dict[str, pd.DataFrame]) -> list[str]:
    matched = []
    for ticker, data in universe_data.items():
        if condition.evaluate(ticker, data).matched:
            matched.append(ticker)
    return matched


def test_single_condition_filtering_min_price():
    high = _scale_prices(build_fixture("strong_uptrend", 200, "price_volume"), 3.0)
    low = _scale_prices(build_fixture("strong_uptrend", 200, "price_volume"), 0.2)
    universe = {"HIGH": high, "LOW": low}

    condition = MinPriceCondition(min_price=1000)
    matched = _apply_condition(condition, universe)

    assert matched == ["HIGH"]


def test_and_composition_min_price_and_rsi_oversold():
    both = _scale_prices(build_fixture("strong_downtrend", 200, "price_volume"), 30.0)
    only_price = _scale_prices(build_fixture("strong_uptrend", 200, "price_volume"), 3.0)
    only_rsi = _scale_prices(build_fixture("strong_downtrend", 200, "price_volume"), 0.2)
    universe = {"BOTH": both, "ONLY_PRICE": only_price, "ONLY_RSI": only_rsi}

    condition = AndCondition([
        MinPriceCondition(min_price=100),
        RSIOversoldCondition(threshold=30, period=14),
    ])
    matched = _apply_condition(condition, universe)

    assert matched == ["BOTH"]


def test_or_composition_above_ma_or_rsi_oversold():
    up = build_fixture("strong_uptrend", 200, "price_volume")
    down = build_fixture("strong_downtrend", 200, "price_volume")
    flat = build_fixture("flat", 200, "price_volume")
    universe = {"UP": up, "DOWN": down, "FLAT": flat}

    condition = OrCondition([
        AboveMACondition(period=20, min_distance_pct=0.0),
        RSIOversoldCondition(threshold=30, period=14),
    ])
    matched = _apply_condition(condition, universe)

    assert "UP" in matched
    assert "DOWN" in matched


def test_empty_dataframe_returns_false_without_error():
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    min_price_result = MinPriceCondition(min_price=100).evaluate("EMPTY", empty)
    above_ma_result = AboveMACondition(period=20).evaluate("EMPTY", empty)
    and_result = AndCondition([MinPriceCondition(min_price=100), AboveMACondition(period=20)]).evaluate("EMPTY", empty)

    assert min_price_result.matched is False
    assert above_ma_result.matched is False
    assert and_result.matched is False


def test_multi_condition_chain_reduces_matches_monotonically():
    up = build_fixture("strong_uptrend", 200, "price_volume")
    down = _scale_prices(build_fixture("strong_downtrend", 200, "price_volume"), 3.0)
    flat = build_fixture("flat", 200, "price_volume")
    universe = {"UP": up, "DOWN": down, "FLAT": flat}

    chain = [
        MinPriceCondition(min_price=80),
        MaxPriceCondition(max_price=3000),
        AboveMACondition(period=20, min_distance_pct=0.0),
        PriceChangeCondition(days=5, min_change_pct=1.0),
        RSIOverboughtCondition(threshold=70, period=14),
    ]

    current = list(universe.keys())
    counts = [len(current)]

    for cond in chain:
        current = [t for t in current if cond.evaluate(t, universe[t]).matched]
        counts.append(len(current))

    assert all(after <= before for before, after in zip(counts, counts[1:]))
    assert current == ["UP"]


def test_stock_screener_run_with_monkeypatched_data(monkeypatch):
    universe_data = {
        "PASS": _scale_prices(build_fixture("strong_downtrend", 200, "price_volume"), 30.0),
        "FAIL": build_fixture("strong_uptrend", 200, "price_volume"),
    }

    condition = AndCondition([
        MinPriceCondition(min_price=100),
        RSIOversoldCondition(threshold=30, period=14),
    ])
    screener = StockScreener(
        conditions=[condition],
        max_workers=1,
        use_full_universe=False,
        request_delay=0.0,
        use_cache=False,
    )

    monkeypatch.setattr(screener, "_fetch_data", lambda ticker, days: universe_data[ticker])
    monkeypatch.setattr(screener, "_get_stock_name", lambda ticker: ticker)

    results = screener.run(
        tickers=["PASS", "FAIL"],
        show_progress=False,
        return_all=False,
    )

    assert [r.ticker for r in results] == ["PASS"]
