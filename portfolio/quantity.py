"""
Quantity Calculator
매수/매도 수량 계산

Usage:
    from portfolio.quantity import calculate_quantity, QuantityMethod

    # 고정 수량
    qty = calculate_quantity(method="fixed", value=10)

    # 금액 기반
    qty = calculate_quantity(
        method="amount",
        value=1000000,
        current_price=70000
    )

    # 퍼센트 기반 (보유 수량의 50%)
    qty = calculate_quantity(
        method="percent",
        value=50,
        holdings_quantity=100
    )

    # 포트폴리오 비율 기반
    qty = calculate_quantity(
        method="portfolio_pct",
        value=5,  # 5% of portfolio
        portfolio_value=10000000,
        current_price=70000
    )
"""

import math
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class QuantityMethod(Enum):
    """수량 계산 방식"""
    FIXED = "fixed"  # 고정 수량
    AMOUNT = "amount"  # 금액 기반
    PERCENT = "percent"  # 보유 비율 기반
    PORTFOLIO_PCT = "portfolio_pct"  # 포트폴리오 비율 기반
    ALL = "all"  # 전량


@dataclass
class QuantityConfig:
    """수량 계산 설정"""
    method: QuantityMethod
    value: float
    min_quantity: int = 1
    round_down: bool = True  # 내림 처리 여부

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "value": self.value,
            "min_quantity": self.min_quantity,
            "round_down": self.round_down,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuantityConfig":
        return cls(
            method=QuantityMethod(data["method"]),
            value=data["value"],
            min_quantity=data.get("min_quantity", 1),
            round_down=data.get("round_down", True),
        )


def calculate_quantity(
    method: str,
    value: float,
    current_price: Optional[float] = None,
    holdings_quantity: Optional[int] = None,
    portfolio_value: Optional[float] = None,
    min_quantity: int = 1,
    round_down: bool = True,
    commission_rate: float = 0.0
) -> int:
    """
    매수/매도 수량 계산

    Args:
        method: 계산 방식 (fixed, amount, percent, portfolio_pct, all)
        value: 값 (수량, 금액, 퍼센트 등)
        current_price: 현재가 (amount, portfolio_pct에 필요)
        holdings_quantity: 보유 수량 (percent, all에 필요)
        portfolio_value: 포트폴리오 총 가치 (portfolio_pct에 필요)
        min_quantity: 최소 주문 수량
        round_down: 내림 처리 여부
        commission_rate: 수수료율 (금액 기반 계산시 고려)

    Returns:
        계산된 수량

    Raises:
        ValueError: 필수 파라미터 누락시
    """
    qty_method = QuantityMethod(method)

    if qty_method == QuantityMethod.FIXED:
        # 고정 수량
        quantity = int(value)

    elif qty_method == QuantityMethod.AMOUNT:
        # 금액 기반
        if current_price is None or current_price <= 0:
            raise ValueError("current_price is required for amount-based calculation")

        # 수수료 고려
        effective_amount = value * (1 - commission_rate)
        quantity = effective_amount / current_price

        if round_down:
            quantity = math.floor(quantity)
        else:
            quantity = round(quantity)

    elif qty_method == QuantityMethod.PERCENT:
        # 보유 수량의 퍼센트
        if holdings_quantity is None:
            raise ValueError("holdings_quantity is required for percent-based calculation")

        quantity = holdings_quantity * (value / 100)

        if round_down:
            quantity = math.floor(quantity)
        else:
            quantity = round(quantity)

    elif qty_method == QuantityMethod.PORTFOLIO_PCT:
        # 포트폴리오 비율 기반
        if portfolio_value is None:
            raise ValueError("portfolio_value is required for portfolio_pct calculation")
        if current_price is None or current_price <= 0:
            raise ValueError("current_price is required for portfolio_pct calculation")

        target_amount = portfolio_value * (value / 100)
        effective_amount = target_amount * (1 - commission_rate)
        quantity = effective_amount / current_price

        if round_down:
            quantity = math.floor(quantity)
        else:
            quantity = round(quantity)

    elif qty_method == QuantityMethod.ALL:
        # 전량
        if holdings_quantity is None:
            raise ValueError("holdings_quantity is required for all calculation")
        quantity = holdings_quantity

    else:
        raise ValueError(f"Unknown method: {method}")

    # 최소 수량 적용
    quantity = max(int(quantity), 0)

    # min_quantity 체크 (0이 아닌 경우에만)
    if quantity > 0 and quantity < min_quantity:
        quantity = min_quantity

    return quantity


