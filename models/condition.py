"""
Quant Condition Schema
퀀트 스크리닝 조건 정의

Usage:
    from models.condition import Condition, ConditionType

    # 단일 조건
    condition = Condition(
        type=ConditionType.MA_TOUCH,
        params={"period": 240, "tolerance": 0.02}
    )

    # 조건 조합
    combined = CombinedCondition(
        conditions=[ma_condition, rsi_condition],
        operator="AND"
    )
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
import yaml


class ConditionType(Enum):
    """퀀트 조건 타입"""
    # 이동평균선 관련
    MA_TOUCH = "ma_touch"           # MA 터치 (근접)
    MA_CROSS_UP = "ma_cross_up"     # 골든크로스
    MA_CROSS_DOWN = "ma_cross_down" # 데드크로스
    ABOVE_MA = "above_ma"           # MA 위
    BELOW_MA = "below_ma"           # MA 아래

    # 모멘텀 지표
    RSI_OVERSOLD = "rsi_oversold"       # RSI 과매도
    RSI_OVERBOUGHT = "rsi_overbought"   # RSI 과매수
    RSI_RANGE = "rsi_range"             # RSI 범위 내

    # MACD
    MACD_CROSS_UP = "macd_cross_up"     # MACD 골든크로스
    MACD_CROSS_DOWN = "macd_cross_down" # MACD 데드크로스

    # 볼린저 밴드
    BB_LOWER_TOUCH = "bb_lower_touch"   # 하단 밴드 터치
    BB_UPPER_TOUCH = "bb_upper_touch"   # 상단 밴드 터치

    # 거래량
    VOLUME_SPIKE = "volume_spike"       # 거래량 급증
    VOLUME_ABOVE_AVG = "volume_above_avg"  # 평균 이상 거래량

    # 가격
    PRICE_RANGE = "price_range"         # 가격 범위 내
    NEW_HIGH = "new_high"               # 신고가
    NEW_LOW = "new_low"                 # 신저가

    # 복합
    CUSTOM = "custom"                   # 사용자 정의


# 각 조건 타입별 기본 파라미터
DEFAULT_PARAMS: Dict[ConditionType, Dict[str, Any]] = {
    ConditionType.MA_TOUCH: {"period": 20, "tolerance": 0.02},
    ConditionType.MA_CROSS_UP: {"short_period": 20, "long_period": 60},
    ConditionType.MA_CROSS_DOWN: {"short_period": 20, "long_period": 60},
    ConditionType.ABOVE_MA: {"period": 20},
    ConditionType.BELOW_MA: {"period": 20},
    ConditionType.RSI_OVERSOLD: {"period": 14, "threshold": 30},
    ConditionType.RSI_OVERBOUGHT: {"period": 14, "threshold": 70},
    ConditionType.RSI_RANGE: {"period": 14, "lower": 30, "upper": 70},
    ConditionType.MACD_CROSS_UP: {"fast": 12, "slow": 26, "signal": 9},
    ConditionType.MACD_CROSS_DOWN: {"fast": 12, "slow": 26, "signal": 9},
    ConditionType.BB_LOWER_TOUCH: {"period": 20, "std": 2, "tolerance": 0.01},
    ConditionType.BB_UPPER_TOUCH: {"period": 20, "std": 2, "tolerance": 0.01},
    ConditionType.VOLUME_SPIKE: {"period": 20, "multiplier": 2.0},
    ConditionType.VOLUME_ABOVE_AVG: {"period": 20, "multiplier": 1.5},
    ConditionType.PRICE_RANGE: {"min_price": 0, "max_price": float('inf')},
    ConditionType.NEW_HIGH: {"period": 52},  # 52주 신고가
    ConditionType.NEW_LOW: {"period": 52},   # 52주 신저가
    ConditionType.CUSTOM: {},
}


@dataclass
class Condition:
    """단일 퀀트 조건"""
    type: ConditionType
    params: Dict[str, Any] = field(default_factory=dict)
    name: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self):
        # 문자열로 들어온 경우 Enum으로 변환
        if isinstance(self.type, str):
            self.type = ConditionType(self.type)

        # 기본 파라미터와 병합
        default = DEFAULT_PARAMS.get(self.type, {}).copy()
        default.update(self.params)
        self.params = default

        # 이름이 없으면 자동 생성
        if self.name is None:
            self.name = self._generate_name()

    def _generate_name(self) -> str:
        """조건 이름 자동 생성"""
        type_name = self.type.value.replace("_", " ").title()
        if self.type in [ConditionType.MA_TOUCH, ConditionType.ABOVE_MA, ConditionType.BELOW_MA]:
            return f"{type_name} ({self.params.get('period', '')})"
        elif self.type in [ConditionType.RSI_OVERSOLD, ConditionType.RSI_OVERBOUGHT]:
            return f"{type_name} ({self.params.get('threshold', '')})"
        return type_name

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "type": self.type.value,
            "params": self.params,
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Condition":
        """딕셔너리에서 생성"""
        return cls(
            type=ConditionType(data["type"]),
            params=data.get("params", {}),
            name=data.get("name"),
            description=data.get("description"),
        )

    def __str__(self) -> str:
        return f"Condition({self.name})"

    def __repr__(self) -> str:
        return f"Condition(type={self.type.value}, params={self.params})"


@dataclass
class ConditionResult:
    """조건 평가 결과"""
    condition: Condition
    matched: bool
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None

    def __str__(self) -> str:
        status = "MATCHED" if self.matched else "NOT MATCHED"
        return f"{self.condition.name}: {status}"


@dataclass
class CombinedCondition:
    """복합 조건 (AND/OR 조합)"""
    conditions: List[Condition]
    operator: str = "AND"  # "AND" or "OR"
    name: Optional[str] = None

    def __post_init__(self):
        if self.operator not in ["AND", "OR"]:
            raise ValueError(f"Invalid operator: {self.operator}. Must be 'AND' or 'OR'")

        if self.name is None:
            cond_names = [c.name for c in self.conditions]
            self.name = f" {self.operator} ".join(cond_names)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "conditions": [c.to_dict() for c in self.conditions],
            "operator": self.operator,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CombinedCondition":
        """딕셔너리에서 생성"""
        conditions = [Condition.from_dict(c) for c in data["conditions"]]
        return cls(
            conditions=conditions,
            operator=data.get("operator", "AND"),
            name=data.get("name"),
        )

    @classmethod
    def combine(
        cls,
        conditions: List[Condition],
        operator: str = "AND"
    ) -> "CombinedCondition":
        """조건들을 조합"""
        return cls(conditions=conditions, operator=operator)

    def __str__(self) -> str:
        return f"CombinedCondition({self.name})"


def save_conditions(conditions: List[Union[Condition, CombinedCondition]], filepath: str):
    """조건들을 YAML 파일로 저장"""
    data = []
    for cond in conditions:
        if isinstance(cond, CombinedCondition):
            data.append({"combined": cond.to_dict()})
        else:
            data.append(cond.to_dict())

    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def load_conditions(filepath: str) -> List[Union[Condition, CombinedCondition]]:
    """YAML 파일에서 조건들을 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    conditions = []
    for item in data:
        if "combined" in item:
            conditions.append(CombinedCondition.from_dict(item["combined"]))
        else:
            conditions.append(Condition.from_dict(item))

    return conditions
