"""Unit tests for ScreeningService multi-universe behavior."""

from unittest.mock import MagicMock

import pytest

from api.services.screening_service import ScreeningService


class TestResolveUniverses:
    def test_resolve_universes_normalizes_and_deduplicates(self):
        service = ScreeningService()
        assert service.resolve_universes("kospi, KOSDAQ, kospi") == ["KOSPI", "KOSDAQ"]

    def test_resolve_universes_defaults_to_kospi(self):
        service = ScreeningService()
        assert service.resolve_universes(None) == ["KOSPI"]

    def test_resolve_universes_rejects_unknown(self):
        service = ScreeningService()
        with pytest.raises(ValueError, match="Unknown universe"):
            service.resolve_universes("KOSPI,INVALID")


class TestTickerMerge:
    def test_get_tickers_for_universes_dedupes_stable_order(self, monkeypatch):
        service = ScreeningService()

        def _mock_get_universe_symbols(universe: str):
            if universe == "KOSPI":
                return {"005930.KS": "Samsung", "000660.KS": "SK Hynix"}
            if universe == "KOSDAQ":
                return {"000660.KS": "SK Hynix", "035720.KQ": "Kakao"}
            raise ValueError("unknown")

        monkeypatch.setattr(service, "_get_universe_symbols", _mock_get_universe_symbols)

        tickers = service.get_tickers_for_universes(["KOSPI", "KOSDAQ"])
        assert tickers == ["005930.KS", "000660.KS", "035720.KQ"]

    def test_get_tickers_for_universes_partial_failure_degrades(self, monkeypatch):
        service = ScreeningService()

        def _mock_get_universe_symbols(universe: str):
            if universe == "KOSPI":
                return {"005930.KS": "Samsung"}
            raise RuntimeError("fetch failed")

        monkeypatch.setattr(service, "_get_universe_symbols", _mock_get_universe_symbols)

        tickers = service.get_tickers_for_universes(["KOSPI", "KOSDAQ"])
        assert tickers == ["005930.KS"]

    def test_get_tickers_for_universes_all_fail_raises(self, monkeypatch):
        service = ScreeningService()

        def _mock_get_universe_symbols(universe: str):
            raise RuntimeError("fetch failed")

        monkeypatch.setattr(service, "_get_universe_symbols", _mock_get_universe_symbols)

        with pytest.raises(ValueError, match="Failed to fetch all universes"):
            service.get_tickers_for_universes(["KOSPI", "KOSDAQ"])


class TestRunScreening:
    def test_run_screening_uses_multi_universe_symbols(self, monkeypatch):
        service = ScreeningService()

        monkeypatch.setattr(service, "_resolve_conditions", lambda preset, params: [object()])
        monkeypatch.setattr(
            service,
            "_get_symbols_for_universes",
            lambda universe_input, fail_fast=False: (
                {"005930.KS": "Samsung", "AAPL": "Apple"},
                ["KOSPI", "SP500"],
                {},
            ),
        )

        class _Result:
            def __init__(self, ticker, name):
                self.ticker = ticker
                self.name = name
                self.current_price = 100.0
                self.matched = True
                self.condition_results = []

        mock_screener = MagicMock()
        mock_screener.run.return_value = [_Result("005930.KS", "Samsung")]

        def _mock_stock_screener(**kwargs):
            assert sorted(kwargs["stock_names"].keys()) == ["005930.KS", "AAPL"]
            return mock_screener

        monkeypatch.setattr("api.services.screening_service.StockScreener", _mock_stock_screener)

        result = service.run_screening(
            preset="accumulation_basic",
            universe="KOSPI",
            universes=["KOSPI", "SP500"],
            params=None,
        )

        assert result["total_count"] == 2
        assert result["matched_count"] == 1
        assert result["resolved_universes"] == ["KOSPI", "SP500"]
        assert result["failed_universe_errors"] == {}

    def test_run_screening_raises_when_all_universe_fetches_fail(self, monkeypatch):
        service = ScreeningService()

        monkeypatch.setattr(service, "_resolve_conditions", lambda preset, params: [object()])
        monkeypatch.setattr(
            service,
            "_get_symbols_for_universes",
            lambda universe_input, fail_fast=False: ({}, ["KOSPI"], {"KOSPI": "fetch failed"}),
        )

        with pytest.raises(ValueError, match="Failed to fetch all universes"):
            service.run_screening(
                preset="accumulation_basic",
                universe="KOSPI",
                universes=["KOSPI"],
                params=None,
            )

    def test_run_screening_guardrail_rejects_oversized_universe(self, monkeypatch):
        service = ScreeningService()
        monkeypatch.setattr(service, "_resolve_conditions", lambda preset, params: [object()])

        oversized_symbols = {f"T{i:04d}": f"Name{i}" for i in range(service.MAX_TICKERS_PER_RUN + 1)}
        monkeypatch.setattr(
            service,
            "_get_symbols_for_universes",
            lambda universe_input, fail_fast=False: (oversized_symbols, ["KOSPI"], {}),
        )

        with pytest.raises(ValueError, match="Target universe too large"):
            service.run_screening(
                preset="accumulation_basic",
                universe="KOSPI",
                universes=["KOSPI"],
                params=None,
            )
