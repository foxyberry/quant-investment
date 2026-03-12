"""US market composite scoring service.

Computes a macro regime signal from VIX, Treasury yield curve (2-10 spread),
and S&P 500 daily performance.  Stateless — all data is passed in; caching
is handled by upstream services.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class UsScoringService:
    """Computes US market composite score from VIX, Treasury curve, and S&P 500."""

    # Component weights
    VIX_WEIGHT = 0.40
    CURVE_WEIGHT = 0.30
    SP500_WEIGHT = 0.30

    # Decay half-lives (seconds) — daily data, so use 48 hours
    HALF_LIFE_VIX = 48 * 3600        # 172_800 sec
    HALF_LIFE_CURVE = 48 * 3600      # 172_800 sec
    HALF_LIFE_SP500 = 48 * 3600      # 172_800 sec

    # Regime thresholds
    RISK_OFF_THRESHOLD = 0.6
    RISK_ON_THRESHOLD = -0.6

    # ------------------------------------------------------------------
    # Raw-score normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clip(value: float, lo: float, hi: float) -> float:
        if not math.isfinite(value):
            return 0.0
        return max(lo, min(hi, value))

    @staticmethod
    def _vix_raw(vix: float) -> float:
        """VIX above 20 → positive (risk_off); below 20 → negative (risk_on)."""
        return UsScoringService._clip((vix - 20) / 15, -1, 1)

    @staticmethod
    def _curve_raw(spread_2_10: float) -> float:
        """Inverted (negative spread) → positive (risk_off).
        Normal (positive spread) → negative (risk_on)."""
        return UsScoringService._clip(-spread_2_10 / 0.5, -1, 1)

    @staticmethod
    def _sp500_raw(sp500_change_pct: float) -> float:
        """Decline → positive (risk_off); rally → negative (risk_on)."""
        return UsScoringService._clip(-sp500_change_pct / 2.0, -1, 1)

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_as_of(as_of: Optional[str]) -> Optional[datetime]:
        if as_of is None:
            return None
        try:
            dt = datetime.fromisoformat(as_of)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _compute_decay(as_of: Optional[str], half_life: int, now: datetime) -> float:
        dt = UsScoringService._parse_as_of(as_of)
        if dt is None:
            return 1.0  # assume fresh if timestamp unavailable
        age_sec = max((now - dt).total_seconds(), 0)
        return math.pow(2, -age_sec / half_life)

    # ------------------------------------------------------------------
    # Interpretation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def interpret_vix(vix: Optional[float]) -> str:
        if vix is None:
            return "unavailable"
        if vix < 15:
            return "low_vol"
        if vix <= 25:
            return "normal"
        if vix <= 35:
            return "elevated"
        return "extreme"

    @staticmethod
    def interpret_curve(spread: Optional[float]) -> str:
        if spread is None:
            return "unavailable"
        if spread > 0.1:
            return "normal"
        if spread >= -0.1:
            return "flat"
        return "inverted"

    @staticmethod
    def interpret_sp500(change_pct: Optional[float]) -> str:
        if change_pct is None:
            return "unavailable"
        if change_pct > 0.5:
            return "bullish"
        if change_pct < -0.5:
            return "bearish"
        return "neutral"

    @staticmethod
    def derive_entry_signal(
        vix_interp: str,
        curve_interp: str,
        sp500_interp: str,
    ) -> str:
        positive = 0
        negative = 0

        if vix_interp in ("low_vol", "normal"):
            positive += 1
        elif vix_interp in ("elevated", "extreme"):
            negative += 1

        if curve_interp == "normal":
            positive += 1
        elif curve_interp == "inverted":
            negative += 1

        if sp500_interp == "bullish":
            positive += 1
        elif sp500_interp == "bearish":
            negative += 1

        if positive >= 2 and negative == 0:
            return "buy_favorable"
        if negative >= 2:
            return "caution"
        return "wait"

    # ------------------------------------------------------------------
    # Core scoring
    # ------------------------------------------------------------------

    def compute_signal(
        self,
        vix: Optional[float],
        vix_as_of: Optional[str],
        spread_2_10: Optional[float],
        bonds_updated_at: Optional[str],
        sp500_change_pct: Optional[float],
        sp500_as_of: Optional[str],
        *,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Compute composite macro signal for the US market.

        Parameters
        ----------
        vix : float | None
            Current VIX level.
        vix_as_of : str | None
            ISO 8601 timestamp of the VIX observation.
        spread_2_10 : float | None
            2-year minus 10-year Treasury spread (percentage points).
        bonds_updated_at : str | None
            ISO 8601 timestamp of the bond data.
        sp500_change_pct : float | None
            S&P 500 daily change in percent.
        sp500_as_of : str | None
            ISO 8601 timestamp of the S&P 500 observation.
        now : datetime | None
            Override current time for deterministic testing.

        Returns
        -------
        dict  matching ``MacroSignal`` schema.
        """
        if now is None:
            now = datetime.now(tz=timezone.utc)

        components: Dict[str, Dict[str, Any]] = {}
        weighted_sum = 0.0
        weight_sum = 0.0

        # --- VIX ---
        if vix is not None and math.isfinite(vix):
            raw = self._vix_raw(vix)
            decay = self._compute_decay(vix_as_of, self.HALF_LIFE_VIX, now)
            contribution = raw * decay * self.VIX_WEIGHT
            weighted_sum += contribution
            weight_sum += decay * self.VIX_WEIGHT
            components["vix"] = {
                "raw": round(raw, 6),
                "decay": round(decay, 6),
                "weight": self.VIX_WEIGHT,
                "contribution": round(contribution, 6),
                "half_life_sec": self.HALF_LIFE_VIX,
            }

        # --- Treasury curve ---
        if spread_2_10 is not None and math.isfinite(spread_2_10):
            raw = self._curve_raw(spread_2_10)
            decay = self._compute_decay(bonds_updated_at, self.HALF_LIFE_CURVE, now)
            contribution = raw * decay * self.CURVE_WEIGHT
            weighted_sum += contribution
            weight_sum += decay * self.CURVE_WEIGHT
            components["curve"] = {
                "raw": round(raw, 6),
                "decay": round(decay, 6),
                "weight": self.CURVE_WEIGHT,
                "contribution": round(contribution, 6),
                "half_life_sec": self.HALF_LIFE_CURVE,
            }

        # --- S&P 500 ---
        if sp500_change_pct is not None and math.isfinite(sp500_change_pct):
            raw = self._sp500_raw(sp500_change_pct)
            decay = self._compute_decay(sp500_as_of, self.HALF_LIFE_SP500, now)
            contribution = raw * decay * self.SP500_WEIGHT
            weighted_sum += contribution
            weight_sum += decay * self.SP500_WEIGHT
            components["sp500"] = {
                "raw": round(raw, 6),
                "decay": round(decay, 6),
                "weight": self.SP500_WEIGHT,
                "contribution": round(contribution, 6),
                "half_life_sec": self.HALF_LIFE_SP500,
            }

        # --- Aggregate ---
        if weight_sum <= 0:
            return {
                "macro_score": None,
                "regime": "unknown",
                "reason": "No US market data available",
                "reason_detail": None,
                "updated_at": now.isoformat(),
                "market_mode": "us",
                "signal_confidence": 0,
                "confidence_band": "low",
            }

        score = weighted_sum / weight_sum
        score = round(score, 6)

        if score >= self.RISK_OFF_THRESHOLD:
            regime = "risk_off"
        elif score <= self.RISK_ON_THRESHOLD:
            regime = "risk_on"
        else:
            regime = "neutral"

        summary = (
            f"US composite={score:.4f} "
            f"(VIX={components.get('vix', {}).get('raw', 'n/a')}, "
            f"curve={components.get('curve', {}).get('raw', 'n/a')}, "
            f"sp500={components.get('sp500', {}).get('raw', 'n/a')})"
        )

        # --- Confidence (reuse KR service's static method) ---
        from api.services.macro_market_service import MacroMarketService

        total_keys = ["vix", "curve", "sp500"]
        weights = {"vix": self.VIX_WEIGHT, "curve": self.CURVE_WEIGHT, "sp500": self.SP500_WEIGHT}
        weighted_for_confidence = [
            (weights[k], components[k]["raw"], components[k]["decay"], True)
            for k in total_keys if k in components
        ]
        # Add placeholders for missing components
        for k in total_keys:
            if k not in components:
                weighted_for_confidence.append((weights[k], 0.0, 0.0, False))
        confidence, band = MacroMarketService._compute_confidence(weighted_for_confidence)

        return {
            "macro_score": score,
            "regime": regime,
            "reason": summary,
            "reason_detail": {
                "version": 1,
                "summary": summary,
                "components": components,
            },
            "updated_at": now.isoformat(),
            "market_mode": "us",
            "signal_confidence": confidence,
            "confidence_band": band,
        }

    # ------------------------------------------------------------------
    # Full bundle (signal + interpretation)
    # ------------------------------------------------------------------

    def compute_us_bundle(
        self,
        vix: Optional[float],
        vix_as_of: Optional[str],
        spread_2_10: Optional[float],
        bonds_updated_at: Optional[str],
        sp500_value: Optional[float],
        sp500_change_pct: Optional[float],
        sp500_as_of: Optional[str],
        *,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Return signal and interpretation bundle.

        ``sp500_value`` is accepted for completeness but is not used in
        scoring (only the daily change matters).
        """
        signal = self.compute_signal(
            vix=vix,
            vix_as_of=vix_as_of,
            spread_2_10=spread_2_10,
            bonds_updated_at=bonds_updated_at,
            sp500_change_pct=sp500_change_pct,
            sp500_as_of=sp500_as_of,
            now=now,
        )

        vix_interp = self.interpret_vix(vix)
        curve_interp = self.interpret_curve(spread_2_10)
        sp500_interp = self.interpret_sp500(sp500_change_pct)
        entry = self.derive_entry_signal(vix_interp, curve_interp, sp500_interp)

        # Execution posture (reuse KR service's static method)
        from api.services.macro_market_service import MacroMarketService
        posture, posture_rationale = MacroMarketService._derive_posture(
            signal.get("regime", "unknown"),
            signal.get("confidence_band"),
            entry,
        )

        return {
            "signal": signal,
            "interpretation": {
                "entry_signal": entry,
                "vix_interpretation": vix_interp,
                "curve_interpretation": curve_interp,
                "sp500_interpretation": sp500_interp,
                "posture": posture,
                "posture_rationale": posture_rationale,
            },
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_us_scoring_service: Optional[UsScoringService] = None


def get_us_scoring_service() -> UsScoringService:
    """Return singleton UsScoringService instance."""
    global _us_scoring_service
    if _us_scoring_service is None:
        _us_scoring_service = UsScoringService()
    return _us_scoring_service
