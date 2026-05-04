"""Tests for PortfolioSellChecker technical signal toggle behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

from scripts.live.portfolio_sell_checker import PortfolioSellChecker
from screener.portfolio_manager import ConfigHolding


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


def test_check_holding_skips_price_data_fetch_when_technical_signals_disabled():
    checker = PortfolioSellChecker()
    checker.pm = MagicMock()
    checker.pm.get_sell_conditions_for.return_value = MagicMock()
    checker.pm.is_technical_signals_enabled.return_value = False
    checker.get_current_price = MagicMock(return_value=100.0)
    checker.check_price_conditions = MagicMock(return_value=[])
    checker.get_price_data = MagicMock()
    checker.check_technical_conditions = MagicMock(return_value=["unexpected"])

    holding = ConfigHolding(
        symbol="AAPL",
        name="Apple",
        buy_price=90.0,
        quantity=10,
        buy_date=None,
    )

    result = checker.check_holding(holding)

    assert result is not None
    assert result.signal.value == "HOLD"
    checker.get_price_data.assert_not_called()
    checker.check_technical_conditions.assert_not_called()
