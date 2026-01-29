"""
Composite Conditions
조건 조합 (AND/OR)

Usage:
    from screener.conditions.composite import AndCondition, OrCondition

    # AND 조합
    condition = AndCondition([
        MinPriceCondition(5000),
        MATouchCondition(160)
    ])

    # OR 조합
    condition = OrCondition([
        RSIOversoldCondition(30),
        MATouchCondition(200)
    ])
"""

from typing import List
import pandas as pd

from .base import BaseCondition, ConditionResult


class AndCondition(BaseCondition):
    """AND 조합 조건 (모든 조건 충족)"""

    def __init__(self, conditions: List[BaseCondition]):
        """
        Args:
            conditions: 조합할 조건 목록
        """
        self.conditions = conditions

    @property
    def name(self) -> str:
        names = [c.name for c in self.conditions]
        return f"AND({', '.join(names)})"

    @property
    def required_days(self) -> int:
        return max(c.required_days for c in self.conditions) if self.conditions else 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        results = []
        all_matched = True

        for condition in self.conditions:
            result = condition.evaluate(ticker, data)
            results.append(result)
            if not result.matched:
                all_matched = False

        return ConditionResult(
            matched=all_matched,
            condition_name=self.name,
            details={
                "sub_results": [
                    {
                        "name": r.condition_name,
                        "matched": r.matched,
                        "details": r.details
                    }
                    for r in results
                ],
                "matched_count": sum(1 for r in results if r.matched),
                "total_count": len(results),
            }
        )

    def __repr__(self) -> str:
        return f"AndCondition({self.conditions})"


class OrCondition(BaseCondition):
    """OR 조합 조건 (하나 이상 충족)"""

    def __init__(self, conditions: List[BaseCondition]):
        """
        Args:
            conditions: 조합할 조건 목록
        """
        self.conditions = conditions

    @property
    def name(self) -> str:
        names = [c.name for c in self.conditions]
        return f"OR({', '.join(names)})"

    @property
    def required_days(self) -> int:
        return max(c.required_days for c in self.conditions) if self.conditions else 1

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        results = []
        any_matched = False

        for condition in self.conditions:
            result = condition.evaluate(ticker, data)
            results.append(result)
            if result.matched:
                any_matched = True

        return ConditionResult(
            matched=any_matched,
            condition_name=self.name,
            details={
                "sub_results": [
                    {
                        "name": r.condition_name,
                        "matched": r.matched,
                        "details": r.details
                    }
                    for r in results
                ],
                "matched_count": sum(1 for r in results if r.matched),
                "total_count": len(results),
            }
        )

    def __repr__(self) -> str:
        return f"OrCondition({self.conditions})"


class NotCondition(BaseCondition):
    """NOT 조건 (반전)"""

    def __init__(self, condition: BaseCondition):
        """
        Args:
            condition: 반전할 조건
        """
        self.condition = condition

    @property
    def name(self) -> str:
        return f"NOT({self.condition.name})"

    @property
    def required_days(self) -> int:
        return self.condition.required_days

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        result = self.condition.evaluate(ticker, data)

        return ConditionResult(
            matched=not result.matched,
            condition_name=self.name,
            details={
                "original_result": {
                    "name": result.condition_name,
                    "matched": result.matched,
                    "details": result.details
                }
            }
        )

    def __repr__(self) -> str:
        return f"NotCondition({self.condition})"
