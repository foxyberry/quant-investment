"""
Portfolio Service.

Business logic for portfolio management operations.
Provides CRUD operations for holdings and P&L calculations.
"""

import json
import logging
import threading
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

from api.schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioSummary,
    SellSignal,
)

# Import data cache for current price retrieval
from utils.data_cache import OHLCVCache, get_cache

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Portfolio service for managing holdings.

    Provides methods for CRUD operations on holdings,
    P&L calculations, and sell signal detection.
    """

    DEFAULT_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "portfolio.json"

    # Default sell signal thresholds
    STOP_LOSS_PCT = -10.0  # -10% triggers stop loss
    TAKE_PROFIT_PCT = 20.0  # +20% triggers take profit

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize the portfolio service.

        Args:
            data_path: Path to portfolio JSON file (default: data/portfolio.json)
        """
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self._lock = threading.Lock()
        self._cache = get_cache()
        self._holdings: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load portfolio data from JSON file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    holdings_list = data.get("holdings", [])
                    self._holdings = {h["ticker"]: h for h in holdings_list}
                    logger.info(f"Loaded {len(self._holdings)} holdings from {self.data_path}")
            except Exception as e:
                logger.warning(f"Failed to load portfolio data: {e}")
                self._holdings = {}
        else:
            # Create initial data file
            self._save()

    def _save(self) -> None:
        """Save portfolio data to JSON file."""
        with self._lock:
            try:
                self.data_path.parent.mkdir(parents=True, exist_ok=True)

                data = {
                    "holdings": list(self._holdings.values()),
                    "updated_at": datetime.now().isoformat()
                }

                with open(self.data_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)

                logger.debug(f"Saved portfolio data to {self.data_path}")
            except Exception as e:
                logger.error(f"Failed to save portfolio data: {e}")
                raise

    def _get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None if unavailable
        """
        try:
            data = self._cache.get(ticker, days=5, force_refresh=False)
            if data is not None and not data.empty:
                return float(data["close"].iloc[-1])
        except Exception as e:
            logger.warning(f"Failed to get current price for {ticker}: {e}")
        return None

    def _get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to current price
        """
        prices = {}
        for ticker in tickers:
            price = self._get_current_price(ticker)
            if price is not None:
                prices[ticker] = price
        return prices

    def _holding_to_response(
        self,
        holding: Dict[str, Any],
        current_price: Optional[float] = None
    ) -> HoldingResponse:
        """
        Convert holding dict to HoldingResponse with P&L.

        Args:
            holding: Holding data dict
            current_price: Current market price (optional)

        Returns:
            HoldingResponse with calculated fields
        """
        quantity = holding.get("quantity", 0)
        avg_price = holding.get("avg_price", 0)
        cost_basis = quantity * avg_price

        market_value = None
        pnl = None
        pnl_pct = None

        if current_price is not None:
            market_value = quantity * current_price
            pnl = market_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

        # Parse bought_at date
        bought_at = holding.get("bought_at")
        if isinstance(bought_at, str):
            try:
                bought_at = date.fromisoformat(bought_at)
            except ValueError:
                bought_at = None

        return HoldingResponse(
            ticker=holding.get("ticker", ""),
            name=holding.get("name"),
            quantity=quantity,
            avg_price=avg_price,
            current_price=current_price,
            market_value=market_value,
            cost_basis=cost_basis,
            pnl=pnl,
            pnl_pct=pnl_pct,
            currency=holding.get("currency", "KRW"),
            bought_at=bought_at,
            note=holding.get("note")
        )

    def get_all_holdings(self, with_prices: bool = True) -> List[HoldingResponse]:
        """
        Get all holdings with optional current prices.

        Args:
            with_prices: Whether to fetch current prices

        Returns:
            List of HoldingResponse objects
        """
        holdings = []
        prices = {}

        if with_prices:
            tickers = list(self._holdings.keys())
            prices = self._get_current_prices(tickers)

        for ticker, holding in self._holdings.items():
            current_price = prices.get(ticker)
            holdings.append(self._holding_to_response(holding, current_price))

        return holdings

    def get_holding(self, ticker: str, with_price: bool = True) -> Optional[HoldingResponse]:
        """
        Get a single holding by ticker.

        Args:
            ticker: Stock ticker symbol
            with_price: Whether to fetch current price

        Returns:
            HoldingResponse or None if not found
        """
        holding = self._holdings.get(ticker)
        if not holding:
            return None

        current_price = None
        if with_price:
            current_price = self._get_current_price(ticker)

        return self._holding_to_response(holding, current_price)

    def add_holding(self, data: HoldingCreate) -> HoldingResponse:
        """
        Add a new holding or add to existing position.

        If the ticker already exists, calculates new average price.

        Args:
            data: HoldingCreate schema with holding details

        Returns:
            Created/updated HoldingResponse
        """
        ticker = data.ticker
        existing = self._holdings.get(ticker)

        if existing:
            # Add to existing position - calculate new average price
            old_quantity = existing.get("quantity", 0)
            old_avg_price = existing.get("avg_price", 0)
            old_cost = old_quantity * old_avg_price

            new_cost = data.quantity * data.avg_price
            total_quantity = old_quantity + data.quantity
            new_avg_price = (old_cost + new_cost) / total_quantity if total_quantity > 0 else 0

            existing["quantity"] = total_quantity
            existing["avg_price"] = new_avg_price
            if data.name:
                existing["name"] = data.name
            if data.note:
                existing["note"] = data.note
            existing["currency"] = data.currency

            logger.info(f"Updated holding: {ticker} (qty: {total_quantity}, avg: {new_avg_price:.2f})")
        else:
            # Create new holding
            self._holdings[ticker] = {
                "ticker": ticker,
                "name": data.name or ticker,
                "quantity": data.quantity,
                "avg_price": data.avg_price,
                "currency": data.currency,
                "note": data.note,
                "bought_at": date.today().isoformat(),
            }
            logger.info(f"Added holding: {ticker} (qty: {data.quantity}, avg: {data.avg_price:.2f})")

        self._save()

        current_price = self._get_current_price(ticker)
        return self._holding_to_response(self._holdings[ticker], current_price)

    def update_holding(self, ticker: str, data: HoldingUpdate) -> Optional[HoldingResponse]:
        """
        Update an existing holding.

        Args:
            ticker: Stock ticker symbol
            data: HoldingUpdate schema with fields to update

        Returns:
            Updated HoldingResponse or None if not found
        """
        holding = self._holdings.get(ticker)
        if not holding:
            return None

        if data.quantity is not None:
            holding["quantity"] = data.quantity
        if data.avg_price is not None:
            holding["avg_price"] = data.avg_price
        if data.name is not None:
            holding["name"] = data.name
        if data.note is not None:
            holding["note"] = data.note

        self._save()
        logger.info(f"Updated holding: {ticker}")

        current_price = self._get_current_price(ticker)
        return self._holding_to_response(holding, current_price)

    def remove_holding(self, ticker: str) -> bool:
        """
        Remove a holding.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if removed, False if not found
        """
        if ticker in self._holdings:
            del self._holdings[ticker]
            self._save()
            logger.info(f"Removed holding: {ticker}")
            return True
        return False

    def get_summary(self) -> PortfolioSummary:
        """
        Get portfolio summary with total P&L.

        Returns:
            PortfolioSummary with aggregated metrics
        """
        holdings = self.get_all_holdings(with_prices=True)

        total_investment = 0.0
        total_market_value = 0.0

        for h in holdings:
            total_investment += h.cost_basis
            if h.market_value is not None:
                total_market_value += h.market_value
            else:
                # Use cost basis if market value unavailable
                total_market_value += h.cost_basis

        total_pnl = total_market_value - total_investment
        total_pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0

        # Determine primary currency (most common)
        currencies = [h.currency for h in holdings]
        primary_currency = max(set(currencies), key=currencies.count) if currencies else "KRW"

        return PortfolioSummary(
            total_investment=total_investment,
            total_market_value=total_market_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            holdings_count=len(holdings),
            currency=primary_currency,
            last_updated=datetime.now()
        )

    def get_sell_signals(
        self,
        stop_loss_pct: float = None,
        take_profit_pct: float = None
    ) -> List[SellSignal]:
        """
        Get sell signals based on P&L thresholds.

        Args:
            stop_loss_pct: Stop loss threshold percentage (default: -10%)
            take_profit_pct: Take profit threshold percentage (default: +20%)

        Returns:
            List of SellSignal objects
        """
        stop_loss = stop_loss_pct if stop_loss_pct is not None else self.STOP_LOSS_PCT
        take_profit = take_profit_pct if take_profit_pct is not None else self.TAKE_PROFIT_PCT

        signals = []
        holdings = self.get_all_holdings(with_prices=True)

        for h in holdings:
            if h.pnl_pct is None or h.current_price is None:
                continue

            signal = None

            # Check stop loss
            if h.pnl_pct <= stop_loss:
                signal = SellSignal(
                    ticker=h.ticker,
                    name=h.name or h.ticker,
                    signal_type="stop_loss",
                    reason=f"Loss exceeded {stop_loss}% threshold (current: {h.pnl_pct:.1f}%)",
                    current_price=h.current_price,
                    trigger_price=h.avg_price * (1 + stop_loss / 100),
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct
                )

            # Check take profit
            elif h.pnl_pct >= take_profit:
                signal = SellSignal(
                    ticker=h.ticker,
                    name=h.name or h.ticker,
                    signal_type="take_profit",
                    reason=f"Profit reached {take_profit}% target (current: {h.pnl_pct:.1f}%)",
                    current_price=h.current_price,
                    trigger_price=h.avg_price * (1 + take_profit / 100),
                    avg_price=h.avg_price,
                    pnl_pct=h.pnl_pct
                )

            if signal:
                signals.append(signal)

        return signals


# Singleton instance
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """
    Get or create the portfolio service singleton.

    Returns:
        PortfolioService instance
    """
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service
