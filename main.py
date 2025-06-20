import sys
import pandas as pd
import logging
from datetime import datetime, timedelta
from screener.basic_filter import BasicInfoScreener
from screener.technical_filter import TechnicalScreener
from utils.config_manager import ConfigManager
from screener.screening_criteria import ScreeningCriteria
from screener.technical_criteria import TechnicalCriteria
from visualizer.plot_breakout import visualize_all_breakouts
from utils.timezone_utils import get_current_market_time

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/screening.log')
        ]
    )

def main():
    """Main screening execution"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=== Quant Investment Screening Started ===")
    
    try:
        # Initialize configuration
        config = ConfigManager()
        
        # 1. Get S&P 500 basic information
        logger.info("Step 1: Loading S&P 500 basic information...")
        basic_screener = BasicInfoScreener()
        basic_info_df = basic_screener.get_snp500_basic_info()
        logger.info(f"[1] S&P 500 stocks loaded: {len(basic_info_df)}")
        
        if basic_info_df.empty:
            logger.error("No basic info data available. Please run data collection first.")
            return 1
        
        # 2. Apply basic filters
        logger.info("Step 2: Applying basic filters...")
        basic_filters = config.get_basic_filters()
        criteria = ScreeningCriteria(
            min_price=basic_filters['price']['min'],
            max_price=basic_filters['price']['max'],
            min_volume=basic_filters['volume']['min'],
            min_market_cap=basic_filters['market_cap']['min'],
            sectors=basic_filters['sector']
        )
      
        filtered_df = basic_screener.apply_basic_filters(basic_info_df, criteria) 
        logger.info(f"[2] Stocks after basic filtering: {len(filtered_df)}")
        
        # 3. Technical analysis 
        logger.info("Step 3: Running technical analysis...")
        technical_screener = TechnicalScreener()
        tech_params = config.get_technical_analysis_params()
      
        technical_criteria = TechnicalCriteria(
            lookback_days=tech_params['lookback_days'],
            volume_threshold=tech_params['volume_threshold'],
            breakout_threshold=tech_params['breakout_threshold'],
            stop_loss_threshold=tech_params['stop_loss_threshold']
        )
        
        # Analyze symbols (limit for performance in demo)
        symbols_to_analyze = filtered_df['symbol'].head(50).tolist()  # Limit to 50 for demo
        logger.info(f"Analyzing {len(symbols_to_analyze)} symbols for technical patterns")
        
        results = technical_screener.batch_technical_analysis(symbols_to_analyze, technical_criteria)
        
        # Merge results with basic info
        all_results = technical_screener.merge_results(results, filtered_df)
        logger.info(f"[3] Stocks after technical analysis: {len(all_results)}")
        
        # 4. Categorize results
        logger.info("Step 4: Categorizing breakout results...")
        fresh_breakouts = technical_screener.filter_by_fresh_breakout(results)
        
        # Fix the filtering logic for other categories
        already_up_stocks = [r for r in results if r.get('breakout_status') == 'ALREADY UP']
        down_again_stocks = [r for r in results if r.get('breakout_status') == 'DOWN AGAIN AFTER BREAKOUT']
        
        logger.info(f"[4] Fresh breakouts today: {len(fresh_breakouts)}")
        logger.info(f"[4] Already up stocks: {len(already_up_stocks)}")
        logger.info(f"[4] Down again after breakout: {len(down_again_stocks)}")

        # 5. Display results
        if fresh_breakouts:
            logger.info("=== Fresh Breakout Stocks ===")
            for r in fresh_breakouts:
                logger.info(f"✅ {r['symbol']} | Current: ${r['current_price']:.2f} | "
                           f"Bottom: ${r['bottom_price']:.2f} | Breakout: ${r['breakout_price']:.2f}")
        else:
            logger.info("No fresh breakouts detected today")

        # 6. Save results
        current_time = get_current_market_time()
        date_str = current_time.strftime('%Y%m%d_%H%M')
        
        if results:
            # Save all results
            all_results_df = pd.DataFrame(results)
            results_file = f'results/screening_results_{date_str}.csv'
            all_results_df.to_csv(results_file, index=False)
            logger.info(f"Results saved to: {results_file}")
            
            # Save fresh breakouts separately
            if fresh_breakouts:
                breakouts_df = pd.DataFrame(fresh_breakouts)
                breakouts_file = f'results/fresh_breakouts_{date_str}.csv'
                breakouts_df.to_csv(breakouts_file, index=False)
                logger.info(f"Fresh breakouts saved to: {breakouts_file}")

        # 7. Generate visualizations
        if all_results.empty:
            logger.warning("No results to visualize")
        else:
            logger.info("Generating visualizations...")
            try:
                visualize_all_breakouts(all_results)
                logger.info("Visualizations generated successfully")
            except Exception as e:
                logger.error(f"Visualization failed: {e}")

        logger.info("=== Screening completed successfully ===")
        return 0
        
    except Exception as e:
        logger.error(f"Screening failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
