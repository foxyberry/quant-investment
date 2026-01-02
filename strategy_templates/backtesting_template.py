"""
Backtesting Strategy Template

Copy this file to my_strategies/backtesting/ and customize it with your own parameters.
The run() function is the entry point that will be called by the orchestrator.
"""

from strategies.backtrader_engine import BacktraderEngine
from strategies.backtrader_strategy import BottomBreakoutStrategy, SimpleBuyHoldStrategy
from screener.basic_filter import BasicInfoScreener
from screener.screening_criteria import ScreeningCriteria
from datetime import datetime, timedelta
import pandas as pd
import logging

# Setup logging for this strategy
logger = logging.getLogger(__name__)


def run():
    """
    Main backtesting logic - customize this function with your parameters
    
    Returns:
        List of backtest results or DataFrame
    """
    logger.info("Starting custom backtesting strategy...")
    
    # ===== STEP 1: Define Symbols to Test =====
    # Option 1: Manually specify symbols
    # symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    
    # Option 2: Get symbols from screening
    symbols = get_symbols_from_screening()
    
    logger.info(f"Testing {len(symbols)} symbols")
    
    # ===== STEP 2: Define Date Range =====
    # Option 1: Fixed dates
    # start_date = datetime(2023, 1, 1)
    # end_date = datetime(2024, 1, 1)
    
    # Option 2: Relative to today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Last 1 year
    
    logger.info(f"Backtest period: {start_date.date()} to {end_date.date()}")
    
    # ===== STEP 3: Initialize Backtest Engine =====
    engine = BacktraderEngine(
        initial_cash=100000,  # Starting capital
        commission=0.001      # Commission rate (0.1%)
    )
    
    # ===== STEP 4: Define Strategy Parameters =====
    # Customize these based on your strategy
    strategy_params = {
        'lookback_days': 20,          # Days to look back for patterns
        'breakout_threshold': 1.05,   # 5% above bottom for breakout
        'stop_loss_threshold': 0.95,  # 5% below bottom for stop loss
        'take_profit_threshold': 1.10, # 10% profit target
        'position_size': 0.2,          # Use 20% of capital per position
        'volume_threshold': 1.5,       # Volume must be 1.5x average
        'timeout_days': 10,            # Exit after 10 days if profitable
        'debug': False,                # Set True for detailed logging
        'verbose_logging': False       # Set True for trade-by-trade logs
    }
    
    # ===== STEP 5: Run Backtests =====
    # Option 1: Batch backtest with same strategy
    results = engine.batch_backtest(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        strategy_class=BottomBreakoutStrategy,
        strategy_params=strategy_params
    )
    
    # Option 2: Compare multiple strategies (uncomment to use)
    # results = compare_strategies(engine, symbols[0], start_date, end_date)
    
    # ===== STEP 6: Process and Analyze Results =====
    results = analyze_results(results)
    
    # ===== STEP 7: Generate Summary Report =====
    generate_summary_report(results)
    
    return results


def get_symbols_from_screening():
    """
    Get symbols using screening criteria
    Customize this to match your universe selection
    """
    screener = BasicInfoScreener()
    stocks = screener.get_snp500_basic_info()
    
    # Apply your criteria
    criteria = ScreeningCriteria(
        min_price=20,
        max_price=500,
        min_volume=2_000_000,
        min_market_cap=20_000_000_000,  # $20B+ large caps
        sectors=['Technology']  # Focus on tech sector
    )
    
    filtered = screener.apply_basic_filters(stocks, criteria)
    
    # Get top N by market cap
    filtered = filtered.nlargest(10, 'market_cap')
    
    return filtered['symbol'].tolist()


def compare_strategies(engine, symbol, start_date, end_date):
    """
    Compare multiple strategies on the same symbol
    """
    strategies = [
        (BottomBreakoutStrategy, {
            'lookback_days': 20,
            'breakout_threshold': 1.05,
            'stop_loss_threshold': 0.95,
            'position_size': 0.2
        }),
        (SimpleBuyHoldStrategy, {}),
        # Add more strategies here
    ]
    
    results = engine.compare_strategies(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        strategies=strategies
    )
    
    return results


def analyze_results(results):
    """
    Analyze and enhance backtest results
    """
    if not results:
        return results
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(results)
    
    # Filter out errors
    df = df[~df['symbol'].isna()]
    df = df[df['total_return_pct'].notna()]
    
    # Add additional metrics
    if not df.empty:
        # Calculate win rate
        df['is_winner'] = df['total_return_pct'] > 0
        
        # Add risk-adjusted returns (simplified Sharpe-like metric)
        if 'max_drawdown_pct' in df.columns:
            df['risk_adjusted_return'] = df['total_return_pct'] / (df['max_drawdown_pct'] + 1)
        
        # Sort by total return
        df = df.sort_values('total_return_pct', ascending=False)
    
    return df.to_dict('records') if not df.empty else results


def generate_summary_report(results):
    """
    Generate a summary report of backtest results
    """
    if not results:
        logger.warning("No results to report")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(results)
    
    # Filter valid results
    valid_results = df[df['total_return_pct'].notna()]
    
    if valid_results.empty:
        logger.warning("No valid backtest results")
        return
    
    # Calculate summary statistics
    total_symbols = len(valid_results)
    winners = len(valid_results[valid_results['total_return_pct'] > 0])
    losers = total_symbols - winners
    win_rate = (winners / total_symbols) * 100 if total_symbols > 0 else 0
    
    avg_return = valid_results['total_return_pct'].mean()
    best_return = valid_results['total_return_pct'].max()
    worst_return = valid_results['total_return_pct'].min()
    
    best_symbol = valid_results.loc[valid_results['total_return_pct'].idxmax(), 'symbol']
    worst_symbol = valid_results.loc[valid_results['total_return_pct'].idxmin(), 'symbol']
    
    # Print summary
    logger.info("=" * 60)
    logger.info("BACKTEST SUMMARY REPORT")
    logger.info("=" * 60)
    logger.info(f"Total symbols tested: {total_symbols}")
    logger.info(f"Winners: {winners} | Losers: {losers} | Win Rate: {win_rate:.1f}%")
    logger.info(f"Average return: {avg_return:.2f}%")
    logger.info(f"Best performer: {best_symbol} ({best_return:.2f}%)")
    logger.info(f"Worst performer: {worst_symbol} ({worst_return:.2f}%)")
    
    # Show top 5 performers
    logger.info("\nTop 5 Performers:")
    for _, row in valid_results.head(5).iterrows():
        logger.info(f"  {row['symbol']:6s}: {row['total_return_pct']:+7.2f}% "
                   f"(Trades: {row.get('num_trades', 0)}, "
                   f"Max DD: {row.get('max_drawdown_pct', 0):.1f}%)")
    
    # Show bottom 5 performers
    if len(valid_results) > 5:
        logger.info("\nBottom 5 Performers:")
        for _, row in valid_results.tail(5).iterrows():
            logger.info(f"  {row['symbol']:6s}: {row['total_return_pct']:+7.2f}% "
                       f"(Trades: {row.get('num_trades', 0)}, "
                       f"Max DD: {row.get('max_drawdown_pct', 0):.1f}%)")


# ===== STANDALONE EXECUTION =====
if __name__ == "__main__":
    # This allows the strategy to be run directly
    results = run()
    
    if results:
        print(f"\nBacktest completed for {len(results)} symbols")
        df = pd.DataFrame(results)
        if not df.empty and 'total_return_pct' in df.columns:
            print(f"Average return: {df['total_return_pct'].mean():.2f}%")
    else:
        print("No backtest results generated")