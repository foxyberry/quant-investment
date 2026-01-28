"""
Condition Evaluator
퀀트 조건 평가기

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드는 discovery.evaluators 모듈을 직접 사용하세요.

Usage:
    # 기존 방식 (호환성 유지)
    from discovery import evaluate_condition

    # 권장 방식
    from discovery.evaluators import get_evaluator, eval_ma_touch
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.condition import Condition, ConditionType, ConditionResult
from utils.fetch import get_ohlcv

# Import evaluators from new module structure
from .evaluators import get_evaluator, EVALUATOR_MAP


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
    evaluator = get_evaluator(condition.type)
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


# Re-export for backward compatibility
_get_evaluator = get_evaluator
