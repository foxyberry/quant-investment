"""
Technology Sector Breakout Screening Strategy

This strategy screens for technology stocks showing breakout patterns
with strong volume confirmation.
"""

from screener.basic_filter import BasicInfoScreener
from screener.technical_filter import TechnicalScreener
from screener.screening_criteria import ScreeningCriteria
from screener.technical_criteria import TechnicalCriteria
import logging

logger = logging.getLogger(__name__)


def run():
    """
    Screen for technology stocks with fresh breakout patterns
    """
    logger.info("Running Technology Breakout Screening...")
    
    # Initialize screeners
    basic_screener = BasicInfoScreener()
    technical_screener = TechnicalScreener()
    
    # Get S&P 500 universe
    stocks = basic_screener.get_snp500_basic_info()
    logger.info(f"Starting universe: {len(stocks)} S&P 500 stocks")
    
    # Define criteria for tech stocks with good liquidity
    basic_criteria = ScreeningCriteria(
        min_price=20.0,              # Above $20 to avoid penny stocks
        max_price=1000.0,            # Below $1000 
        min_volume=2_000_000,        # At least 2M daily volume
        min_market_cap=50_000_000_000,  # Large cap: $50B+
        sectors=['Technology']        # Technology sector only
    )
    
    # Apply basic filters
    filtered_stocks = basic_screener.apply_basic_filters(stocks, basic_criteria)
    logger.info(f"Technology large-caps: {len(filtered_stocks)} stocks")
    
    # Define technical criteria for breakout detection
    technical_criteria = TechnicalCriteria(
        lookback_days=20,           # 20-day lookback for bottom
        volume_threshold=2.0,        # Volume must be 2x average
        breakout_threshold=1.05,     # 5% above 20-day bottom
        stop_loss_threshold=0.97     # 3% stop loss
    )
    
    # Get symbols for technical analysis
    symbols = filtered_stocks['symbol'].tolist()
    
    # Run technical analysis
    logger.info(f"Analyzing {len(symbols)} technology stocks for breakout patterns...")
    technical_results = technical_screener.batch_technical_analysis(
        symbols, 
        technical_criteria
    )
    
    # Filter for fresh breakouts only
    fresh_breakouts = technical_screener.filter_by_fresh_breakout(technical_results)
    
    # Merge with fundamental data
    final_results = technical_screener.merge_results(technical_results, filtered_stocks)
    
    # Log results
    logger.info(f"Found {len(fresh_breakouts)} fresh breakouts in technology sector")
    
    if fresh_breakouts:
        logger.info("\n=== TOP TECHNOLOGY BREAKOUTS ===")
        for i, stock in enumerate(fresh_breakouts[:10], 1):
            logger.info(
                f"{i}. {stock['symbol']:6s} | "
                f"Price: ${stock['current_price']:.2f} | "
                f"Volume Ratio: {stock.get('volume_ratio', 0):.1f}x | "
                f"Above Bottom: {stock.get('above_bottom_pct', 0):.1f}%"
            )
    
    return final_results


if __name__ == "__main__":
    results = run()
    print(f"\nScreening complete: {len(results)} stocks analyzed")