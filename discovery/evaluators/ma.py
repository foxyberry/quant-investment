"""
Moving Average Evaluators
이동평균선 평가기

Usage:
    from discovery.evaluators.ma import eval_ma_touch, eval_above_ma
"""

from typing import Dict, Any, Tuple
import pandas as pd

from .helpers import calculate_ma, is_valid_data


def eval_ma_touch(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    이동평균선 터치 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period, tolerance}

    Returns:
        (matched, details)
    """
    period = params.get("period", 20)
    tolerance = params.get("tolerance", 0.02)

    close = data['close']
    ma = calculate_ma(close, period)

    current_price = close.iloc[-1]
    ma_value = ma.iloc[-1]

    if not is_valid_data(ma_value):
        return False, {"error": "Insufficient data for MA calculation"}

    distance_pct = abs(current_price - ma_value) / ma_value
    matched = distance_pct <= tolerance

    return matched, {
        "current_price": float(current_price),
        "ma_value": float(ma_value),
        "ma_period": period,
        "distance_pct": float(distance_pct),
        "tolerance": tolerance,
    }


def eval_above_ma(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    MA 위에 있는지 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period}

    Returns:
        (matched, details)
    """
    period = params.get("period", 20)

    close = data['close']
    ma = calculate_ma(close, period)

    current_price = close.iloc[-1]
    ma_value = ma.iloc[-1]

    if not is_valid_data(ma_value):
        return False, {"error": "Insufficient data for MA calculation"}

    matched = current_price > ma_value

    return matched, {
        "current_price": float(current_price),
        "ma_value": float(ma_value),
        "ma_period": period,
        "distance_pct": float((current_price - ma_value) / ma_value),
    }


def eval_below_ma(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    MA 아래에 있는지 평가

    Args:
        data: OHLCV 데이터프레임
        params: {period}

    Returns:
        (matched, details)
    """
    period = params.get("period", 20)

    close = data['close']
    ma = calculate_ma(close, period)

    current_price = close.iloc[-1]
    ma_value = ma.iloc[-1]

    if not is_valid_data(ma_value):
        return False, {"error": "Insufficient data for MA calculation"}

    matched = current_price < ma_value

    return matched, {
        "current_price": float(current_price),
        "ma_value": float(ma_value),
        "ma_period": period,
        "distance_pct": float((current_price - ma_value) / ma_value),
    }


def eval_ma_cross_up(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    골든크로스 평가 (단기MA가 장기MA를 상향돌파)

    Args:
        data: OHLCV 데이터프레임
        params: {short_period, long_period}

    Returns:
        (matched, details)
    """
    short_period = params.get("short_period", 20)
    long_period = params.get("long_period", 60)

    close = data['close']
    short_ma = calculate_ma(close, short_period)
    long_ma = calculate_ma(close, long_period)

    if not is_valid_data(short_ma.iloc[-1]) or not is_valid_data(long_ma.iloc[-1]):
        return False, {"error": "Insufficient data for MA calculation"}

    # Check for crossover in last 2 days
    prev_short = short_ma.iloc[-2]
    prev_long = long_ma.iloc[-2]
    curr_short = short_ma.iloc[-1]
    curr_long = long_ma.iloc[-1]

    matched = prev_short <= prev_long and curr_short > curr_long

    return matched, {
        "short_ma": float(curr_short),
        "long_ma": float(curr_long),
        "short_period": short_period,
        "long_period": long_period,
        "prev_short_ma": float(prev_short),
        "prev_long_ma": float(prev_long),
    }


def eval_ma_cross_down(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """
    데드크로스 평가 (단기MA가 장기MA를 하향돌파)

    Args:
        data: OHLCV 데이터프레임
        params: {short_period, long_period}

    Returns:
        (matched, details)
    """
    short_period = params.get("short_period", 20)
    long_period = params.get("long_period", 60)

    close = data['close']
    short_ma = calculate_ma(close, short_period)
    long_ma = calculate_ma(close, long_period)

    if not is_valid_data(short_ma.iloc[-1]) or not is_valid_data(long_ma.iloc[-1]):
        return False, {"error": "Insufficient data for MA calculation"}

    # Check for crossover in last 2 days
    prev_short = short_ma.iloc[-2]
    prev_long = long_ma.iloc[-2]
    curr_short = short_ma.iloc[-1]
    curr_long = long_ma.iloc[-1]

    matched = prev_short >= prev_long and curr_short < curr_long

    return matched, {
        "short_ma": float(curr_short),
        "long_ma": float(curr_long),
        "short_period": short_period,
        "long_period": long_period,
        "prev_short_ma": float(prev_short),
        "prev_long_ma": float(prev_long),
    }
