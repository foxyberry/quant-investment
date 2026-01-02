"""
Momentum Strategy Backtest

This strategy backtests a momentum-based approach on high-volume stocks
with specific entry and exit criteria.
"""

from strategies.backtrader_engine import BacktraderEngine
from strategies.backtrader_strategy import BottomBreakoutStrategy
from screener.basic_filter import BasicInfoScreener
from screener.screening_criteria import ScreeningCriteria
from datetime import datetime, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def run():
    """
    Backtest momentum strategy on selected high-momentum stocks
    """
    logger.info("Starting Momentum Strategy Backtest...")
    
    # Get high-momentum stock candidates
    symbols = get_momentum_stocks()
    logger.info(f"Selected {len(symbols)} momentum candidates")
    
    # Define backtest period (last 6 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    logger.info(f"Backtest period: {start_date.date()} to {end_date.date()}")
    
    # Initialize backtest engine
    engine = BacktraderEngine(
        initial_cash=100000,
        commission=0.001  # 0.1% commission
    )
    
    # Define momentum strategy parameters
    strategy_params = {
        'lookback_days': 10,          # Shorter lookback for momentum
        'breakout_threshold': 1.03,   # 3% breakout threshold
        'stop_loss_threshold': 0.97,  # Tight 3% stop loss
        'take_profit_threshold': 1.08, # 8% profit target
        'position_size': 0.25,         # 25% position size
        'volume_threshold': 1.8,       # High volume requirement
        'timeout_days': 7,             # Shorter holding period
        'debug': False,
        'verbose_logging': False
    }
    
    # Run backtests on all symbols
    logger.info("Running backtests...")
    results = engine.batch_backtest(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        strategy_class=BottomBreakoutStrategy,
        strategy_params=strategy_params
    )
    
    # Analyze results
    analyze_and_report(results)
    
    return results


def get_momentum_stocks():
    """
    Select stocks showing strong momentum characteristics
    Focus on liquid stocks with strong recent performance
    """
    screener = BasicInfoScreener()
    stocks = screener.get_snp500_basic_info()
    
    # Criteria for momentum stocks
    criteria = ScreeningCriteria(
        min_price=50,               # Higher priced stocks
        max_price=500,              # Not too expensive
        min_volume=5_000_000,       # Very liquid
        min_market_cap=100_000_000_000,  # Mega caps ($100B+)
        sectors=['Technology', 'Consumer Cyclical', 'Communication Services']
    )
    
    filtered = screener.apply_basic_filters(stocks, criteria)
    
    # Select top stocks by market cap (momentum often in large caps)
    top_stocks = filtered.nlargest(15, 'market_cap')
    
    return top_stocks['symbol'].tolist()


def analyze_and_report(results):
    """
    Analyze backtest results and generate detailed report
    """
    if not results:
        logger.warning("No backtest results to analyze")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Filter valid results
    valid = df[df['total_return_pct'].notna()].copy()
    
    if valid.empty:
        logger.warning("No valid results found")
        return
    
    # Calculate statistics
    total_trades = valid['num_trades'].sum()
    avg_return = valid['total_return_pct'].mean()
    median_return = valid['total_return_pct'].median()
    best_performer = valid.loc[valid['total_return_pct'].idxmax()]
    worst_performer = valid.loc[valid['total_return_pct'].idxmin()]
    
    winners = valid[valid['total_return_pct'] > 0]
    win_rate = (len(winners) / len(valid)) * 100
    
    # Report
    logger.info("\n" + "=" * 70)
    logger.info("MOMENTUM STRATEGY BACKTEST RESULTS")
    logger.info("=" * 70)
    logger.info(f"Symbols tested: {len(valid)}")
    logger.info(f"Total trades executed: {total_trades}")
    logger.info(f"Win rate: {win_rate:.1f}% ({len(winners)}/{len(valid)})")
    logger.info(f"Average return: {avg_return:.2f}%")
    logger.info(f"Median return: {median_return:.2f}%")
    
    logger.info(f"\nBest performer: {best_performer['symbol']}")
    logger.info(f"  Return: {best_performer['total_return_pct']:.2f}%")
    logger.info(f"  Trades: {best_performer['num_trades']}")
    logger.info(f"  Max Drawdown: {best_performer.get('max_drawdown_pct', 0):.1f}%")
    
    logger.info(f"\nWorst performer: {worst_performer['symbol']}")
    logger.info(f"  Return: {worst_performer['total_return_pct']:.2f}%")
    logger.info(f"  Trades: {worst_performer['num_trades']}")
    
    # Performance breakdown
    logger.info("\n" + "-" * 40)
    logger.info("INDIVIDUAL SYMBOL PERFORMANCE")
    logger.info("-" * 40)
    
    valid_sorted = valid.sort_values('total_return_pct', ascending=False)
    for _, row in valid_sorted.iterrows():
        status = "✅" if row['total_return_pct'] > 0 else "❌"
        logger.info(
            f"{status} {row['symbol']:6s}: {row['total_return_pct']:+7.2f}% | "
            f"Trades: {row['num_trades']:2d} | "
            f"Max DD: {row.get('max_drawdown_pct', 0):5.1f}%"
        )
    
    # Summary statistics
    if len(valid) > 1:
        profitable = valid[valid['total_return_pct'] > 5]  # >5% return
        if len(profitable) > 0:
            logger.info(f"\n{len(profitable)} symbols achieved >5% return")


if __name__ == "__main__":
    results = run()
    if results:
        print(f"\nBacktest complete: {len(results)} symbols tested")