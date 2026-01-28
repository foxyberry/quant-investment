#!/usr/bin/env python3
"""
Backtest Runner
백테스트 실행 스크립트

Usage:
    python scripts/backtesting/run_backtest.py --ticker 005930.KS --period 1y
    python scripts/backtesting/run_backtest.py --ticker AAPL --strategy sma --n1 10 --n2 30
    python scripts/backtesting/run_backtest.py --ticker 005930.KS --optimize
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine import BacktestEngine, calculate_metrics
from engine.strategies import SmaCross, EmaCross
from engine.strategies.ma_cross import MaTouchStrategy


STRATEGIES = {
    'sma': SmaCross,
    'ema': EmaCross,
    'ma_touch': MaTouchStrategy,
}


def main():
    parser = argparse.ArgumentParser(description="Run backtest on a stock")
    parser.add_argument('--ticker', '-t', required=True, help="Stock ticker (e.g., 005930.KS, AAPL)")
    parser.add_argument('--period', '-p', default='1y', help="Data period (e.g., 1y, 6mo, 3mo)")
    parser.add_argument('--strategy', '-s', default='sma', choices=STRATEGIES.keys(), help="Strategy to use")
    parser.add_argument('--cash', '-c', type=float, default=10_000_000, help="Initial cash")
    parser.add_argument('--n1', type=int, default=10, help="Short MA period")
    parser.add_argument('--n2', type=int, default=20, help="Long MA period")
    parser.add_argument('--optimize', '-o', action='store_true', help="Run parameter optimization")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")

    args = parser.parse_args()

    print()
    print("=" * 60)
    print(f"BACKTEST: {args.ticker}")
    print(f"Strategy: {args.strategy.upper()}")
    print(f"Period: {args.period}")
    print(f"Initial Cash: {args.cash:,.0f}")
    print("=" * 60)
    print()

    # Create engine
    engine = BacktestEngine(commission=0.001)  # 0.1% commission

    # Get strategy class
    strategy_class = STRATEGIES[args.strategy]

    try:
        if args.optimize:
            print("Running parameter optimization...")
            print("This may take a while...")
            print()

            result = engine.optimize(
                strategy=strategy_class,
                ticker=args.ticker,
                period=args.period,
                cash=args.cash,
                maximize='Sharpe Ratio',
                n1=range(5, 30, 5),
                n2=range(10, 60, 10),
            )

            print(f"Optimal n1: {result.stats._strategy.n1}")
            print(f"Optimal n2: {result.stats._strategy.n2}")
            print()

        else:
            # Run backtest with specified parameters
            result = engine.run(
                strategy=strategy_class,
                ticker=args.ticker,
                period=args.period,
                cash=args.cash,
                n1=args.n1,
                n2=args.n2,
            )

        # Print basic results
        print(result.summary())
        print()

        # Calculate and print detailed metrics
        metrics = calculate_metrics(result)
        print(metrics.summary())

        # Print trades if verbose
        if args.verbose and not result.trades.empty:
            print()
            print("TRADES:")
            print("-" * 60)
            print(result.trades.to_string())

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
