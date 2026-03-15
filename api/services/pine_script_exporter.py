"""
Pine Script v5 Exporter.

Transpiles QuantCanvas strategy graphs into TradingView Pine Script v5 code.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_ALLOWED_MA_TYPES = {"SMA", "EMA"}


def _sanitize_string(s: str) -> str:
    """Remove characters that could break Pine Script string literals."""
    return re.sub(r'["\\\n\r\t]', '', s)


def _safe_int(val: Any, default: int) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val: Any, default: float) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_ma_type(val: Any) -> str:
    s = str(val).upper() if val else "SMA"
    return s if s in _ALLOWED_MA_TYPES else "SMA"


def _get_param(params: Dict[str, Any], key: str, default: Any) -> Any:
    return params.get(key, default)


# ---------------------------------------------------------------------------
# Condition transpilers: each returns (pine_code_lines, condition_expression)
# The `idx` parameter ensures unique variable names per condition instance.
# ---------------------------------------------------------------------------

def _pine_ma_cross_up(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    short = _safe_int(params.get("short_period"), 10)
    long = _safe_int(params.get("long_period"), 20)
    ma_type = _safe_ma_type(params.get("ma_type"))
    fn = "ta.ema" if ma_type == "EMA" else "ta.sma"
    s, l = f"maShort{idx}", f"maLong{idx}"
    return [
        f"{s} = {fn}(close, {short})",
        f"{l} = {fn}(close, {long})",
    ], f"ta.crossover({s}, {l})"


def _pine_ma_cross_down(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    short = _safe_int(params.get("short_period"), 10)
    long = _safe_int(params.get("long_period"), 20)
    ma_type = _safe_ma_type(params.get("ma_type"))
    fn = "ta.ema" if ma_type == "EMA" else "ta.sma"
    s, l = f"maShort{idx}", f"maLong{idx}"
    return [
        f"{s} = {fn}(close, {short})",
        f"{l} = {fn}(close, {long})",
    ], f"ta.crossunder({s}, {l})"


def _pine_above_ma(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 20)
    ma_type = _safe_ma_type(params.get("ma_type"))
    fn = "ta.ema" if ma_type == "EMA" else "ta.sma"
    v = f"maLine{idx}"
    return [f"{v} = {fn}(close, {period})"], f"close > {v}"


def _pine_below_ma(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 20)
    ma_type = _safe_ma_type(params.get("ma_type"))
    fn = "ta.ema" if ma_type == "EMA" else "ta.sma"
    v = f"maLine{idx}"
    return [f"{v} = {fn}(close, {period})"], f"close < {v}"


def _pine_ma_touch(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 20)
    tolerance = _safe_float(params.get("tolerance"), 0.02)
    ml, mt = f"maTouchLine{idx}", f"maTouchTol{idx}"
    return [
        f"{ml} = ta.sma(close, {period})",
        f"{mt} = {ml} * {tolerance}",
    ], f"math.abs(close - {ml}) <= {mt}"


def _pine_rsi_oversold(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 14)
    threshold = _safe_int(params.get("threshold"), 30)
    v = f"rsiVal{idx}"
    return [f"{v} = ta.rsi(close, {period})"], f"{v} < {threshold}"


def _pine_rsi_overbought(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 14)
    threshold = _safe_int(params.get("threshold"), 70)
    v = f"rsiVal{idx}"
    return [f"{v} = ta.rsi(close, {period})"], f"{v} > {threshold}"


def _pine_rsi_range(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 14)
    lower = _safe_int(params.get("lower"), 30)
    upper = _safe_int(params.get("upper"), 70)
    v = f"rsiVal{idx}"
    return [f"{v} = ta.rsi(close, {period})"], f"{v} >= {lower} and {v} <= {upper}"


def _pine_macd_cross_up(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    fast = _safe_int(params.get("fast_period"), 12)
    slow = _safe_int(params.get("slow_period"), 26)
    signal = _safe_int(params.get("signal_period"), 9)
    ml, sl = f"macdLine{idx}", f"signalLine{idx}"
    return [
        f"[{ml}, {sl}, _] = ta.macd(close, {fast}, {slow}, {signal})",
    ], f"ta.crossover({ml}, {sl})"


def _pine_macd_cross_down(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    fast = _safe_int(params.get("fast_period"), 12)
    slow = _safe_int(params.get("slow_period"), 26)
    signal = _safe_int(params.get("signal_period"), 9)
    ml, sl = f"macdLine{idx}", f"signalLine{idx}"
    return [
        f"[{ml}, {sl}, _] = ta.macd(close, {fast}, {slow}, {signal})",
    ], f"ta.crossunder({ml}, {sl})"


def _pine_bb_lower_touch(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 20)
    std_dev = _safe_float(params.get("std_dev"), 2.0)
    bm, bu, bl = f"bbMiddle{idx}", f"bbUpper{idx}", f"bbLower{idx}"
    return [
        f"[{bm}, {bu}, {bl}] = ta.bb(close, {period}, {std_dev})",
    ], f"close <= {bl}"


def _pine_bb_upper_touch(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 20)
    std_dev = _safe_float(params.get("std_dev"), 2.0)
    bm, bu, bl = f"bbMiddle{idx}", f"bbUpper{idx}", f"bbLower{idx}"
    return [
        f"[{bm}, {bu}, {bl}] = ta.bb(close, {period}, {std_dev})",
    ], f"close >= {bu}"


def _pine_min_volume(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    min_vol = _safe_int(params.get("min_volume"), 100000)
    return [], f"volume >= {min_vol}"


def _pine_volume_above_avg(params: Dict[str, Any], idx: int) -> Tuple[List[str], str]:
    period = _safe_int(params.get("period"), 20)
    multiplier = _safe_float(params.get("multiplier"), 1.5)
    v = f"avgVol{idx}"
    return [
        f"{v} = ta.sma(volume, {period})",
    ], f"volume >= {v} * {multiplier}"


_PINE_COMPILERS = {
    "ma_cross_up": _pine_ma_cross_up,
    "ma_cross_down": _pine_ma_cross_down,
    "above_ma": _pine_above_ma,
    "below_ma": _pine_below_ma,
    "ma_touch": _pine_ma_touch,
    "rsi_oversold": _pine_rsi_oversold,
    "rsi_overbought": _pine_rsi_overbought,
    "rsi_range": _pine_rsi_range,
    "macd_cross_up": _pine_macd_cross_up,
    "macd_cross_down": _pine_macd_cross_down,
    "bb_lower_touch": _pine_bb_lower_touch,
    "bb_upper_touch": _pine_bb_upper_touch,
    "min_volume": _pine_min_volume,
    "volume_above_avg": _pine_volume_above_avg,
}


def export_pine_script(
    graph: dict,
    strategy_name: str = "QuantCanvas Strategy",
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
) -> str:
    """Transpile a strategy graph into Pine Script v5.

    All conditions are combined with AND logic. Each condition instance
    gets unique variable names (suffixed with index) to avoid collisions
    when multiple conditions of the same type are used.

    Args:
        graph: Strategy graph dict with nodes and edges.
        strategy_name: Name for the Pine Script strategy.
        take_profit: Optional take-profit ratio (e.g. 0.05 = 5%).
        stop_loss: Optional stop-loss ratio (e.g. 0.03 = 3%).

    Returns:
        Pine Script v5 code as string.
    """
    safe_name = _sanitize_string(strategy_name)

    nodes = graph.get("nodes", [])
    conditions = []
    skipped = []

    for node in nodes:
        data = node.get("data", {})
        if data.get("node_type") != "condition":
            continue
        ct = data.get("condition_type", "")
        params = data.get("params", {})
        compiler = _PINE_COMPILERS.get(ct)
        if compiler:
            conditions.append((ct, params, compiler))
        else:
            skipped.append(ct)

    if not conditions:
        # Return a stub script with comments instead of raising an error,
        # so the frontend can show a graceful warning.
        stub_lines = [
            "//@version=5",
            f'strategy("{safe_name}", overlay=true)',
            "",
            "// No exportable conditions found.",
        ]
        if skipped:
            stub_lines.append(f"// Skipped unsupported conditions: {', '.join(_sanitize_string(str(s)) for s in skipped)}")
        stub_lines.append("")
        return "\n".join(stub_lines)

    # Build script
    lines = [
        '//@version=5',
        f'strategy("{safe_name}", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100)',
        '',
        '// --- Indicator Calculations ---',
        '// NOTE: All conditions are combined with AND logic.',
    ]

    all_setup_lines: List[str] = []
    condition_exprs: List[str] = []

    for idx, (ct, params, compiler) in enumerate(conditions):
        setup_lines, expr = compiler(params, idx)
        all_setup_lines.extend(setup_lines)
        condition_exprs.append(expr)

    for line in all_setup_lines:
        lines.append(line)

    lines.append('')
    lines.append('// --- Entry Condition ---')

    if len(condition_exprs) == 1:
        lines.append(f'enterLong = {condition_exprs[0]}')
    else:
        combined = " and ".join(f"({e})" for e in condition_exprs)
        lines.append(f'enterLong = {combined}')

    lines.append('')
    lines.append('// --- Strategy Execution ---')
    lines.append('if enterLong')
    lines.append('    strategy.entry("Long", strategy.long)')

    # Exit conditions
    if take_profit is not None or stop_loss is not None:
        tp = _safe_float(take_profit, 0) if take_profit is not None else None
        sl = _safe_float(stop_loss, 0) if stop_loss is not None else None
        lines.append('')
        lines.append('// --- Risk Management ---')
        if tp is not None and sl is not None:
            lines.append(
                f'strategy.exit("Exit", "Long", '
                f'profit=close * {tp}, '
                f'loss=close * {sl})'
            )
        elif tp is not None:
            lines.append(
                f'strategy.exit("Exit", "Long", profit=close * {tp})'
            )
        else:
            lines.append(
                f'strategy.exit("Exit", "Long", loss=close * {sl})'
            )

    # Add skipped warnings
    if skipped:
        lines.append('')
        lines.append('// --- Warnings ---')
        for s in skipped:
            safe_s = _sanitize_string(str(s))
            lines.append(f'// Skipped unsupported condition: {safe_s}')

    lines.append('')
    return '\n'.join(lines)
