"""
Backtesting Strategy Template

Copy this file to scripts/backtesting/ and customize it with your own strategy.
The run() function is the entry point that will be called by the orchestrator.
"""

from engine.backtesting_engine import BacktestingEngine
from engine.strategies.ma_cross import SmaCross, EmaCross
from datetime import datetime, timedelta
import logging

# Setup logging for this strategy
logger = logging.getLogger(__name__)


def run():
    """
    Main backtesting logic - customize this function with your strategy

    Returns:
        dict or list of backtest results
    """
    logger.info("Starting custom backtesting strategy...")

    # ===== STEP 1: Define Symbols to Test =====
    symbols = ['AAPL', 'MSFT', 'GOOGL']

    # ===== STEP 2: Initialize Backtest Engine =====
    engine = BacktestingEngine(
        initial_cash=100000,
        commission=0.001
    )

    # ===== STEP 3: Define Strategy Parameters =====
    # For SMA/EMA crossover strategies
    strategy_params = {
        'n1': 10,  # Short MA period
        'n2': 20,  # Long MA period
    }

    # ===== STEP 4: Set Date Range =====
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 1 year backtest

    # ===== STEP 5: Run Backtest =====
    results = []

    for symbol in symbols:
        logger.info(f"Backtesting {symbol}...")

        try:
            result = engine.run(
                ticker=symbol,
                strategy_class=SmaCross,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                **strategy_params
            )

            if result:
                results.append({
                    'symbol': symbol,
                    **result
                })
                logger.info(f"  {symbol}: Return={result.get('return_pct', 0):.2f}%")

        except Exception as e:
            logger.error(f"  {symbol}: Error - {e}")
            results.append({
                'symbol': symbol,
                'error': str(e)
            })

    # ===== STEP 6: Summarize Results =====
    successful = [r for r in results if 'error' not in r]
    if successful:
        avg_return = sum(r.get('return_pct', 0) for r in successful) / len(successful)
        logger.info(f"Average return: {avg_return:.2f}%")

    return results


# ===== HELPER FUNCTIONS (Optional) =====
def optimize_parameters(symbol: str, param_ranges: dict):
    """
    Run parameter optimization for a strategy

    Example:
        param_ranges = {
            'n1': range(5, 20, 5),
            'n2': range(20, 50, 10)
        }
    """
    engine = BacktestingEngine()
    # Add optimization logic here
    pass


def compare_strategies(symbol: str, strategies: list):
    """
    Compare multiple strategies on the same symbol
    """
    results = {}
    engine = BacktestingEngine()

    for strategy_class in strategies:
        result = engine.run(ticker=symbol, strategy_class=strategy_class)
        results[strategy_class.__name__] = result

    return results


# ===== STANDALONE EXECUTION =====
if __name__ == "__main__":
    results = run()

    print(f"\nBacktested {len(results)} symbols")
    for r in results:
        if 'error' not in r:
            print(f"  {r['symbol']}: {r.get('return_pct', 0):.2f}%")
        else:
            print(f"  {r['symbol']}: ERROR - {r['error']}")
