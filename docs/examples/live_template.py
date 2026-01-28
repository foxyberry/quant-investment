"""
Live Trading/Bot Strategy Template

Copy this file to scripts/live/ and customize it with your own logic.
The run() function is the entry point that will be called by the orchestrator.
"""

from portfolio import Portfolio, OrderExecutor, Order
from portfolio.monitor import PriceMonitor
from portfolio.trigger import ConditionChecker
from portfolio.risk import RiskManager, MaxPositionRule, DailyLossLimitRule
from news import NewsAggregator
import logging
import time

# Setup logging for this strategy
logger = logging.getLogger(__name__)


def run():
    """
    Main live trading/bot logic - customize this function

    Returns:
        dict with execution summary
    """
    logger.info("Starting live trading bot...")

    # ===== STEP 1: Initialize Portfolio =====
    portfolio = Portfolio()

    # Load existing holdings or add new ones
    # portfolio.add("AAPL", quantity=10, avg_price=150.0)

    # ===== STEP 2: Initialize Order Executor =====
    # dry_run=True for paper trading, False for live
    executor = OrderExecutor(
        dry_run=True,
        initial_balance=100000
    )

    # ===== STEP 3: Setup Risk Management =====
    risk_manager = RiskManager()
    risk_manager.add_rule(MaxPositionRule(max_pct=0.2))  # Max 20% per position
    risk_manager.add_rule(DailyLossLimitRule(max_loss_pct=0.05))  # Max 5% daily loss

    # ===== STEP 4: Define Symbols to Monitor =====
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

    # ===== STEP 5: Setup Condition Checker =====
    checker = ConditionChecker()

    # Add conditions for each symbol
    for symbol in symbols:
        # Example: Alert when price drops 5%
        checker.add_condition(
            ticker=symbol,
            condition_type='PRICE_BELOW',
            target=0.95,  # 95% of current price
            cooldown_minutes=60
        )

    # ===== STEP 6: Setup Callbacks =====
    def on_trigger(event):
        logger.info(f"TRIGGERED: {event.ticker} - {event.condition_type}")
        # Add your trading logic here
        # Example: Create sell order
        # order = Order(event.ticker, "SELL", quantity=5)
        # executor.execute(order)

    checker.on_triggered(on_trigger)

    # ===== STEP 7: Optional - News Monitoring =====
    try:
        news_aggregator = NewsAggregator()
        for symbol in symbols[:2]:  # Check news for first 2 symbols
            sentiment = news_aggregator.get_sentiment(symbol)
            if sentiment:
                logger.info(f"{symbol} sentiment: {sentiment.overall_sentiment.value}")
    except Exception as e:
        logger.warning(f"News check failed: {e}")

    # ===== STEP 8: Main Loop (for continuous monitoring) =====
    # Uncomment for continuous operation
    """
    monitor = PriceMonitor(interval=60)  # Check every 60 seconds

    for symbol in symbols:
        monitor.add(symbol)

    def on_price_update(prices):
        checker.check(prices)

    monitor.on_update(on_price_update)
    monitor.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        logger.info("Bot stopped")
    """

    # ===== STEP 9: One-time Check (for cron jobs) =====
    logger.info("Running one-time check...")

    # Get current prices and check conditions
    from utils.fetch import get_current_prices

    try:
        prices = get_current_prices(symbols)
        triggered = checker.check(prices)

        for event in triggered:
            logger.info(f"Signal: {event.ticker} - {event.condition_type}")

    except Exception as e:
        logger.error(f"Price check failed: {e}")

    # ===== STEP 10: Return Summary =====
    return {
        'symbols_monitored': len(symbols),
        'portfolio_value': portfolio.total_value() if hasattr(portfolio, 'total_value') else 0,
        'executor_balance': executor.balance if hasattr(executor, 'balance') else 0,
        'status': 'completed'
    }


# ===== HELPER FUNCTIONS (Optional) =====
def check_sell_signals(portfolio: Portfolio) -> list:
    """
    Check for sell signals on portfolio holdings
    """
    signals = []
    # Add your sell signal logic here
    return signals


def check_buy_signals(watchlist: list) -> list:
    """
    Check for buy signals on watchlist
    """
    signals = []
    # Add your buy signal logic here
    return signals


# ===== STANDALONE EXECUTION =====
if __name__ == "__main__":
    result = run()

    print(f"\nBot execution completed")
    print(f"  Symbols monitored: {result.get('symbols_monitored', 0)}")
    print(f"  Status: {result.get('status', 'unknown')}")
