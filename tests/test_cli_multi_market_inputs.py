"""Smoke tests for multi-market CLI input parsers."""

from scripts.analysis.run_daily_analysis import parse_market_inputs
from scripts.cache_manager import parse_universe_inputs as parse_cache_universes
from scripts.screening.accumulation_screen import parse_universe_inputs as parse_accum_universes
from scripts.screening.run_screener import parse_universe_inputs as parse_screener_universes


def test_screener_parser_supports_csv_and_repeated_flags():
    resolved = parse_screener_universes("KOSPI,KOSDAQ", ["SP500"])
    assert resolved == ["SP500", "KOSPI", "KOSDAQ"]


def test_accumulation_parser_defaults_to_kospi():
    resolved = parse_accum_universes("", [])
    assert resolved == ["KOSPI"]


def test_cache_parser_deduplicates_stably():
    resolved = parse_cache_universes("KOSPI", ["KOSDAQ", "KOSPI,KOSDAQ"])
    assert resolved == ["KOSDAQ", "KOSPI"]


def test_daily_analysis_market_parser_expands_all():
    resolved = parse_market_inputs("ALL", [])
    assert resolved == ["KOSPI", "SP500"]


def test_daily_analysis_market_parser_rejects_invalid():
    try:
        parse_market_inputs("NASDAQ100", [])
        assert False, "expected ValueError for unsupported market"
    except ValueError as exc:
        assert "Unsupported market" in str(exc)
