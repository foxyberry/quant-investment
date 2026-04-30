"""Interpretation helpers for MacroMarketService."""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_interpretation(service, fx: Dict[str, Any], futures: Dict[str, Any], flow: Dict[str, Any]) -> Dict[str, Any]:
    fx_interp = interpret_fx(service, fx)
    futures_interp = interpret_futures(service, futures)
    flow_interp = interpret_flow(service, flow)
    entry_signal = derive_entry_signal(fx_interp, futures_interp, flow_interp)
    return {
        "entry_signal": entry_signal,
        "fx_interpretation": fx_interp,
        "futures_interpretation": futures_interp,
        "flow_interpretation": flow_interp,
    }


def interpret_fx(service, fx: Dict[str, Any]) -> str:
    change = service._to_float(fx.get("change_pct"))
    if change is None:
        return "unavailable"
    if change > 0.5:
        return "rising_strong"
    if change > 0.1:
        return "rising"
    if change < -0.5:
        return "falling_strong"
    if change < -0.1:
        return "falling"
    return "stable"


def interpret_futures(service, futures: Dict[str, Any]) -> str:
    basis = service._to_float(futures.get("basis"))
    if basis is None:
        return "unavailable"
    if basis > 0.1:
        return "contango"
    if basis < -0.1:
        return "backwardation"
    return "flat"


def interpret_flow(service, flow: Dict[str, Any]) -> str:
    foreign = service._to_float(flow.get("foreign_net"))
    if foreign is None:
        return "unavailable"
    if foreign > 50_000_000_000:
        return "foreign_strong_buy"
    if foreign > 0:
        return "foreign_buy"
    if foreign < -50_000_000_000:
        return "foreign_strong_sell"
    if foreign < 0:
        return "foreign_sell"
    return "neutral"


def derive_entry_signal(fx_interp: str, futures_interp: str, flow_interp: str) -> str:
    positive = 0
    negative = 0

    if fx_interp in ("falling", "falling_strong"):
        positive += 1
    elif fx_interp in ("rising", "rising_strong"):
        negative += 1

    if futures_interp == "contango":
        positive += 1
    elif futures_interp == "backwardation":
        negative += 1

    if flow_interp in ("foreign_buy", "foreign_strong_buy"):
        positive += 1
    elif flow_interp in ("foreign_sell", "foreign_strong_sell"):
        negative += 1

    if positive >= 2 and negative == 0:
        return "buy_favorable"
    if negative >= 2:
        return "caution"
    return "wait"


def derive_posture(
    regime: str,
    confidence_band: Optional[str],
    entry_signal: str,
) -> tuple:
    if regime == "risk_off":
        if confidence_band == "high" and entry_signal == "caution":
            return "hedge_bias", "posture_hedge_bias"
        return "risk_off_defensive", "posture_risk_off_defensive"

    if regime == "risk_on":
        if entry_signal == "caution":
            return "wait", "posture_wait_neutral"
        if confidence_band == "high" and entry_signal == "buy_favorable":
            return "risk_on_full", "posture_risk_on_full"
        if confidence_band in ("high", "medium"):
            return "risk_on_small", "posture_risk_on_small"
        return "wait", "posture_wait_low_confidence"

    return "wait", "posture_wait_neutral"
