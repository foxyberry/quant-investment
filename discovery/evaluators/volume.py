"""
Volume Evaluators
거래량 평가기

Usage:
    from discovery.evaluators.volume import eval_volume_spike, eval_volume_above_avg
"""

from typing import Dict, Any, Tuple
import pandas as pd

from .helpers import is_valid_data


def eval_volume_spike(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    거래량 급증 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period, multiplier}

    Returns:
        (matched, details)
    """
    period = params.get("period", 20)
    multiplier = params.get("multiplier", 2.0)

    volume = data['volume']
    avg_volume = volume.rolling(period).mean()

    current_volume = volume.iloc[-1]
    avg_vol = avg_volume.iloc[-1]

    if not is_valid_data(avg_vol) or avg_vol == 0:
        return False, {"error": "Insufficient data for volume calculation"}

    ratio = current_volume / avg_vol
    matched = ratio >= multiplier

    return matched, {
        "current_volume": float(current_volume),
        "avg_volume": float(avg_vol),
        "ratio": float(ratio),
        "multiplier": multiplier,
        "period": period,
    }


def eval_volume_above_avg(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    평균 이상 거래량 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period, multiplier}

    Returns:
        (matched, details)
    """
    period = params.get("period", 20)
    multiplier = params.get("multiplier", 1.5)

    return eval_volume_spike(data, {"period": period, "multiplier": multiplier})
