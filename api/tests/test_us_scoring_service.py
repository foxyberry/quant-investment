"""Tests for UsScoringService."""

from datetime import datetime, timedelta, timezone

import pytest

from api.services.us_scoring_service import UsScoringService, get_us_scoring_service

NOW = datetime(2026, 3, 12, 12, 0, 0, tzinfo=timezone.utc)
FRESH = NOW.isoformat()  # timestamps == now → decay = 1.0


@pytest.fixture
def svc() -> UsScoringService:
    return UsScoringService()


# ------------------------------------------------------------------
# 1. VIX high → risk_off leaning
# ------------------------------------------------------------------
def test_vix_high_produces_risk_off(svc: UsScoringService):
    """VIX=35 with normal curve and neutral S&P should push score positive."""
    result = svc.compute_signal(
        vix=35,
        vix_as_of=FRESH,
        spread_2_10=0.0,
        bonds_updated_at=FRESH,
        sp500_change_pct=0.0,
        sp500_as_of=FRESH,
        now=NOW,
    )

    assert result["macro_score"] is not None
    assert result["macro_score"] > 0, "High VIX should push score positive (risk_off direction)"
    assert result["regime"] in ("risk_off", "neutral")
    assert result["market_mode"] == "us"
    assert "reason_detail" in result
    assert result["reason_detail"]["components"]["vix"]["raw"] == pytest.approx(1.0)


# ------------------------------------------------------------------
# 2. All neutral → neutral regime, score near zero
# ------------------------------------------------------------------
def test_all_neutral_produces_neutral_regime(svc: UsScoringService):
    """VIX=20, spread=0, sp500_change=0 → all raw scores are 0."""
    result = svc.compute_signal(
        vix=20,
        vix_as_of=FRESH,
        spread_2_10=0.0,
        bonds_updated_at=FRESH,
        sp500_change_pct=0.0,
        sp500_as_of=FRESH,
        now=NOW,
    )

    assert result["macro_score"] == pytest.approx(0.0, abs=1e-6)
    assert result["regime"] == "neutral"


# ------------------------------------------------------------------
# 3. Low VIX + positive S&P + normal curve → risk_on
# ------------------------------------------------------------------
def test_low_vix_positive_sp500_produces_risk_on(svc: UsScoringService):
    """VIX=12, spread=0.5 (normal), sp500_change=+2.0 (rally) → risk_on."""
    result = svc.compute_signal(
        vix=12,
        vix_as_of=FRESH,
        spread_2_10=0.5,
        bonds_updated_at=FRESH,
        sp500_change_pct=2.0,
        sp500_as_of=FRESH,
        now=NOW,
    )

    assert result["macro_score"] is not None
    assert result["macro_score"] < 0, "Favorable conditions should push score negative (risk_on)"
    assert result["regime"] == "risk_on"


# ------------------------------------------------------------------
# 4. Interpretation functions
# ------------------------------------------------------------------
class TestInterpretations:
    def test_interpret_vix(self):
        assert UsScoringService.interpret_vix(None) == "unavailable"
        assert UsScoringService.interpret_vix(10) == "low_vol"
        assert UsScoringService.interpret_vix(14.99) == "low_vol"
        assert UsScoringService.interpret_vix(15) == "normal"
        assert UsScoringService.interpret_vix(25) == "normal"
        assert UsScoringService.interpret_vix(25.01) == "elevated"
        assert UsScoringService.interpret_vix(35) == "elevated"
        assert UsScoringService.interpret_vix(35.01) == "extreme"
        assert UsScoringService.interpret_vix(80) == "extreme"

    def test_interpret_curve(self):
        assert UsScoringService.interpret_curve(None) == "unavailable"
        assert UsScoringService.interpret_curve(0.5) == "normal"
        assert UsScoringService.interpret_curve(0.11) == "normal"
        assert UsScoringService.interpret_curve(0.1) == "flat"
        assert UsScoringService.interpret_curve(0.0) == "flat"
        assert UsScoringService.interpret_curve(-0.1) == "flat"
        assert UsScoringService.interpret_curve(-0.11) == "inverted"
        assert UsScoringService.interpret_curve(-1.0) == "inverted"

    def test_interpret_sp500(self):
        assert UsScoringService.interpret_sp500(None) == "unavailable"
        assert UsScoringService.interpret_sp500(1.0) == "bullish"
        assert UsScoringService.interpret_sp500(0.51) == "bullish"
        assert UsScoringService.interpret_sp500(0.5) == "neutral"
        assert UsScoringService.interpret_sp500(0.0) == "neutral"
        assert UsScoringService.interpret_sp500(-0.5) == "neutral"
        assert UsScoringService.interpret_sp500(-0.51) == "bearish"
        assert UsScoringService.interpret_sp500(-3.0) == "bearish"


