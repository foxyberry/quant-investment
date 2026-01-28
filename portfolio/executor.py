"""
Order Executor
주문 실행 (Paper Trading / Live)

Usage:
    from portfolio.executor import Order, OrderExecutor

    # Paper Trading (Dry-run)
    executor = OrderExecutor(dry_run=True)
    order = Order(ticker="005930.KS", side="BUY", quantity=10)
    result = executor.execute(order)

    if result.success:
        print(f"Simulated: {result.fill_price} x {result.fill_quantity}")
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class OrderSide(Enum):
    """주문 방향"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """주문 유형"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    SIMULATED = "SIMULATED"


@dataclass
class Order:
    """주문 데이터"""
    ticker: str
    side: str  # BUY or SELL
    quantity: int
    price: Optional[float] = None  # None for market order
    order_type: str = "MARKET"
    order_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.order_id is None:
            self.order_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class OrderResult:
    """주문 실행 결과"""
    order_id: str
    success: bool
    status: str
    fill_price: Optional[float] = None
    fill_quantity: Optional[int] = None
    commission: float = 0.0
    message: str = ""
    simulated: bool = False
    executed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "success": self.success,
            "status": self.status,
            "fill_price": self.fill_price,
            "fill_quantity": self.fill_quantity,
            "commission": self.commission,
            "message": self.message,
            "simulated": self.simulated,
            "executed_at": self.executed_at.isoformat(),
        }

    @property
    def total_value(self) -> float:
        """총 거래 금액"""
        if self.fill_price and self.fill_quantity:
            return self.fill_price * self.fill_quantity + self.commission
        return 0


class BaseExecutor(ABC):
    """주문 실행기 기본 클래스"""

    @abstractmethod
    def execute(self, order: Order) -> OrderResult:
        """주문 실행"""
        pass

    @abstractmethod
    def cancel(self, order_id: str) -> bool:
        """주문 취소"""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        """주문 상태 조회"""
        pass


class PaperExecutor(BaseExecutor):
    """Paper Trading 실행기 (시뮬레이션)"""

    def __init__(
        self,
        slippage_pct: float = 0.001,  # 0.1% 슬리피지
        commission_rate: float = 0.00015,  # 0.015% 수수료
        initial_balance: float = 10000000
    ):
        self.slippage_pct = slippage_pct
        self.commission_rate = commission_rate
        self.balance = initial_balance
        self.logger = logging.getLogger(__name__)

        self._orders: Dict[str, Order] = {}
        self._results: Dict[str, OrderResult] = {}
        self._positions: Dict[str, Dict[str, Any]] = {}  # Virtual positions
        self._trade_log: List[Dict[str, Any]] = []

    def execute(self, order: Order, market_price: Optional[float] = None) -> OrderResult:
        """
        주문 시뮬레이션 실행

        Args:
            order: 주문 데이터
            market_price: 현재 시장가 (없으면 주문 가격 사용)
        """
        self._orders[order.order_id] = order

        # Determine fill price
        if order.order_type == "MARKET":
            if market_price is None:
                return OrderResult(
                    order_id=order.order_id,
                    success=False,
                    status=OrderStatus.REJECTED.value,
                    message="Market price required for market order simulation",
                    simulated=True,
                )
            base_price = market_price
        else:
            base_price = order.price or market_price or 0

        if base_price <= 0:
            return OrderResult(
                order_id=order.order_id,
                success=False,
                status=OrderStatus.REJECTED.value,
                message="Invalid price",
                simulated=True,
            )

        # Apply slippage
        if order.side == "BUY":
            fill_price = base_price * (1 + self.slippage_pct)
        else:
            fill_price = base_price * (1 - self.slippage_pct)

        # Calculate commission
        trade_value = fill_price * order.quantity
        commission = trade_value * self.commission_rate

        # Check balance for buy orders
        if order.side == "BUY":
            total_cost = trade_value + commission
            if total_cost > self.balance:
                return OrderResult(
                    order_id=order.order_id,
                    success=False,
                    status=OrderStatus.REJECTED.value,
                    message=f"Insufficient balance: {self.balance:,.0f} < {total_cost:,.0f}",
                    simulated=True,
                )
            self.balance -= total_cost

            # Update position
            if order.ticker not in self._positions:
                self._positions[order.ticker] = {"quantity": 0, "avg_price": 0}

            pos = self._positions[order.ticker]
            total_cost_before = pos["quantity"] * pos["avg_price"]
            total_quantity = pos["quantity"] + order.quantity
            if total_quantity > 0:
                pos["avg_price"] = (total_cost_before + trade_value) / total_quantity
            pos["quantity"] = total_quantity

        else:  # SELL
            if order.ticker not in self._positions:
                return OrderResult(
                    order_id=order.order_id,
                    success=False,
                    status=OrderStatus.REJECTED.value,
                    message=f"No position for {order.ticker}",
                    simulated=True,
                )

            pos = self._positions[order.ticker]
            if pos["quantity"] < order.quantity:
                return OrderResult(
                    order_id=order.order_id,
                    success=False,
                    status=OrderStatus.REJECTED.value,
                    message=f"Insufficient quantity: {pos['quantity']} < {order.quantity}",
                    simulated=True,
                )

            self.balance += trade_value - commission
            pos["quantity"] -= order.quantity

            if pos["quantity"] == 0:
                del self._positions[order.ticker]

        # Create result
        result = OrderResult(
            order_id=order.order_id,
            success=True,
            status=OrderStatus.SIMULATED.value,
            fill_price=fill_price,
            fill_quantity=order.quantity,
            commission=commission,
            message="Paper trade executed",
            simulated=True,
        )

        self._results[order.order_id] = result

        # Log trade
        self._trade_log.append({
            "order": order.to_dict(),
            "result": result.to_dict(),
            "balance_after": self.balance,
        })

        self.logger.info(
            f"[PAPER] {order.side} {order.ticker}: "
            f"{order.quantity} @ {fill_price:,.0f} (commission: {commission:,.0f})"
        )

        return result

    def cancel(self, order_id: str) -> bool:
        """Paper trading에서는 즉시 체결되므로 취소 불가"""
        return False

    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        """주문 결과 조회"""
        return self._results.get(order_id)

    def get_balance(self) -> float:
        """현재 잔고"""
        return self.balance

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """가상 포지션"""
        return self._positions.copy()

    def get_trade_log(self) -> List[Dict[str, Any]]:
        """거래 로그"""
        return self._trade_log.copy()

    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """포트폴리오 총 가치"""
        position_value = sum(
            pos["quantity"] * prices.get(ticker, pos["avg_price"])
            for ticker, pos in self._positions.items()
        )
        return self.balance + position_value

    def reset(self, initial_balance: float = 10000000) -> None:
        """상태 초기화"""
        self.balance = initial_balance
        self._orders.clear()
        self._results.clear()
        self._positions.clear()
        self._trade_log.clear()


