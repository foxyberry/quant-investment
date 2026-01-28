"""
Condition Trigger Detection
조건 트리거 감지

Usage:
    from portfolio.trigger import ConditionChecker, TriggerCondition

    checker = ConditionChecker()
    checker.add_condition("005930.KS", "PRICE_ABOVE", 80000)
    checker.add_condition("AAPL", "PRICE_BELOW", 150)

    def on_triggered(event):
        print(f"ALERT: {event['ticker']} - {event['message']}")

    checker.on_triggered(on_triggered)
    checker.check({"005930.KS": 81000, "AAPL": 148})
"""

import logging
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum


class TriggerType(Enum):
    """트리거 조건 타입"""
    PRICE_ABOVE = "PRICE_ABOVE"
    PRICE_BELOW = "PRICE_BELOW"
    PRICE_EQUALS = "PRICE_EQUALS"
    CHANGE_PCT_ABOVE = "CHANGE_PCT_ABOVE"
    CHANGE_PCT_BELOW = "CHANGE_PCT_BELOW"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


@dataclass
class TriggerCondition:
    """트리거 조건"""
    ticker: str
    condition_type: TriggerType
    target: float
    tolerance: float = 0.0  # For PRICE_EQUALS
    recurring: bool = False  # One-time vs recurring
    cooldown_minutes: int = 60  # Cooldown between triggers
    enabled: bool = True

    # Internal state
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "condition_type": self.condition_type.value,
            "target": self.target,
            "tolerance": self.tolerance,
            "recurring": self.recurring,
            "cooldown_minutes": self.cooldown_minutes,
            "enabled": self.enabled,
            "trigger_count": self.trigger_count,
        }


