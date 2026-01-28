"""
Evaluators Module
조건 평가기 모듈

Usage:
    from discovery.evaluators import get_evaluator, EVALUATOR_MAP
    from discovery.evaluators.ma import eval_ma_touch
    from discovery.evaluators.rsi import eval_rsi_oversold
"""

from typing import Dict, Any, Tuple, Callable
import pandas as pd

# Import all evaluators
from .ma import (
    eval_ma_touch,
    eval_above_ma,
    eval_below_ma,
    eval_ma_cross_up,
    eval_ma_cross_down,
)
from .rsi import (
    eval_rsi_oversold,
    eval_rsi_overbought,
    eval_rsi_range,
)
from .volume import (
    eval_volume_spike,
    eval_volume_above_avg,
)
from .bollinger import (
    eval_bb_lower_touch,
    eval_bb_upper_touch,
)
from .helpers import (
    calculate_rsi,
    calculate_ma,
    calculate_bollinger_bands,
    is_valid_data,
)

# Import ConditionType for mapping
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from models.condition import ConditionType


def eval_not_implemented(data: pd.DataFrame, params: Dict[str, Any]) -> Tuple[bool, Dict]:
    """미구현 조건"""
    return False, {"error": "Condition type not implemented"}


# Evaluator mapping
EVALUATOR_MAP: Dict[ConditionType, Callable] = {
    ConditionType.MA_TOUCH: eval_ma_touch,
    ConditionType.ABOVE_MA: eval_above_ma,
    ConditionType.BELOW_MA: eval_below_ma,
    ConditionType.MA_CROSS_UP: eval_ma_cross_up,
    ConditionType.MA_CROSS_DOWN: eval_ma_cross_down,
    ConditionType.RSI_OVERSOLD: eval_rsi_oversold,
    ConditionType.RSI_OVERBOUGHT: eval_rsi_overbought,
    ConditionType.RSI_RANGE: eval_rsi_range,
    ConditionType.VOLUME_SPIKE: eval_volume_spike,
    ConditionType.VOLUME_ABOVE_AVG: eval_volume_above_avg,
    ConditionType.BB_LOWER_TOUCH: eval_bb_lower_touch,
    ConditionType.BB_UPPER_TOUCH: eval_bb_upper_touch,
}


def get_evaluator(condition_type: ConditionType) -> Callable:
    """
    조건 타입에 맞는 평가 함수 반환

    Args:
        condition_type: ConditionType enum

    Returns:
        평가 함수
    """
    return EVALUATOR_MAP.get(condition_type, eval_not_implemented)


__all__ = [
    # Main function
    'get_evaluator',
    'EVALUATOR_MAP',
    'eval_not_implemented',

    # MA evaluators
    'eval_ma_touch',
    'eval_above_ma',
    'eval_below_ma',
    'eval_ma_cross_up',
    'eval_ma_cross_down',

    # RSI evaluators
    'eval_rsi_oversold',
    'eval_rsi_overbought',
    'eval_rsi_range',

    # Volume evaluators
    'eval_volume_spike',
    'eval_volume_above_avg',

    # Bollinger evaluators
    'eval_bb_lower_touch',
    'eval_bb_upper_touch',

    # Helpers
    'calculate_rsi',
    'calculate_ma',
    'calculate_bollinger_bands',
    'is_valid_data',
]
