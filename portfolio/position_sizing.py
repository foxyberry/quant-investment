"""
Position Sizing Module
포지션 사이징 모듈

This module calculates recommended position sizes based on:
- Total capital
- Risk score (1-10 scale)
- Stop loss percentage
- Maximum position size constraints

Usage:
    from portfolio.position_sizing import PositionSizer, PositionRecommendation

    sizer = PositionSizer(
        total_capital=100000,
        max_position_pct=0.10,  # Max 10% per position
        max_risk_per_trade_pct=0.02,  # Max 2% risk per trade
    )

    # Single calculation
    recommendation = sizer.calculate(
        ticker="AAPL",
        current_price=185.50,
        risk_score=5,  # 1-10 scale
        stop_loss_pct=0.05,  # 5% stop loss
    )

    print(f"Buy {recommendation.shares} shares at ${recommendation.current_price}")
    print(f"Risk amount: ${recommendation.risk_amount:.2f}")

    # Batch calculation
    tickers = [
        ("AAPL", 185.50, 5),
        ("MSFT", 420.00, 3),
        ("TSLA", 250.00, 8),
    ]
    recommendations = sizer.calculate_batch(tickers)
"""

import math
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class PositionRecommendation:
    """
    Position size recommendation result.
    포지션 사이즈 추천 결과.

    Attributes:
        ticker: Stock ticker symbol
        current_price: Current stock price
        shares: Recommended number of shares to buy
        amount: Total position amount (shares * current_price)
        position_pct: Position size as percentage of total capital
        stop_loss_price: Calculated stop loss price
        stop_loss_pct: Stop loss percentage used
        risk_amount: Maximum loss if stop loss is triggered
        currency: Currency symbol ($ or won)
    """
    ticker: str
    current_price: float
    shares: int
    amount: float
    position_pct: float
    stop_loss_price: float
    stop_loss_pct: float
    risk_amount: float
    currency: str = "$"

    def __str__(self) -> str:
        """Human-readable representation."""
        if self.currency == "$":
            return (
                f"{self.ticker}: {self.shares} shares @ {self.currency}{self.current_price:.2f} "
                f"= {self.currency}{self.amount:,.2f} ({self.position_pct:.1%}) | "
                f"Stop: {self.currency}{self.stop_loss_price:.2f} | "
                f"Risk: {self.currency}{self.risk_amount:,.2f}"
            )
        else:
            # KRW formatting (no decimals, comma separated)
            return (
                f"{self.ticker}: {self.shares} shares @ {self.currency}{self.current_price:,.0f} "
                f"= {self.currency}{self.amount:,.0f} ({self.position_pct:.1%}) | "
                f"Stop: {self.currency}{self.stop_loss_price:,.0f} | "
                f"Risk: {self.currency}{self.risk_amount:,.0f}"
            )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "current_price": self.current_price,
            "shares": self.shares,
            "amount": self.amount,
            "position_pct": self.position_pct,
            "stop_loss_price": self.stop_loss_price,
            "stop_loss_pct": self.stop_loss_pct,
            "risk_amount": self.risk_amount,
            "currency": self.currency,
        }


