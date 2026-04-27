from datetime import datetime, timezone

from api.services.macro_service import MacroMarketService


class StubExchangeService:
    def get_rates(self, base: str = "USD"):
        assert base == "USD"
        return {
            "base": "USD",
            "rates": {"KRW": 1340.0},
            "updated_at": datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),
        }


class StubMarketService:
    def get_quote(self, ticker: str):
        if ticker == "069500.KS":
            return {
                "ticker": ticker,
                "current_price": 402.0,
                "change_pct": -0.4,
                "timestamp": "2026-03-08T00:00:00+00:00",
            }
        if ticker == "^KS11":
            return {
                "ticker": ticker,
                "current_price": 400.0,
                "change_pct": -0.2,
                "timestamp": "2026-03-08T00:00:00+00:00",
            }
        return None


def test_bundle_returns_regime_and_history_point(tmp_path):
    svc = MacroMarketService(
        market_service=StubMarketService(),
        exchange_service=StubExchangeService(),
    )
    svc.investor_flow_path = tmp_path / "investor_flow_latest.json"

    bundle = svc.get_bundle()

    assert "signal" in bundle
    assert bundle["signal"]["regime"] in {"risk_on", "neutral", "risk_off", "unknown"}

    history = svc.get_history("60m")
    assert history["window"] == "60m"
    assert len(history["points"]) >= 1


def test_invalid_window_falls_back_without_crash(tmp_path):
    svc = MacroMarketService(
        market_service=StubMarketService(),
        exchange_service=StubExchangeService(),
    )
    svc.investor_flow_path = tmp_path / "investor_flow_latest.json"

    svc.get_bundle()
    history = svc.get_history("x5m")

    assert history["window"] == "x5m"
    assert isinstance(history["points"], list)
