from screener.basic_filter import BasicInfoScreener
from screener.technical_filter import TechnicalScreener
from utils.config_manager import ConfigManager
from screener.screening_criteria import ScreeningCriteria
from screener.technical_criteria import TechnicalCriteria
from visualizer.plot_breakout import visualize_all_breakouts

def main():
    # Initialize configuration
    config = ConfigManager()
    
    # 1. sp500의 기본 정보 가져오기
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
  
    # 2. 기본 필터링
    filtered_df = basic.apply_basic_filters(basic_info_df, criteria) 
    print("[2] 기본 필터링 후 종목 수:", len(filtered_df))
    

    # 3. 기술적 분석 
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

    all_result = tech.merge_results(results, filtered_df)
    print("[3] 기술 체크 후 종목 수:", len(all_result))
    

    fresh_breakouts = [r for r in results if r.get('is_fresh_breakout')]
    already_breakouts = [r for r in results if r.get('breakout_status') != 'ALREADY UP']
    down_again_breakouts = [r for r in results if r.get('breakout_status') != 'DOWN AGAIN AFTER BREAKOUT']
    print("[4] 오늘 breakout 감지된 종목 수:", len(fresh_breakouts))
    print("[4] 돌파중인 종목 수:", len(already_breakouts))
    print("[4] 돌파 후 다시 내려간 종목 수:", len(down_again_breakouts))


    for r in fresh_breakouts:
        print(f"\n✅ {r['symbol']} | 현재가: {r['current_price']:.2f} | 바닥가: {r['bottom_price']:.2f} | 돌파가: {r['breakout_price']:.2f}")

    visualize_all_breakouts(all_result)


if __name__ == "__main__":
    main()
