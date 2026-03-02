"""Tests for portfolio realtime websocket endpoint."""

from types import SimpleNamespace
from unittest.mock import patch

from api.routers import portfolio as portfolio_router


class _FakePortfolioService:
    def __init__(self):
        self.holdings_calls = 0
        self.price_calls = 0

    def get_all_holdings(self, with_prices=True):
        self.holdings_calls += 1
        return [
            SimpleNamespace(ticker="AAPL", currency="USD"),
            SimpleNamespace(ticker="005930.KS", currency="KRW"),
        ]

    def _get_current_prices(self, tickers):
        self.price_calls += 1
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


def test_portfolio_realtime_websocket_reuses_shared_snapshot(client):
    """Two close websocket connections should reuse one snapshot build."""
    fake_service = _FakePortfolioService()
    portfolio_router._ws_snapshot_cache = None
    portfolio_router._ws_snapshot_ts = 0.0

    with patch("api.routers.portfolio.get_portfolio_service", return_value=fake_service):
        with client.websocket_connect("/api/portfolio/realtime/ws?tickers=AAPL,005930.KS") as ws1:
            ws1.receive_json()
        with client.websocket_connect("/api/portfolio/realtime/ws?tickers=AAPL,005930.KS") as ws2:
            ws2.receive_json()

    assert fake_service.holdings_calls == 1
    assert fake_service.price_calls == 1
