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
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from kiwoom.chejan_handler import ChejanHandler, OrderStatus as KiwoomChejanStatus
from kiwoom.constants import HogaType as KiwoomHogaType
from kiwoom.constants import OrderType as KiwoomOrderType
from kiwoom.order import KiwoomOrderManager
from portfolio.risk_module.manager import RiskManager, create_default_risk_manager


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


class KiwoomExecutor(BaseExecutor):
    """Kiwoom-backed live order executor."""

    def __init__(
        self,
        order_manager: KiwoomOrderManager,
        chejan_handler: ChejanHandler,
        account_no: str,
        screen_no: str = "9000",
        risk_manager: Optional[RiskManager] = None,
        risk_context_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self._order_manager = order_manager
        self._chejan_handler = chejan_handler
        self._account_no = account_no
        self._screen_no = screen_no
        self._risk_manager = risk_manager or create_default_risk_manager()
        self._risk_context_provider = risk_context_provider
        self._orders: Dict[str, Order] = {}
        self._results: Dict[str, OrderResult] = {}
        self._order_id_to_broker_no: Dict[str, str] = {}
        self._broker_no_to_order_id: Dict[str, str] = {}
        self._chejan_handler.add_observer(self._on_chejan_event)

    @staticmethod
    def _normalize_code(ticker: str) -> str:
        code = ticker.strip().upper()
        if code.endswith(".KS") or code.endswith(".KQ"):
            code = code.split(".")[0]
        return code

    @staticmethod
    def _to_kiwoom_order_type(side: str) -> int:
        return int(KiwoomOrderType.NEW_BUY) if side.upper() == "BUY" else int(KiwoomOrderType.NEW_SELL)

    @staticmethod
    def _to_kiwoom_hoga(order_type: str) -> str:
        if order_type.upper() == "MARKET":
            return KiwoomHogaType.MARKET.value
        return KiwoomHogaType.LIMIT.value

    def _build_risk_context(self, order: Order) -> Dict[str, Any]:
        if self._risk_context_provider is None:
            return {
                "portfolio_value": 100_000_000.0,
                "cash_balance": 100_000_000.0,
                "positions": {},
                "daily_pnl": 0.0,
                "daily_trades": 0,
            }
        try:
            snapshot = self._risk_context_provider()
            if isinstance(snapshot, dict):
                return snapshot
        except Exception:
            self.logger.exception("risk_context_provider failed")
        return {
            "portfolio_value": 100_000_000.0,
            "cash_balance": 100_000_000.0,
            "positions": {},
            "daily_pnl": 0.0,
            "daily_trades": 0,
        }

    def _validate_risk(self, order: Order, price: float) -> Optional[str]:
        snapshot = self._build_risk_context(order)
        result = self._risk_manager.validate_order(
            ticker=self._normalize_code(order.ticker),
            side=order.side.upper(),
            quantity=order.quantity,
            price=price,
            portfolio_value=float(snapshot.get("portfolio_value", 0.0)),
            cash_balance=float(snapshot.get("cash_balance", 0.0)),
            positions=snapshot.get("positions", {}),
            daily_pnl=float(snapshot.get("daily_pnl", 0.0)),
            daily_trades=int(snapshot.get("daily_trades", 0)),
        )
        if result.allowed:
            return None
        messages = ", ".join(v.message for v in result.violations) or "risk validation failed"
        return messages

    def execute(self, order: Order) -> OrderResult:
        self._orders[order.order_id] = order
        code = self._normalize_code(order.ticker)
        kiwoom_order_type = self._to_kiwoom_order_type(order.side)
        hoga_type = self._to_kiwoom_hoga(order.order_type)
        price = int(order.price or 0) if hoga_type == KiwoomHogaType.LIMIT.value else 0

        risk_error = self._validate_risk(order, float(price or order.price or 0))
        if risk_error:
            result = OrderResult(
                order_id=order.order_id,
                success=False,
                status=OrderStatus.REJECTED.value,
                message=f"Risk blocked: {risk_error}",
                simulated=False,
            )
            self._results[order.order_id] = result
            return result

        try:
            broker_order_no = self._order_manager.send_order(
                rq_name=f"pf_{order.order_id}",
                screen_no=self._screen_no,
                acc_no=self._account_no,
                order_type=kiwoom_order_type,
                code=code,
                qty=int(order.quantity),
                price=price,
                hoga_type=hoga_type,
                org_order_no="",
            )
            self._order_id_to_broker_no[order.order_id] = broker_order_no
            self._broker_no_to_order_id[broker_order_no] = order.order_id
            result = OrderResult(
                order_id=order.order_id,
                success=True,
                status=OrderStatus.PENDING.value,
                message=f"Order submitted: {broker_order_no}",
                simulated=False,
            )
            self._results[order.order_id] = result
            return result
        except Exception as exc:
            result = OrderResult(
                order_id=order.order_id,
                success=False,
                status=OrderStatus.REJECTED.value,
                message=str(exc),
                simulated=False,
            )
            self._results[order.order_id] = result
            return result

    def cancel(self, order_id: str) -> bool:
        base_order = self._orders.get(order_id)
        broker_order_no = self._order_id_to_broker_no.get(order_id)
        if base_order is None or not broker_order_no:
            return False
        try:
            cancel_type = int(KiwoomOrderType.CANCEL_BUY) if base_order.side.upper() == "BUY" else int(KiwoomOrderType.CANCEL_SELL)
            self._order_manager.send_order(
                rq_name=f"cancel_{order_id}",
                screen_no=self._screen_no,
                acc_no=self._account_no,
                order_type=cancel_type,
                code=self._normalize_code(base_order.ticker),
                qty=int(base_order.quantity),
                price=0,
                hoga_type=KiwoomHogaType.LIMIT.value,
                org_order_no=broker_order_no,
            )
            current = self._results.get(order_id)
            if current:
                current.status = OrderStatus.CANCELLED.value
                current.message = "Cancel requested"
            return True
        except Exception:
            self.logger.exception("cancel failed for %s", order_id)
            return False

    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        result = self._results.get(order_id)
        if result is None:
            return None
        broker_order_no = self._order_id_to_broker_no.get(order_id)
        if not broker_order_no:
            return result
        chejan_status = self._chejan_handler.get_order_status(broker_order_no)
        if chejan_status is None:
            return result
        if chejan_status == KiwoomChejanStatus.FILLED:
            result.status = OrderStatus.FILLED.value
            result.success = True
        elif chejan_status == KiwoomChejanStatus.PARTIAL:
            result.status = OrderStatus.PARTIAL.value
        elif chejan_status == KiwoomChejanStatus.CANCELLED:
            result.status = OrderStatus.CANCELLED.value
        elif chejan_status == KiwoomChejanStatus.REJECTED:
            result.status = OrderStatus.REJECTED.value
            result.success = False
        return result

    def _on_chejan_event(self, payload: Dict[str, Any]) -> None:
        if payload.get("type") != "order":
            return
        broker_order_no = str(payload.get("order_no", ""))
        order_id = self._broker_no_to_order_id.get(broker_order_no)
        if not order_id:
            return
        result = self._results.get(order_id)
        if not result:
            return
        status = str(payload.get("status", ""))
        if status == KiwoomChejanStatus.FILLED.value:
            result.status = OrderStatus.FILLED.value
            result.success = True
            result.fill_price = float(payload.get("fill_price", 0) or 0)
            result.fill_quantity = int(payload.get("filled_qty", 0) or 0)
            result.message = str(payload.get("raw_status", "filled"))
        elif status == KiwoomChejanStatus.PARTIAL.value:
            result.status = OrderStatus.PARTIAL.value
            result.success = True
            result.fill_price = float(payload.get("fill_price", 0) or 0)
            result.fill_quantity = int(payload.get("filled_qty", 0) or 0)
            result.message = str(payload.get("raw_status", "partial"))
        elif status == KiwoomChejanStatus.CANCELLED.value:
            result.status = OrderStatus.CANCELLED.value
            result.message = str(payload.get("raw_status", "cancelled"))
        elif status == KiwoomChejanStatus.REJECTED.value:
            result.status = OrderStatus.REJECTED.value
            result.success = False
            result.message = str(payload.get("raw_status", "rejected"))


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
