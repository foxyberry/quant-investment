"""Tests for PortfolioSellChecker technical signal toggle behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

from scripts.live.portfolio_sell_checker import PortfolioSellChecker


def test_check_technical_conditions_returns_empty_when_disabled():
    checker = PortfolioSellChecker()
    checker.pm = MagicMock()
    checker.pm.is_technical_signals_enabled.return_value = False

    reasons = checker.check_technical_conditions(
        "AAPL",
        {
            "current": 90.0,
            "ma_20": 100.0,
            "ma_60": 110.0,
            "prev_ma_20": 120.0,
            "prev_ma_60": 115.0,
        },
    )

    assert reasons == []
    checker.pm.get_technical_signals_config.assert_not_called()


def test_check_technical_conditions_evaluates_when_enabled():
    checker = PortfolioSellChecker()
    checker.pm = MagicMock()
    checker.pm.is_technical_signals_enabled.return_value = True
    checker.pm.get_technical_signals_config.return_value = {
        "ma_breakdown": True,
        "death_cross": True,
    }

    reasons = checker.check_technical_conditions(
        "AAPL",
        {
            "current": 90.0,
            "ma_20": 100.0,
            "ma_60": 110.0,
            "prev_ma_20": 120.0,
            "prev_ma_60": 115.0,
        },
    )

    assert "Below 20-day MA (90 < 100)" in reasons
    assert "Death cross detected (MA20 crossed below MA60)" in reasons