@dataclass
class TriggerEvent:
    """트리거 이벤트"""
    ticker: str
    condition_type: str
    target: float
    actual: float
    message: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "condition_type": self.condition_type,
            "target": self.target,
            "actual": self.actual,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class ConditionChecker:
    """조건 트리거 체커"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._conditions: List[TriggerCondition] = []
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._event_log: List[TriggerEvent] = []

    def add_condition(
        self,
        ticker: str,
        condition_type: str,
        target: float,
        tolerance: float = 0.0,
        recurring: bool = False,
        cooldown_minutes: int = 60
    ) -> TriggerCondition:
        """
        조건 추가

        Args:
            ticker: 종목 코드
            condition_type: 조건 타입 (PRICE_ABOVE, PRICE_BELOW, etc.)
            target: 목표 값
            tolerance: 허용 오차 (PRICE_EQUALS용)
            recurring: 반복 트리거 여부
            cooldown_minutes: 쿨다운 시간 (분)

        Returns:
            생성된 TriggerCondition
        """
        cond_type = TriggerType(condition_type)

        condition = TriggerCondition(
            ticker=ticker,
            condition_type=cond_type,
            target=target,
            tolerance=tolerance,
            recurring=recurring,
            cooldown_minutes=cooldown_minutes,
        )
        self._conditions.append(condition)
        self.logger.info(f"Added condition: {ticker} {condition_type} {target}")
        return condition

    def remove_condition(self, ticker: str, condition_type: Optional[str] = None) -> int:
        """
        조건 제거

        Args:
            ticker: 종목 코드
            condition_type: 조건 타입 (None이면 모든 조건)

        Returns:
            제거된 조건 수
        """
        before = len(self._conditions)

        if condition_type:
            cond_type = TriggerType(condition_type)
            self._conditions = [
                c for c in self._conditions
                if not (c.ticker == ticker and c.condition_type == cond_type)
            ]
        else:
            self._conditions = [c for c in self._conditions if c.ticker != ticker]

        removed = before - len(self._conditions)
        if removed:
            self.logger.info(f"Removed {removed} condition(s) for {ticker}")
        return removed

    def get_conditions(self, ticker: Optional[str] = None) -> List[TriggerCondition]:
        """조건 조회"""
        if ticker:
            return [c for c in self._conditions if c.ticker == ticker]
        return self._conditions.copy()

    def on_triggered(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """트리거 콜백 등록"""
        self._callbacks.append(callback)

    def check(self, prices: Dict[str, float]) -> List[TriggerEvent]:
        """
        조건 체크

        Args:
            prices: {ticker: current_price} 딕셔너리

        Returns:
            발생한 트리거 이벤트 목록
        """
        events = []
        now = datetime.now()

        for condition in self._conditions:
            if not condition.enabled:
                continue

            ticker = condition.ticker
            if ticker not in prices:
                continue

            current_price = prices[ticker]

            # Check cooldown
            if condition.last_triggered:
                cooldown_end = condition.last_triggered + timedelta(minutes=condition.cooldown_minutes)
                if now < cooldown_end:
                    continue

            # Check condition
            triggered, message = self._evaluate_condition(condition, current_price)

            if triggered:
                event = TriggerEvent(
                    ticker=ticker,
                    condition_type=condition.condition_type.value,
                    target=condition.target,
                    actual=current_price,
                    message=message,
                    timestamp=now,
                )
                events.append(event)
                self._event_log.append(event)

                # Update condition state
                condition.last_triggered = now
                condition.trigger_count += 1

                # Disable if one-time
                if not condition.recurring:
                    condition.enabled = False

                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(event.to_dict())
                    except Exception as e:
                        self.logger.error(f"Callback error: {e}")

                self.logger.info(f"Trigger: {message}")

        return events

    def _evaluate_condition(
        self,
        condition: TriggerCondition,
        current_price: float
    ) -> tuple[bool, str]:
        """조건 평가"""
        ticker = condition.ticker
        target = condition.target
        cond_type = condition.condition_type

        if cond_type == TriggerType.PRICE_ABOVE:
            if current_price >= target:
                return True, f"{ticker} price ({current_price:,.0f}) reached target ({target:,.0f})"

        elif cond_type == TriggerType.PRICE_BELOW:
            if current_price <= target:
                return True, f"{ticker} price ({current_price:,.0f}) dropped to target ({target:,.0f})"

        elif cond_type == TriggerType.PRICE_EQUALS:
            tolerance = condition.tolerance or (target * 0.01)  # 1% default
            if abs(current_price - target) <= tolerance:
                return True, f"{ticker} price ({current_price:,.0f}) near target ({target:,.0f})"

        elif cond_type == TriggerType.STOP_LOSS:
            if current_price <= target:
                return True, f"STOP LOSS: {ticker} ({current_price:,.0f}) hit stop ({target:,.0f})"

        elif cond_type == TriggerType.TAKE_PROFIT:
            if current_price >= target:
                return True, f"TAKE PROFIT: {ticker} ({current_price:,.0f}) reached target ({target:,.0f})"

        return False, ""

    def check_with_change(
        self,
        prices: Dict[str, float],
        changes: Dict[str, float]
    ) -> List[TriggerEvent]:
        """
        가격 변동률 포함 조건 체크

        Args:
            prices: {ticker: current_price}
            changes: {ticker: change_pct}
        """
        events = self.check(prices)
        now = datetime.now()

        for condition in self._conditions:
            if not condition.enabled:
                continue

            ticker = condition.ticker
            if ticker not in changes:
                continue

            change_pct = changes[ticker]
            cond_type = condition.condition_type
            target = condition.target

            triggered = False
            message = ""

            if cond_type == TriggerType.CHANGE_PCT_ABOVE:
                if change_pct >= target:
                    triggered = True
                    message = f"{ticker} change ({change_pct:.1f}%) exceeded {target:.1f}%"

            elif cond_type == TriggerType.CHANGE_PCT_BELOW:
                if change_pct <= target:
                    triggered = True
                    message = f"{ticker} change ({change_pct:.1f}%) dropped below {target:.1f}%"

            if triggered:
                # Check cooldown
                if condition.last_triggered:
                    cooldown_end = condition.last_triggered + timedelta(minutes=condition.cooldown_minutes)
                    if now < cooldown_end:
                        continue

                event = TriggerEvent(
                    ticker=ticker,
                    condition_type=cond_type.value,
                    target=target,
                    actual=change_pct,
                    message=message,
                    timestamp=now,
                )
                events.append(event)
                self._event_log.append(event)

                condition.last_triggered = now
                condition.trigger_count += 1

                if not condition.recurring:
                    condition.enabled = False

                for callback in self._callbacks:
                    try:
                        callback(event.to_dict())
                    except Exception as e:
                        self.logger.error(f"Callback error: {e}")

        return events

    def get_event_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """이벤트 로그 조회"""
        return [e.to_dict() for e in self._event_log[-limit:]]

    def clear_event_log(self) -> None:
        """이벤트 로그 초기화"""
        self._event_log.clear()

    def reset_conditions(self) -> None:
        """모든 조건 상태 초기화"""
        for condition in self._conditions:
            condition.last_triggered = None
            condition.trigger_count = 0
            condition.enabled = True