class OrderExecutor:
    """통합 주문 실행기"""

    def __init__(
        self,
        dry_run: bool = True,
        slippage_pct: float = 0.001,
        commission_rate: float = 0.00015,
        initial_balance: float = 10000000
    ):
        """
        Args:
            dry_run: True면 Paper Trading, False면 Live 실행
            slippage_pct: 슬리피지 (Paper Trading용)
            commission_rate: 수수료율
            initial_balance: 초기 잔고 (Paper Trading용)
        """
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

        if dry_run:
            self._executor = PaperExecutor(
                slippage_pct=slippage_pct,
                commission_rate=commission_rate,
                initial_balance=initial_balance
            )
        else:
            # Live executor requires broker setup
            self._executor = None
            self.logger.warning("Live trading not configured. Use set_live_executor()")

    def execute(
        self,
        order: Order,
        market_price: Optional[float] = None,
        dry_run: Optional[bool] = None
    ) -> OrderResult:
        """
        주문 실행

        Args:
            order: 주문 데이터
            market_price: 현재 시장가
            dry_run: 실행 모드 오버라이드
        """
        use_dry_run = dry_run if dry_run is not None else self.dry_run

        if use_dry_run:
            if isinstance(self._executor, PaperExecutor):
                return self._executor.execute(order, market_price)
            else:
                # Fallback paper executor
                paper = PaperExecutor()
                return paper.execute(order, market_price)
        else:
            if self._executor is None:
                return OrderResult(
                    order_id=order.order_id,
                    success=False,
                    status=OrderStatus.REJECTED.value,
                    message="Live executor not configured",
                    simulated=False,
                )
            return self._executor.execute(order)

    def cancel(self, order_id: str) -> bool:
        """주문 취소"""
        if self._executor:
            return self._executor.cancel(order_id)
        return False

    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        """주문 상태 조회"""
        if self._executor:
            return self._executor.get_order_status(order_id)
        return None

    def set_live_executor(self, executor: BaseExecutor) -> None:
        """Live 실행기 설정"""
        self._executor = executor
        self.dry_run = False
        self.logger.info("Live executor configured")

    # Paper trading specific methods
    def get_paper_balance(self) -> Optional[float]:
        """Paper trading 잔고"""
        if isinstance(self._executor, PaperExecutor):
            return self._executor.get_balance()
        return None

    def get_paper_positions(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Paper trading 포지션"""
        if isinstance(self._executor, PaperExecutor):
            return self._executor.get_positions()
        return None

    def get_trade_log(self) -> List[Dict[str, Any]]:
        """거래 로그"""
        if isinstance(self._executor, PaperExecutor):
            return self._executor.get_trade_log()
        return []

    def reset_paper_trading(self, initial_balance: float = 10000000) -> None:
        """Paper trading 초기화"""
        if isinstance(self._executor, PaperExecutor):
            self._executor.reset(initial_balance)
