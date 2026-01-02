"""
Screening Strategy Template

Copy this file to my_strategies/screening/ and customize it with your own criteria.
The run() function is the entry point that will be called by the orchestrator.
"""

from screener.basic_filter import BasicInfoScreener
from screener.technical_filter import TechnicalScreener
from screener.screening_criteria import ScreeningCriteria
from screener.technical_criteria import TechnicalCriteria
import pandas as pd
import logging

# Setup logging for this strategy
logger = logging.getLogger(__name__)


def run():
    """
    Main screening logic - customize this function with your criteria
    
    Returns:
        DataFrame or list of results
    """
    logger.info("Starting custom screening strategy...")
    
    # ===== STEP 1: Initialize Screeners =====
    basic_screener = BasicInfoScreener()
    technical_screener = TechnicalScreener()
    
    # ===== STEP 2: Get Base Universe =====
    # You can start with S&P 500 stocks or load your own universe
    stocks = basic_screener.get_snp500_basic_info()
    logger.info(f"Starting universe: {len(stocks)} stocks")
    
    # ===== STEP 3: Define Your Basic Criteria =====
    # Customize these values based on your strategy
    basic_criteria = ScreeningCriteria(
        min_price=10.0,              # Minimum stock price
        max_price=500.0,             # Maximum stock price
        min_volume=1_000_000,        # Minimum daily volume
        min_market_cap=10_000_000_000,  # Minimum market cap ($10B)
        sectors=['Technology', 'Healthcare', 'Financial Services']  # Sectors to include
    )
    
    # ===== STEP 4: Apply Basic Filters =====
    filtered_stocks = basic_screener.apply_basic_filters(stocks, basic_criteria)
    logger.info(f"After basic filtering: {len(filtered_stocks)} stocks")
    
    # ===== STEP 5: Define Technical Criteria (Optional) =====
    # Uncomment and customize if you want technical analysis
    technical_criteria = TechnicalCriteria(
        lookback_days=20,           # Days to look back for patterns
        volume_threshold=1.5,        # Volume spike threshold (1.5x average)
        breakout_threshold=1.05,     # Price breakout threshold (5% above bottom)
        stop_loss_threshold=0.95     # Stop loss threshold (5% below bottom)
    )
    
    # ===== STEP 6: Run Technical Analysis (Optional) =====
    # Get symbols from filtered stocks
    symbols_to_analyze = filtered_stocks['symbol'].tolist()
    
    # Limit for performance if needed
    # symbols_to_analyze = symbols_to_analyze[:50]  # Analyze first 50 only
    
    technical_results = technical_screener.batch_technical_analysis(
        symbols_to_analyze, 
        technical_criteria
    )
    
    # ===== STEP 7: Apply Custom Logic =====
    # Add your own custom filtering logic here
    # Example: Filter for fresh breakouts only
    fresh_breakouts = technical_screener.filter_by_fresh_breakout(technical_results)
    
    # ===== STEP 8: Merge and Format Results =====
    # Combine basic and technical results
    final_results = technical_screener.merge_results(technical_results, filtered_stocks)
    
    # ===== STEP 9: Custom Post-Processing =====
    # Add any additional calculations or filtering
    # Example: Sort by volume ratio
    if not final_results.empty and 'volume_ratio' in final_results.columns:
        final_results = final_results.sort_values('volume_ratio', ascending=False)
    
    # ===== STEP 10: Log Summary =====
    logger.info(f"Screening complete: {len(final_results)} stocks found")
    if len(fresh_breakouts) > 0:
        logger.info(f"Fresh breakouts: {len(fresh_breakouts)}")
        for stock in fresh_breakouts[:5]:  # Show top 5
            logger.info(f"  - {stock.get('symbol', 'N/A')}: ${stock.get('current_price', 0):.2f}")
    
    return final_results


# ===== HELPER FUNCTIONS (Optional) =====
def apply_custom_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add your custom filtering logic here
    
    Example custom filters:
    - RSI conditions
    - Moving average crossovers
    - Fundamental ratios
    - News sentiment
    """
    # Example: Filter for positive momentum
    # df = df[df['price_change_pct'] > 0]
    
    return df


def calculate_custom_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate custom scoring or ranking
    """
    # Example: Create composite score
    # df['custom_score'] = df['volume_ratio'] * df['price_change_pct']
    
    return df


# ===== STANDALONE EXECUTION =====
if __name__ == "__main__":
    # This allows the strategy to be run directly
    results = run()
    
    if isinstance(results, pd.DataFrame):
        print(f"\nFound {len(results)} stocks")
        print("\nTop 10 results:")
        print(results.head(10)[['symbol', 'company_name', 'sector', 'current_price']])
    else:
        print(f"\nStrategy completed with {len(results) if results else 0} results")