"""Tests for portfolio realtime websocket endpoint."""

from types import SimpleNamespace
from unittest.mock import patch


class _FakePortfolioService:
    def get_all_holdings(self, with_prices=True):
        return [
            SimpleNamespace(ticker="AAPL", currency="USD"),
            SimpleNamespace(ticker="005930.KS", currency="KRW"),
        ]

    def _get_current_prices(self, tickers):
        return {ticker: 100.0 + idx for idx, ticker in enumerate(tickers)}


def test_portfolio_realtime_websocket_emits_updates(client):
    """Websocket should accept and emit updates in expected payload shape."""
    fake_service = _FakePortfolioService()

    with patch("api.routers.portfolio.get_portfolio_service", return_value=fake_service):
        with client.websocket_connect("/api/portfolio/realtime/ws?tickers=AAPL,005930.KS") as ws:
            payload = ws.receive_json()

    assert "updates" in payload
    assert isinstance(payload["updates"], list)
    assert {u["ticker"] for u in payload["updates"]} == {"AAPL", "005930.KS"}
    assert all("current_price" in u for u in payload["updates"])
