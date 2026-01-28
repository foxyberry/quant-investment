"""
Bollinger Band Evaluators
볼린저밴드 평가기

Usage:
    from discovery.evaluators.bollinger import eval_bb_lower_touch, eval_bb_upper_touch
"""

from typing import Dict, Any, Tuple
import pandas as pd

from .helpers import calculate_bollinger_bands, is_valid_data


def eval_bb_lower_touch(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    볼린저밴드 하단 터치 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period, std, tolerance}

    Returns:
        (matched, details)
    """
    period = params.get("period", 20)
    std_mult = params.get("std", 2)
    tolerance = params.get("tolerance", 0.01)

    close = data['close']
    upper_band, _, lower_band = calculate_bollinger_bands(close, period, std_mult)

    current_price = close.iloc[-1]
    lower_value = lower_band.iloc[-1]

    if not is_valid_data(lower_value):
        return False, {"error": "Insufficient data for BB calculation"}

    distance_pct = (current_price - lower_value) / lower_value
    matched = distance_pct <= tolerance

    return matched, {
        "current_price": float(current_price),
        "lower_band": float(lower_value),
        "distance_pct": float(distance_pct),
        "tolerance": tolerance,
        "period": period,
    }


def eval_bb_upper_touch(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    볼린저밴드 상단 터치 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period, std, tolerance}

    Returns:
        (matched, details)
    """
    period = params.get("period", 20)
    std_mult = params.get("std", 2)
    tolerance = params.get("tolerance", 0.01)

    close = data['close']
    upper_band, _, lower_band = calculate_bollinger_bands(close, period, std_mult)

    current_price = close.iloc[-1]
    upper_value = upper_band.iloc[-1]

    if not is_valid_data(upper_value):
        return False, {"error": "Insufficient data for BB calculation"}

    distance_pct = (upper_value - current_price) / upper_value
    matched = distance_pct <= tolerance

    return matched, {
        "current_price": float(current_price),
        "upper_band": float(upper_value),
        "distance_pct": float(distance_pct),
        "tolerance": tolerance,
        "period": period,
    }
