#!/usr/bin/env python3
"""
Main backtesting script using backtrader library
"""

from screener.basic_filter import BasicInfoScreener
from utils.config_manager import ConfigManager
from screener.screening_criteria import ScreeningCriteria
from screener.technical_criteria import TechnicalCriteria      
from strategies.backtrader_engine import BacktraderEngine
from strategies.backtrader_strategy import BottomBreakoutStrategy
from utils.timezone_utils import get_valid_backtest_dates

def main():

    # Initialize configuration
    config = ConfigManager()
    
    basic = BasicInfoScreener()
    basic_info_df = basic.get_snp500_basic_info()
    print(f"[1] S&P 500 종목 수: {len(basic_info_df)}")
    
    # 2. Apply basic filters
    basic_filters = config.get_basic_filters()
    criteria = ScreeningCriteria(
        min_price=basic_filters['price']['min'],
        max_price=basic_filters['price']['max'],
        min_volume=basic_filters['volume']['min'],
        min_market_cap=basic_filters['market_cap']['min'],
        sectors=basic_filters['sector']
    )
    
    filtered_df = basic.apply_basic_filters(basic_info_df, criteria)
    print(f"[2] 기본 필터링 후 종목 수: {len(filtered_df)}")
    
    tech_params = config.get_technical_analysis_params()
    
    backtester = BacktraderEngine(initial_cash=100000, commission=0.001)
    
    start_date, end_date = get_valid_backtest_dates(days_back=120)

    # Strategy parameters for backtrader
    strategy_params = {
        'lookback_days': tech_params['lookback_days'],
        'volume_threshold': tech_params['volume_threshold'],
        'breakout_threshold': tech_params['breakout_threshold'],
        'stop_loss_threshold': tech_params['stop_loss_threshold'],
        'take_profit_threshold': tech_params['take_profit_threshold'],
        'start_date': start_date,
        'end_date': end_date
    }
    
    print(f"📅 Backtesting period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"📅 Start date is trading day: {start_date.strftime('%A')}")
    print(f"📅 End date is trading day: {end_date.strftime('%A')}")
        
  
    # 7. Run batch backtest for all symbols
    print("\n🔄 Running batch backtest for all symbols...")
    batch_results = backtester.batch_backtest(
        symbols=["SMCI"],
        start_date=start_date,
        end_date=end_date,
        strategy_class=BottomBreakoutStrategy,
        strategy_params=strategy_params
    )
    
    # 9. Display batch results
    print("\n" + "="*80)
    print("BATCH BACKTEST RESULTS")
    print("="*80)
    
    # Filter out error results for analysis
    successful_results = [r for r in batch_results if 'error' not in r]
    
    if successful_results:
        print(f"\n✅ Successfully backtested {len(successful_results)} out of {len(batch_results)} symbols")
        
        # Sort by total return
        successful_results.sort(key=lambda x: x.get('total_return_pct', 0), reverse=True)
        
        print("\n📈 Top Performers:")
        for result in successful_results[:3]:
            print(f"   {result['symbol']}: {result['total_return_pct']:.2f}% return, "
                  f"{result['num_trades']} trades, {result['max_drawdown_pct']:.2f}% max drawdown")
        
        if len(successful_results) > 3:
            print("\n📉 Other Results:")
            for result in successful_results[3:]:
                print(f"   {result['symbol']}: {result['total_return_pct']:.2f}% return, "
                      f"{result['num_trades']} trades, {result['max_drawdown_pct']:.2f}% max drawdown")
        
        # 10. Strategy comparison for best performer
        if successful_results:
            best_symbol = successful_results[0]['symbol']
            print(f"\n🔍 Comparing strategies for best performer: {best_symbol}")
            
            comparison = backtester.compare_strategies(
                best_symbol, start_date, end_date
            )
            
            if comparison:
                print("\nStrategy Comparison:")
                for strategy_name, result in comparison.items():
                    if 'error' not in result:
                        print(f"   {strategy_name}:")
                        print(f"     Return: {result['total_return_pct']:.2f}%")
                        print(f"     Trades: {result['num_trades']}")
                        print(f"     Max DD: {result['max_drawdown_pct']:.2f}%")
                        print()
                    else:
                        print(f"   {strategy_name}: Error - {result['error']}")
        
        # 11. Summary statistics
        print("\n" + "="*60)
        print("SUMMARY STATISTICS")
        print("="*60)
        returns = [r['total_return_pct'] for r in successful_results]
        trades = [r['num_trades'] for r in successful_results]
        drawdowns = [r['max_drawdown_pct'] for r in successful_results]
        
        for i in returns:
            print(i)

        print(f"Average Total Return: {sum(returns)/len(returns):.2f}%")
        print(f"Average Max Drawdown: {sum(drawdowns)/len(drawdowns):.2f}%")
        print(f"Total Trades: {sum(trades)}")
        print(f"Symbols with Positive Returns: {len([r for r in returns if r > 0])}")
        print(f"Symbols with Negative Returns: {len([r for r in returns if r < 0])}")
        
        # 12. Save results to CSV
        import pandas as pd
        output_file = f"backtrader_results_{end_date.strftime('%Y%m%d_%H%M%S')}.csv"
        results_df = pd.DataFrame(successful_results)
        results_df.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to: {output_file}")
        
    else:
        print("❌ No successful backtest results generated. Check your data and parameters.")
        # Show error details
        for result in batch_results:
            if 'error' in result:
                print(f"   Error: {result['error']}")
    
    print("\n✅ Backtrader backtesting completed!")


if __name__ == "__main__":
    main() 