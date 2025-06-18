from screener.basic_filter import BasicInfoScreener
from screener.technical_filter import TechnicalScreener
from utils.config_manager import ConfigManager
from screener.screening_criteria import ScreeningCriteria
from screener.technical_criteria import TechnicalCriteria
from visualizer.plot_breakout import visualize_all_breakouts
import pandas as pd

def main():
    # Initialize configuration
    config = ConfigManager()
    
    # 1. 기본 필터링 수행
    basic = BasicInfoScreener()
    

    basic_info_df = basic.get_snp500_basic_info()
    print("[1] S&P 500 종목 수:", len(basic_info_df))
    
    # Get screening criteria from config
    basic_filters = config.get_basic_filters()
    criteria = ScreeningCriteria(
        min_price=basic_filters['price']['min'],
        max_price=basic_filters['price']['max'],
        min_volume=basic_filters['volume']['min'],
        min_market_cap=basic_filters['market_cap']['min'],
        sectors=basic_filters['sector']
    )
  

    filtered_df = basic.apply_basic_filters(basic_info_df, criteria)
    print(filtered_df.head())
    
    print("[2] 기본 필터링 후 종목 수:", len(filtered_df))
    

    # 2. 기술적 분석 (병렬 처리)
    tech = TechnicalScreener()
    tech_params = config.get_technical_analysis_params()
  
    results = tech.batch_technical_analysis(
        symbols=filtered_df['symbol'].tolist(),
        technical_criteria=TechnicalCriteria(
            lookback_days=tech_params['lookback_days'],
            volume_threshold=tech_params['volume_threshold'],
            breakout_threshold=tech_params['breakout_threshold'],
            stop_loss_threshold=tech_params['stop_loss_threshold']
        )
    )

    print("[3] 기술 체크 후 종목 수:", len(results))
    all_result = pd.DataFrame(results).merge(filtered_df, on='symbol', how='inner')
    print(all_result.head())

    visualize_all_breakouts(all_result)

    exit()
    fresh_breakouts = [r for r in results if r.get('is_fresh_breakout')]
    print("[4] 오늘 breakout 감지된 종목 수:", len(fresh_breakouts))
    for r in fresh_breakouts:
        print(f"\n✅ {r['symbol']} | 현재가: {r['current_price']:.2f} | 바닥가: {r['bottom_price']:.2f} | 돌파가: {r['breakout_price']:.2f}")


if __name__ == "__main__":
    main()