# ------------------------------------------------------------------
# 5. Entry signal derivation
# ------------------------------------------------------------------
class TestEntrySignal:
    def test_buy_favorable(self):
        # 2+ positive, 0 negative
        assert UsScoringService.derive_entry_signal("low_vol", "normal", "neutral") == "buy_favorable"
        assert UsScoringService.derive_entry_signal("normal", "normal", "bullish") == "buy_favorable"

    def test_caution(self):
        # 2+ negative
        assert UsScoringService.derive_entry_signal("elevated", "inverted", "bearish") == "caution"
        assert UsScoringService.derive_entry_signal("extreme", "inverted", "neutral") == "caution"

    def test_wait(self):
        # mixed or insufficient positives
        assert UsScoringService.derive_entry_signal("low_vol", "inverted", "neutral") == "wait"
        assert UsScoringService.derive_entry_signal("unavailable", "flat", "neutral") == "wait"
        assert UsScoringService.derive_entry_signal("normal", "flat", "neutral") == "wait"


# ------------------------------------------------------------------
# 6. Null safety — all inputs None
# ------------------------------------------------------------------
def test_null_safety(svc: UsScoringService):
    result = svc.compute_signal(
        vix=None,
        vix_as_of=None,
        spread_2_10=None,
        bonds_updated_at=None,
        sp500_change_pct=None,
        sp500_as_of=None,
        now=NOW,
    )

    assert result["macro_score"] is None
    assert result["regime"] == "unknown"
    assert result["market_mode"] == "us"
    assert result["reason_detail"] is None


# ------------------------------------------------------------------
# 7. Partial data — some inputs None, others available
# ------------------------------------------------------------------
def test_partial_data_vix_only(svc: UsScoringService):
    """Only VIX provided; curve and S&P are None."""
    result = svc.compute_signal(
        vix=30,
        vix_as_of=FRESH,
        spread_2_10=None,
        bonds_updated_at=None,
        sp500_change_pct=None,
        sp500_as_of=None,
        now=NOW,
    )

    assert result["macro_score"] is not None
    assert result["regime"] in ("risk_off", "neutral", "risk_on")
    # Only VIX component should be present
    detail = result["reason_detail"]
    assert "vix" in detail["components"]
    assert "curve" not in detail["components"]
    assert "sp500" not in detail["components"]


def test_partial_data_sp500_only(svc: UsScoringService):
    """Only S&P 500 change provided."""
    result = svc.compute_signal(
        vix=None,
        vix_as_of=None,
        spread_2_10=None,
        bonds_updated_at=None,
        sp500_change_pct=-3.0,
        sp500_as_of=FRESH,
        now=NOW,
    )

    assert result["macro_score"] is not None
    assert result["macro_score"] > 0, "Big decline should push score positive"
    detail = result["reason_detail"]
    assert "sp500" in detail["components"]
    assert "vix" not in detail["components"]


# ------------------------------------------------------------------
# 8. Decay effect — stale data reduces contribution
# ------------------------------------------------------------------
def test_decay_reduces_contribution(svc: UsScoringService):
    """Data 48 hours old should have decay ~0.5 (one half-life)."""
    stale = (NOW - timedelta(hours=48)).isoformat()

    result_fresh = svc.compute_signal(
        vix=35, vix_as_of=FRESH,
        spread_2_10=0.0, bonds_updated_at=FRESH,
        sp500_change_pct=0.0, sp500_as_of=FRESH,
        now=NOW,
    )
    result_stale = svc.compute_signal(
        vix=35, vix_as_of=stale,
        spread_2_10=0.0, bonds_updated_at=FRESH,
        sp500_change_pct=0.0, sp500_as_of=FRESH,
        now=NOW,
    )

    # Stale VIX decay should be ~0.5
    vix_decay = result_stale["reason_detail"]["components"]["vix"]["decay"]
    assert vix_decay == pytest.approx(0.5, abs=0.01)

    # Stale VIX should yield lower absolute score
    assert abs(result_stale["macro_score"]) < abs(result_fresh["macro_score"])


# ------------------------------------------------------------------
# 9. Full bundle includes interpretation
# ------------------------------------------------------------------
def test_compute_us_bundle(svc: UsScoringService):
    bundle = svc.compute_us_bundle(
        vix=18,
        vix_as_of=FRESH,
        spread_2_10=0.3,
        bonds_updated_at=FRESH,
        sp500_value=5200.0,
        sp500_change_pct=0.8,
        sp500_as_of=FRESH,
        now=NOW,
    )

    assert "signal" in bundle
    assert "interpretation" in bundle

    sig = bundle["signal"]
    assert sig["market_mode"] == "us"
    assert sig["macro_score"] is not None

    interp = bundle["interpretation"]
    assert interp["entry_signal"] in ("buy_favorable", "wait", "caution")
    assert interp["vix_interpretation"] == "normal"
    assert interp["curve_interpretation"] == "normal"
    assert interp["sp500_interpretation"] == "bullish"


# ------------------------------------------------------------------
# 10. Singleton accessor
# ------------------------------------------------------------------
def test_singleton():
    a = get_us_scoring_service()
    b = get_us_scoring_service()
    assert a is b
    assert isinstance(a, UsScoringService)
