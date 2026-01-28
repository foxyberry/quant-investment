"""
Trading Conditions (IoC Pattern)
매매 조건 인터페이스

Usage:
    from portfolio.conditions import (
        TradingContext, TradingCondition,
        StopLossCondition, TakeProfitCondition, TrailingStopCondition
    )

    # 기본 조건 사용
    stop_loss = StopLossCondition(pct=0.05)
    take_profit = TakeProfitCondition(pct=0.15)

    context = TradingContext(
        ticker="005930.KS",
        current_price=75000,
        avg_price=70000,
        quantity=10
    )

    if stop_loss.should_sell(context):
        print("Stop loss triggered!")

    # 커스텀 조건 구현
    class MyCondition(TradingCondition):
        def should_buy(self, context):
            return context.rsi < 30

        def should_sell(self, context):
            return context.rsi > 70
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Protocol
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TradingContext:
    """매매 판단에 필요한 컨텍스트"""
    ticker: str
    current_price: float
    avg_price: Optional[float] = None
    quantity: Optional[int] = None

    # Price history
    high_since_buy: Optional[float] = None
    low_since_buy: Optional[float] = None

    # Technical indicators
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None

    # Volume
    volume: Optional[int] = None
    volume_avg: Optional[float] = None

    # Portfolio context
    portfolio_value: Optional[float] = None
    position_pct: Optional[float] = None

    # Timestamps
    bought_at: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def pnl_pct(self) -> Optional[float]:
        """현재 손익률"""
        if self.avg_price and self.avg_price > 0:
            return (self.current_price - self.avg_price) / self.avg_price
        return None

    @property
    def holding_days(self) -> Optional[int]:
        """보유 일수"""
        if self.bought_at:
            return (datetime.now() - self.bought_at).days
        return None


class TradingCondition(Protocol):
    """매매 조건 프로토콜 (Duck Typing)"""

    def should_buy(self, context: TradingContext) -> bool:
        """매수 조건 충족 여부"""
        ...

    def should_sell(self, context: TradingContext) -> bool:
        """매도 조건 충족 여부"""
        ...


class BaseTradingCondition(ABC):
    """매매 조건 기본 클래스"""

    @abstractmethod
    def should_buy(self, context: TradingContext) -> bool:
        """매수 조건 충족 여부"""
        pass

    @abstractmethod
    def should_sell(self, context: TradingContext) -> bool:
        """매도 조건 충족 여부"""
        pass

    def get_reason(self) -> str:
        """조건 트리거 이유"""
        return ""


class StopLossCondition(BaseTradingCondition):
    """손절 조건"""

    def __init__(self, pct: float = 0.05):
        """
        Args:
            pct: 손절 비율 (0.05 = 5%)
        """
        self.pct = pct
        self._reason = ""

    def should_buy(self, context: TradingContext) -> bool:
        return False

    def should_sell(self, context: TradingContext) -> bool:
        pnl = context.pnl_pct
        if pnl is not None and pnl <= -self.pct:
            self._reason = f"Stop loss triggered: {pnl:.1%} (threshold: -{self.pct:.1%})"
            return True
        return False

    def get_reason(self) -> str:
        return self._reason


class TakeProfitCondition(BaseTradingCondition):
    """익절 조건"""

    def __init__(self, pct: float = 0.15):
        """
        Args:
            pct: 익절 비율 (0.15 = 15%)
        """
        self.pct = pct
        self._reason = ""

    def should_buy(self, context: TradingContext) -> bool:
        return False

    def should_sell(self, context: TradingContext) -> bool:
        pnl = context.pnl_pct
        if pnl is not None and pnl >= self.pct:
            self._reason = f"Take profit triggered: {pnl:.1%} (threshold: +{self.pct:.1%})"
            return True
        return False

    def get_reason(self) -> str:
        return self._reason


class TrailingStopCondition(BaseTradingCondition):
    """트레일링 스탑 조건"""

    def __init__(self, pct: float = 0.08):
        """
        Args:
            pct: 고점 대비 하락 허용 비율 (0.08 = 8%)
        """
        self.pct = pct
        self._reason = ""

    def should_buy(self, context: TradingContext) -> bool:
        return False

    def should_sell(self, context: TradingContext) -> bool:
        if context.high_since_buy and context.current_price:
            drop_pct = (context.high_since_buy - context.current_price) / context.high_since_buy
            if drop_pct >= self.pct:
                self._reason = (
                    f"Trailing stop triggered: {drop_pct:.1%} drop from high "
                    f"({context.high_since_buy:,.0f} → {context.current_price:,.0f})"
                )
                return True
        return False

    def get_reason(self) -> str:
        return self._reason


class RSICondition(BaseTradingCondition):
    """RSI 기반 조건"""

    def __init__(self, oversold: float = 30, overbought: float = 70):
        self.oversold = oversold
        self.overbought = overbought
        self._reason = ""

    def should_buy(self, context: TradingContext) -> bool:
        if context.rsi is not None and context.rsi <= self.oversold:
            self._reason = f"RSI oversold: {context.rsi:.1f} (threshold: {self.oversold})"
            return True
        return False

    def should_sell(self, context: TradingContext) -> bool:
        if context.rsi is not None and context.rsi >= self.overbought:
            self._reason = f"RSI overbought: {context.rsi:.1f} (threshold: {self.overbought})"
            return True
        return False

    def get_reason(self) -> str:
        return self._reason


class MACDCondition(BaseTradingCondition):
    """MACD 기반 조건"""

    def __init__(self):
        self._reason = ""

    def should_buy(self, context: TradingContext) -> bool:
        if context.macd is not None and context.macd_signal is not None:
            if context.macd > context.macd_signal:
                self._reason = f"MACD bullish crossover: {context.macd:.2f} > {context.macd_signal:.2f}"
                return True
        return False

    def should_sell(self, context: TradingContext) -> bool:
        if context.macd is not None and context.macd_signal is not None:
            if context.macd < context.macd_signal:
                self._reason = f"MACD bearish crossover: {context.macd:.2f} < {context.macd_signal:.2f}"
                return True
        return False

    def get_reason(self) -> str:
        return self._reason


class HoldingPeriodCondition(BaseTradingCondition):
    """보유 기간 조건"""

    def __init__(self, min_days: int = 0, max_days: Optional[int] = None):
        """
        Args:
            min_days: 최소 보유 일수 (매도 가능 조건)
            max_days: 최대 보유 일수 (초과시 매도)
        """
        self.min_days = min_days
        self.max_days = max_days
        self._reason = ""

    def should_buy(self, context: TradingContext) -> bool:
        return False

    def should_sell(self, context: TradingContext) -> bool:
        days = context.holding_days
        if days is None:
            return False

        if days < self.min_days:
            return False  # 최소 보유 기간 미충족

        if self.max_days and days >= self.max_days:
            self._reason = f"Max holding period reached: {days} days (max: {self.max_days})"
            return True

        return False

    def get_reason(self) -> str:
        return self._reason


class ConditionChain:
    """조건 체인 (복합 조건)"""

    def __init__(self, operator: str = "OR"):
        """
        Args:
            operator: "AND" 또는 "OR"
        """
        self.operator = operator.upper()
        self._conditions: List[BaseTradingCondition] = []
        self._triggered: List[BaseTradingCondition] = []

    def add(self, condition: BaseTradingCondition) -> "ConditionChain":
        """조건 추가"""
        self._conditions.append(condition)
        return self

    def should_buy(self, context: TradingContext) -> bool:
        """매수 조건 체크"""
        self._triggered.clear()

        if self.operator == "AND":
            for cond in self._conditions:
                if not cond.should_buy(context):
                    return False
                self._triggered.append(cond)
            return len(self._conditions) > 0
        else:  # OR
            for cond in self._conditions:
                if cond.should_buy(context):
                    self._triggered.append(cond)
                    return True
            return False

    def should_sell(self, context: TradingContext) -> bool:
        """매도 조건 체크"""
        self._triggered.clear()

        if self.operator == "AND":
            for cond in self._conditions:
                if not cond.should_sell(context):
                    return False
                self._triggered.append(cond)
            return len(self._conditions) > 0
        else:  # OR
            for cond in self._conditions:
                if cond.should_sell(context):
                    self._triggered.append(cond)
                    return True
            return False

    def get_triggered_reasons(self) -> List[str]:
        """트리거된 조건들의 이유"""
        return [c.get_reason() for c in self._triggered if c.get_reason()]


# Factory functions
def create_default_sell_conditions(
    stop_loss_pct: float = 0.05,
    take_profit_pct: float = 0.15,
    trailing_stop_pct: float = 0.08
) -> ConditionChain:
    """기본 매도 조건 생성"""
    chain = ConditionChain(operator="OR")
    chain.add(StopLossCondition(pct=stop_loss_pct))
    chain.add(TakeProfitCondition(pct=take_profit_pct))
    chain.add(TrailingStopCondition(pct=trailing_stop_pct))
    return chain


def create_technical_conditions(
    rsi_oversold: float = 30,
    rsi_overbought: float = 70
) -> ConditionChain:
    """기술적 지표 기반 조건 생성"""
    chain = ConditionChain(operator="OR")
    chain.add(RSICondition(oversold=rsi_oversold, overbought=rsi_overbought))
    chain.add(MACDCondition())
    return chain