def calculate_buy_quantity(
    budget: float,
    current_price: float,
    min_quantity: int = 1,
    commission_rate: float = 0.00015,  # 0.015% 기본 수수료
    round_down: bool = True
) -> Dict[str, Any]:
    """
    매수 수량 계산 (편의 함수)

    Args:
        budget: 투자 금액
        current_price: 현재가
        min_quantity: 최소 주문 수량
        commission_rate: 수수료율
        round_down: 내림 처리

    Returns:
        {
            "quantity": int,
            "total_cost": float,
            "commission": float,
            "remaining": float
        }
    """
    quantity = calculate_quantity(
        method="amount",
        value=budget,
        current_price=current_price,
        min_quantity=min_quantity,
        commission_rate=commission_rate,
        round_down=round_down
    )

    if quantity == 0:
        return {
            "quantity": 0,
            "total_cost": 0,
            "commission": 0,
            "remaining": budget,
        }

    base_cost = quantity * current_price
    commission = base_cost * commission_rate
    total_cost = base_cost + commission
    remaining = budget - total_cost

    return {
        "quantity": quantity,
        "total_cost": total_cost,
        "commission": commission,
        "remaining": remaining,
    }


def calculate_sell_quantity(
    holdings_quantity: int,
    sell_pct: float = 100,
    min_quantity: int = 1
) -> Dict[str, Any]:
    """
    매도 수량 계산 (편의 함수)

    Args:
        holdings_quantity: 보유 수량
        sell_pct: 매도 비율 (%)
        min_quantity: 최소 주문 수량

    Returns:
        {
            "quantity": int,
            "remaining": int,
            "is_full_sell": bool
        }
    """
    if sell_pct >= 100:
        # 전량 매도
        return {
            "quantity": holdings_quantity,
            "remaining": 0,
            "is_full_sell": True,
        }

    quantity = calculate_quantity(
        method="percent",
        value=sell_pct,
        holdings_quantity=holdings_quantity,
        min_quantity=min_quantity
    )

    remaining = holdings_quantity - quantity
    is_full_sell = remaining == 0

    return {
        "quantity": quantity,
        "remaining": remaining,
        "is_full_sell": is_full_sell,
    }


def estimate_position_size(
    portfolio_value: float,
    risk_per_trade_pct: float = 2.0,
    stop_loss_pct: float = 5.0,
    current_price: float = 0
) -> Dict[str, Any]:
    """
    포지션 사이징 (위험 기반)

    Kelly Criterion 간소화 버전:
    Position Size = (Risk per Trade) / (Stop Loss %)

    Args:
        portfolio_value: 포트폴리오 총 가치
        risk_per_trade_pct: 거래당 허용 손실 (%)
        stop_loss_pct: 손절 비율 (%)
        current_price: 현재가

    Returns:
        {
            "position_value": float,
            "position_pct": float,
            "quantity": int (current_price가 있을 때)
        }
    """
    # Position % = Risk % / Stop Loss %
    position_pct = risk_per_trade_pct / stop_loss_pct * 100

    # Cap at 100%
    position_pct = min(position_pct, 100)

    position_value = portfolio_value * (position_pct / 100)

    result = {
        "position_value": position_value,
        "position_pct": position_pct,
        "max_loss": portfolio_value * (risk_per_trade_pct / 100),
    }

    if current_price and current_price > 0:
        result["quantity"] = math.floor(position_value / current_price)

    return result
