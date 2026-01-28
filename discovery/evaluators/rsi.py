"""
RSI Evaluators
RSI 평가기

Usage:
    from discovery.evaluators.rsi import eval_rsi_oversold, eval_rsi_overbought
"""

from typing import Dict, Any, Tuple
import pandas as pd

from .helpers import calculate_rsi, is_valid_data


def eval_rsi_oversold(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    RSI 과매도 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period, threshold}

    Returns:
        (matched, details)
    """
    period = params.get("period", 14)
    threshold = params.get("threshold", 30)

    rsi = calculate_rsi(data['close'], period)

    if not is_valid_data(rsi.iloc[-1]):
        return False, {"error": "Insufficient data for RSI calculation"}

    current_rsi = rsi.iloc[-1]
    matched = current_rsi <= threshold

    return matched, {
        "rsi": float(current_rsi),
        "threshold": threshold,
        "period": period,
    }


def eval_rsi_overbought(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    RSI 과매수 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period, threshold}

    Returns:
        (matched, details)
    """
    period = params.get("period", 14)
    threshold = params.get("threshold", 70)

    rsi = calculate_rsi(data['close'], period)

    if not is_valid_data(rsi.iloc[-1]):
        return False, {"error": "Insufficient data for RSI calculation"}

    current_rsi = rsi.iloc[-1]
    matched = current_rsi >= threshold

    return matched, {
        "rsi": float(current_rsi),
        "threshold": threshold,
        "period": period,
    }


def eval_rsi_range(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    RSI 범위 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period, lower, upper}

    Returns:
        (matched, details)
    """
    period = params.get("period", 14)
    lower = params.get("lower", 30)
    upper = params.get("upper", 70)

    rsi = calculate_rsi(data['close'], period)

    if not is_valid_data(rsi.iloc[-1]):
        return False, {"error": "Insufficient data for RSI calculation"}

    current_rsi = rsi.iloc[-1]
    matched = lower <= current_rsi <= upper

    return matched, {
        "rsi": float(current_rsi),
        "lower": lower,
        "upper": upper,
        "period": period,
    }