class PositionSizer:
    """
    Position sizing calculator based on risk management principles.
    위험 관리 기반 포지션 사이징 계산기.

    This class calculates appropriate position sizes by:
    1. Scaling position size inversely with risk score (higher risk = smaller position)
    2. Ensuring position never exceeds max_position_pct of total capital
    3. Limiting maximum risk per trade to max_risk_per_trade_pct

    The algorithm uses a risk-adjusted approach:
    - Base position = (max_risk_per_trade / stop_loss_pct) * risk_multiplier
    - risk_multiplier decreases as risk_score increases

    Attributes:
        total_capital: Total available capital for investing
        max_position_pct: Maximum position size as fraction of capital (default 0.10 = 10%)
        max_risk_per_trade_pct: Maximum risk per trade as fraction of capital (default 0.02 = 2%)
    """

    # Risk score to multiplier mapping (1-10 scale)
    # Higher risk score = lower multiplier = smaller position
    RISK_MULTIPLIERS = {
        1: 1.0,    # Lowest risk: full position allowed
        2: 0.95,
        3: 0.85,
        4: 0.75,
        5: 0.65,   # Medium risk: 65% of max position
        6: 0.55,
        7: 0.45,
        8: 0.35,
        9: 0.25,
        10: 0.15,  # Highest risk: only 15% of max position
    }

    def __init__(
        self,
        total_capital: float,
        max_position_pct: float = 0.10,
        max_risk_per_trade_pct: float = 0.02,
    ):
        """
        Initialize position sizer.

        Args:
            total_capital: Total available capital for investing
            max_position_pct: Maximum position size as fraction of capital (default 0.10 = 10%)
            max_risk_per_trade_pct: Maximum risk per trade as fraction of capital (default 0.02 = 2%)

        Raises:
            ValueError: If total_capital is not positive or percentages are invalid
        """
        if total_capital <= 0:
            raise ValueError("total_capital must be positive")
        if not 0 < max_position_pct <= 1:
            raise ValueError("max_position_pct must be between 0 and 1")
        if not 0 < max_risk_per_trade_pct <= 1:
            raise ValueError("max_risk_per_trade_pct must be between 0 and 1")

        self.total_capital = total_capital
        self.max_position_pct = max_position_pct
        self.max_risk_per_trade_pct = max_risk_per_trade_pct

    def _get_risk_multiplier(self, risk_score: float) -> float:
        """
        Get risk multiplier based on risk score.

        For scores between integers, interpolate linearly.

        Args:
            risk_score: Risk score (1-10, higher = riskier)

        Returns:
            Risk multiplier (0 < multiplier <= 1)
        """
        # Clamp risk score to valid range
        risk_score = max(1, min(10, risk_score))

        # Get integer bounds
        lower = int(math.floor(risk_score))
        upper = int(math.ceil(risk_score))

        if lower == upper:
            return self.RISK_MULTIPLIERS[lower]

        # Linear interpolation
        lower_mult = self.RISK_MULTIPLIERS[lower]
        upper_mult = self.RISK_MULTIPLIERS[upper]
        fraction = risk_score - lower

        return lower_mult + (upper_mult - lower_mult) * fraction

    def calculate(
        self,
        ticker: str,
        current_price: float,
        risk_score: float,
        stop_loss_pct: float = 0.05,
        currency: str = "$",
    ) -> PositionRecommendation:
        """
        Calculate position size based on risk management.

        The calculation follows these steps:
        1. Get risk multiplier based on risk_score
        2. Calculate base position size using risk-based formula
        3. Apply maximum position constraint
        4. Calculate shares (rounded down to whole numbers)
        5. Compute stop loss price and risk amount

        Args:
            ticker: Stock ticker symbol
            current_price: Current stock price
            risk_score: Risk score (1-10, higher = riskier)
            stop_loss_pct: Stop loss percentage (default 0.05 = 5%)
            currency: Currency symbol ($ or won)

        Returns:
            PositionRecommendation with calculated position details

        Raises:
            ValueError: If current_price is not positive or stop_loss_pct is invalid
        """
        if current_price <= 0:
            raise ValueError("current_price must be positive")
        if not 0 < stop_loss_pct < 1:
            raise ValueError("stop_loss_pct must be between 0 and 1")

        # Step 1: Get risk multiplier
        risk_multiplier = self._get_risk_multiplier(risk_score)

        # Step 2: Calculate base position size using risk-based formula
        # Position = (Max Risk / Stop Loss %) * Risk Multiplier
        # This ensures that if stop loss triggers, loss is within max_risk_per_trade_pct
        max_risk_amount = self.total_capital * self.max_risk_per_trade_pct
        base_position_value = (max_risk_amount / stop_loss_pct) * risk_multiplier

        # Step 3: Apply maximum position constraint
        max_position_value = self.total_capital * self.max_position_pct
        position_value = min(base_position_value, max_position_value)

        # Step 4: Calculate shares (round down to whole numbers)
        shares = int(math.floor(position_value / current_price))

        # Ensure at least 0 shares (can't buy negative)
        shares = max(0, shares)

        # Recalculate actual position value based on whole shares
        amount = shares * current_price

        # Step 5: Calculate position percentage
        position_pct = amount / self.total_capital if self.total_capital > 0 else 0

        # Step 6: Calculate stop loss price and risk amount
        stop_loss_price = current_price * (1 - stop_loss_pct)
        risk_amount = shares * current_price * stop_loss_pct

        return PositionRecommendation(
            ticker=ticker,
            current_price=current_price,
            shares=shares,
            amount=amount,
            position_pct=position_pct,
            stop_loss_price=stop_loss_price,
            stop_loss_pct=stop_loss_pct,
            risk_amount=risk_amount,
            currency=currency,
        )

    def calculate_batch(
        self,
        recommendations: List[Tuple[str, float, float]],
        stop_loss_pct: float = 0.05,
        currency: str = "$",
    ) -> List[PositionRecommendation]:
        """
        Calculate position sizes for multiple stocks.

        Args:
            recommendations: List of (ticker, price, risk_score) tuples
            stop_loss_pct: Stop loss percentage to apply to all (default 0.05 = 5%)
            currency: Currency symbol to apply to all ($ or won)

        Returns:
            List of PositionRecommendation objects
        """
        results = []
        for ticker, price, risk_score in recommendations:
            result = self.calculate(
                ticker=ticker,
                current_price=price,
                risk_score=risk_score,
                stop_loss_pct=stop_loss_pct,
                currency=currency,
            )
            results.append(result)
        return results

    def calculate_with_custom_stop_loss(
        self,
        ticker: str,
        current_price: float,
        risk_score: float,
        stop_loss_price: float,
        currency: str = "$",
    ) -> PositionRecommendation:
        """
        Calculate position size with a custom stop loss price.

        This is useful when you have a specific price level (e.g., support level)
        rather than a percentage-based stop loss.

        Args:
            ticker: Stock ticker symbol
            current_price: Current stock price
            risk_score: Risk score (1-10, higher = riskier)
            stop_loss_price: Specific stop loss price
            currency: Currency symbol ($ or won)

        Returns:
            PositionRecommendation with calculated position details

        Raises:
            ValueError: If stop_loss_price >= current_price
        """
        if stop_loss_price >= current_price:
            raise ValueError("stop_loss_price must be less than current_price")

        stop_loss_pct = (current_price - stop_loss_price) / current_price

        return self.calculate(
            ticker=ticker,
            current_price=current_price,
            risk_score=risk_score,
            stop_loss_pct=stop_loss_pct,
            currency=currency,
        )

    def summary(self) -> str:
        """Return a summary of the position sizer configuration."""
        return (
            f"PositionSizer(capital={self.total_capital:,.2f}, "
            f"max_position={self.max_position_pct:.1%}, "
            f"max_risk_per_trade={self.max_risk_per_trade_pct:.1%})"
        )


def create_position_sizer(
    total_capital: float,
    conservative: bool = False,
    aggressive: bool = False,
) -> PositionSizer:
    """
    Factory function to create a PositionSizer with preset configurations.

    Args:
        total_capital: Total available capital for investing
        conservative: Use conservative settings (lower risk limits)
        aggressive: Use aggressive settings (higher risk limits)

    Returns:
        Configured PositionSizer instance
    """
    if conservative and aggressive:
        raise ValueError("Cannot use both conservative and aggressive modes")

    if conservative:
        return PositionSizer(
            total_capital=total_capital,
            max_position_pct=0.05,  # 5% max per position
            max_risk_per_trade_pct=0.01,  # 1% max risk per trade
        )
    elif aggressive:
        return PositionSizer(
            total_capital=total_capital,
            max_position_pct=0.20,  # 20% max per position
            max_risk_per_trade_pct=0.03,  # 3% max risk per trade
        )
    else:
        return PositionSizer(
            total_capital=total_capital,
            max_position_pct=0.10,  # 10% max per position (default)
            max_risk_per_trade_pct=0.02,  # 2% max risk per trade (default)
        )
