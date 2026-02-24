"""Tests for screening/strategy multi-market schema normalization."""

from api.schemas.screening import (
    ScreeningRequest,
    find_invalid_universes,
    format_invalid_universe_error,
)
from api.schemas.strategy import StrategyExecuteRequest, StrategyGraph


def test_screening_request_single_universe_normalization():
    request = ScreeningRequest(universe="kospi")
    assert request.universe == "KOSPI"
    assert request.universes == ["KOSPI"]


def test_screening_request_multi_universe_order_and_dedup():
    request = ScreeningRequest(universe="KOSPI, kosdaq, KOSPI")
    assert request.universes == ["KOSPI", "KOSDAQ"]
    assert request.universe == "KOSPI"


def test_screening_request_null_defaults_to_kospi():
    request = ScreeningRequest(universe=None)
    assert request.universe == "KOSPI"
    assert request.universes == ["KOSPI"]


def test_strategy_execute_request_override_normalization():
    request = StrategyExecuteRequest(
        graph=StrategyGraph(nodes=[], edges=[]),
        universe_override="sp500, nasdaq100",
    )
    assert request.universe_override == "SP500"
    assert request.universe_overrides == ["SP500", "NASDAQ100"]


def test_invalid_universe_helpers():
    invalid = find_invalid_universes(["KOSPI", "INVALID", "WRONG"])
    assert invalid == ["INVALID", "WRONG"]
    assert (
        format_invalid_universe_error(invalid)
        == "Invalid universe value(s): INVALID, WRONG. Allowed values: KOSPI, KOSDAQ, SP500, NASDAQ100"
    )
