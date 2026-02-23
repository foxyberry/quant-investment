"""Tests for stock name resolution priority in StockScreener."""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from screener.stock_screener import StockScreener


class TestStockNameResolution:
    """Test _get_stock_name priority: injected > CSV > yfinance."""

    def _make_screener(self, stock_names=None):
        """Create a screener with no conditions for name testing."""
        return StockScreener(
            conditions=[],
            use_full_universe=False,
            stock_names=stock_names,
        )

    def test_injected_name_used_first(self):
        """Injected names take priority over all other sources."""
        screener = self._make_screener(stock_names={"AAPL": "Apple Inc."})
        assert screener._get_stock_name("AAPL") == "Apple Inc."

    def test_injected_korean_name(self):
        """Injected Korean name takes priority over CSV."""
        screener = self._make_screener(
            stock_names={"005930.KS": "삼성전자 (injected)"}
        )
        assert screener._get_stock_name("005930.KS") == "삼성전자 (injected)"

    def test_csv_fallback_for_korean(self):
        """Korean stocks fall back to CSV when not injected."""
        screener = self._make_screener()
        # Mock _load_korean_names to return test data
        screener._korean_names = {"005930.KS": "삼성전자"}
        name = screener._get_stock_name("005930.KS")
        assert name == "삼성전자"

    @patch("screener.stock_screener.yf")
    def test_yfinance_last_resort(self, mock_yf):
        """yfinance is only called when no injected or CSV name exists."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"shortName": "Apple Inc."}
        mock_yf.Ticker.return_value = mock_ticker

        screener = self._make_screener()
        name = screener._get_stock_name("AAPL")
        assert name == "Apple Inc."
        mock_yf.Ticker.assert_called_once_with("AAPL")

    @patch("screener.stock_screener.yf")
    def test_injected_name_skips_yfinance(self, mock_yf):
        """When name is injected, yfinance is never called."""
        screener = self._make_screener(stock_names={"AAPL": "Apple"})
        name = screener._get_stock_name("AAPL")
        assert name == "Apple"
        mock_yf.Ticker.assert_not_called()

    @patch("screener.stock_screener.yf")
    def test_yfinance_failure_returns_ticker(self, mock_yf):
        """When yfinance fails, ticker symbol is returned."""
        mock_yf.Ticker.side_effect = Exception("API error")
        screener = self._make_screener()
        name = screener._get_stock_name("UNKNOWN")
        assert name == "UNKNOWN"
