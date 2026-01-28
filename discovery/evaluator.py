"""
Condition Evaluator
퀀트 조건 평가기

Usage:
    from discovery import evaluate_condition
    from models.condition import Condition, ConditionType

    condition = Condition(type=ConditionType.MA_TOUCH, params={"period": 240})
    result = evaluate_condition("005930.KS", condition)

    if result.matched:
        print(f"Condition matched! Details: {result.details}")
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.condition import Condition, ConditionType, ConditionResult, CombinedCondition
from utils.fetch import get_ohlcv


def evaluate_condition(
    ticker: str,
    condition: Condition,
    data: Optional[pd.DataFrame] = None
) -> ConditionResult:
    """
    단일 조건 평가

    Args:
        ticker: 종목 코드
        condition: 평가할 조건
        data: 가격 데이터 (없으면 자동 조회)

    Returns:
        ConditionResult 객체
    """
    # Fetch data if not provided
    if data is None:
        days = _get_required_days(condition)
        data = get_ohlcv(ticker, days=days)

    # Evaluate based on condition type
    evaluator = _get_evaluator(condition.type)
    matched, details = evaluator(data, condition.params)

    return ConditionResult(
        condition=condition,
        matched=bool(matched),  # Ensure Python bool, not numpy.bool
        details=details,
        timestamp=datetime.now().isoformat()
    )


def evaluate_conditions(
    ticker: str,
    conditions: List[Condition],
    operator: str = "AND"
) -> Dict[str, Any]:
    """
    여러 조건 평가

    Args:
        ticker: 종목 코드
        conditions: 평가할 조건 목록
        operator: 조합 연산자 ("AND" or "OR")

    Returns:
        {
            "ticker": str,
            "overall_matched": bool,
            "results": List[ConditionResult],
            "timestamp": str
        }
    """
    # Fetch data once for all conditions
    max_days = max(_get_required_days(c) for c in conditions)
    data = get_ohlcv(ticker, days=max_days)

    results = []
    for condition in conditions:
        result = evaluate_condition(ticker, condition, data)
        results.append(result)

    # Combine results
    if operator == "AND":
        overall_matched = all(r.matched for r in results)
    else:  # OR
        overall_matched = any(r.matched for r in results)

    return {
        "ticker": ticker,
        "overall_matched": overall_matched,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


def _get_required_days(condition: Condition) -> int:
    """조건 평가에 필요한 데이터 일수 계산"""
    params = condition.params

    # MA related
    if condition.type in [ConditionType.MA_TOUCH, ConditionType.ABOVE_MA, ConditionType.BELOW_MA]:
        return params.get("period", 20) + 50

    if condition.type in [ConditionType.MA_CROSS_UP, ConditionType.MA_CROSS_DOWN]:
        return max(params.get("short_period", 20), params.get("long_period", 60)) + 50

    # RSI
    if condition.type in [ConditionType.RSI_OVERSOLD, ConditionType.RSI_OVERBOUGHT, ConditionType.RSI_RANGE]:
        return params.get("period", 14) + 50

    # MACD
    if condition.type in [ConditionType.MACD_CROSS_UP, ConditionType.MACD_CROSS_DOWN]:
        return params.get("slow", 26) + params.get("signal", 9) + 50

    # Bollinger Bands
    if condition.type in [ConditionType.BB_LOWER_TOUCH, ConditionType.BB_UPPER_TOUCH]:
        return params.get("period", 20) + 50

    # Volume
    if condition.type in [ConditionType.VOLUME_SPIKE, ConditionType.VOLUME_ABOVE_AVG]:
        return params.get("period", 20) + 50

    # New high/low
    if condition.type in [ConditionType.NEW_HIGH, ConditionType.NEW_LOW]:
        return params.get("period", 52) * 5 + 50  # weeks to days

    return 365  # Default


def _get_evaluator(condition_type: ConditionType):
    """조건 타입에 맞는 평가 함수 반환"""
    evaluators = {
        ConditionType.MA_TOUCH: _eval_ma_touch,
        ConditionType.ABOVE_MA: _eval_above_ma,
        ConditionType.BELOW_MA: _eval_below_ma,
        ConditionType.MA_CROSS_UP: _eval_ma_cross_up,
        ConditionType.MA_CROSS_DOWN: _eval_ma_cross_down,
        ConditionType.RSI_OVERSOLD: _eval_rsi_oversold,
        ConditionType.RSI_OVERBOUGHT: _eval_rsi_overbought,
        ConditionType.RSI_RANGE: _eval_rsi_range,
        ConditionType.VOLUME_SPIKE: _eval_volume_spike,
        ConditionType.VOLUME_ABOVE_AVG: _eval_volume_above_avg,
        ConditionType.BB_LOWER_TOUCH: _eval_bb_lower_touch,
        ConditionType.BB_UPPER_TOUCH: _eval_bb_upper_touch,
    }
    return evaluators.get(condition_type, _eval_not_implemented)


# ============================================================
# Evaluation Functions
# ============================================================

def _eval_ma_touch(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """이동평균선 터치 평가"""
    period = params.get("period", 20)
    tolerance = params.get("tolerance", 0.02)

    close = data['close']
    ma = close.rolling(period).mean()

    current_price = close.iloc[-1]
    ma_value = ma.iloc[-1]

    if pd.isna(ma_value):
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


def _eval_above_ma(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """MA 위에 있는지 평가"""
    period = params.get("period", 20)

    close = data['close']
    ma = close.rolling(period).mean()

    current_price = close.iloc[-1]
    ma_value = ma.iloc[-1]

    if pd.isna(ma_value):
        return False, {"error": "Insufficient data for MA calculation"}

    matched = current_price > ma_value

    return matched, {
        "current_price": float(current_price),
        "ma_value": float(ma_value),
        "ma_period": period,
        "distance_pct": float((current_price - ma_value) / ma_value),
    }


def _eval_below_ma(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """MA 아래에 있는지 평가"""
    period = params.get("period", 20)

    close = data['close']
    ma = close.rolling(period).mean()

    current_price = close.iloc[-1]
    ma_value = ma.iloc[-1]

    if pd.isna(ma_value):
        return False, {"error": "Insufficient data for MA calculation"}

    matched = current_price < ma_value

    return matched, {
        "current_price": float(current_price),
        "ma_value": float(ma_value),
        "ma_period": period,
        "distance_pct": float((current_price - ma_value) / ma_value),
    }


def _eval_ma_cross_up(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """골든크로스 평가 (단기MA가 장기MA를 상향돌파)"""
    short_period = params.get("short_period", 20)
    long_period = params.get("long_period", 60)

    close = data['close']
    short_ma = close.rolling(short_period).mean()
    long_ma = close.rolling(long_period).mean()

    if pd.isna(short_ma.iloc[-1]) or pd.isna(long_ma.iloc[-1]):
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


def _eval_ma_cross_down(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """데드크로스 평가 (단기MA가 장기MA를 하향돌파)"""
    short_period = params.get("short_period", 20)
    long_period = params.get("long_period", 60)

    close = data['close']
    short_ma = close.rolling(short_period).mean()
    long_ma = close.rolling(long_period).mean()

    if pd.isna(short_ma.iloc[-1]) or pd.isna(long_ma.iloc[-1]):
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


def _eval_rsi_oversold(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """RSI 과매도 평가"""
    period = params.get("period", 14)
    threshold = params.get("threshold", 30)

    rsi = _calculate_rsi(data['close'], period)

    if pd.isna(rsi.iloc[-1]):
        return False, {"error": "Insufficient data for RSI calculation"}

    current_rsi = rsi.iloc[-1]
    matched = current_rsi <= threshold

    return matched, {
        "rsi": float(current_rsi),
        "threshold": threshold,
        "period": period,
    }


def _eval_rsi_overbought(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """RSI 과매수 평가"""
    period = params.get("period", 14)
    threshold = params.get("threshold", 70)

    rsi = _calculate_rsi(data['close'], period)

    if pd.isna(rsi.iloc[-1]):
        return False, {"error": "Insufficient data for RSI calculation"}

    current_rsi = rsi.iloc[-1]
    matched = current_rsi >= threshold

    return matched, {
        "rsi": float(current_rsi),
        "threshold": threshold,
        "period": period,
    }


def _eval_rsi_range(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """RSI 범위 평가"""
    period = params.get("period", 14)
    lower = params.get("lower", 30)
    upper = params.get("upper", 70)

    rsi = _calculate_rsi(data['close'], period)

    if pd.isna(rsi.iloc[-1]):
        return False, {"error": "Insufficient data for RSI calculation"}

    current_rsi = rsi.iloc[-1]
    matched = lower <= current_rsi <= upper

    return matched, {
        "rsi": float(current_rsi),
        "lower": lower,
        "upper": upper,
        "period": period,
    }


def _eval_volume_spike(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """거래량 급증 평가"""
    period = params.get("period", 20)
    multiplier = params.get("multiplier", 2.0)

    volume = data['volume']
    avg_volume = volume.rolling(period).mean()

    current_volume = volume.iloc[-1]
    avg_vol = avg_volume.iloc[-1]

    if pd.isna(avg_vol) or avg_vol == 0:
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


def _eval_volume_above_avg(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """평균 이상 거래량 평가"""
    period = params.get("period", 20)
    multiplier = params.get("multiplier", 1.5)

    return _eval_volume_spike(data, {"period": period, "multiplier": multiplier})


def _eval_bb_lower_touch(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """볼린저밴드 하단 터치 평가"""
    period = params.get("period", 20)
    std_mult = params.get("std", 2)
    tolerance = params.get("tolerance", 0.01)

    close = data['close']
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()

    lower_band = ma - (std_mult * std)

    current_price = close.iloc[-1]
    lower_value = lower_band.iloc[-1]

    if pd.isna(lower_value):
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


def _eval_bb_upper_touch(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """볼린저밴드 상단 터치 평가"""
    period = params.get("period", 20)
    std_mult = params.get("std", 2)
    tolerance = params.get("tolerance", 0.01)

    close = data['close']
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()

    upper_band = ma + (std_mult * std)

    current_price = close.iloc[-1]
    upper_value = upper_band.iloc[-1]

    if pd.isna(upper_value):
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


def _eval_not_implemented(data: pd.DataFrame, params: Dict[str, Any]) -> tuple:
    """미구현 조건"""
    return False, {"error": "Condition type not implemented"}


# ============================================================
# Helper Functions
# ============================================================

def _calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
