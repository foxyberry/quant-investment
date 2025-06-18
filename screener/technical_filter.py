import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import logging
from screener.technical_criteria import TechnicalCriteria
import concurrent.futures
from datetime import timezone
from utils.config_manager import ConfigManager
from utils.fetch import get_historical_data

class TechnicalScreener:
    """
    기술적 분석 기반 스크리너
    - 바닥 가격 대비 5% 돌파 조건
    - 거래량 증가 조건 등
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = ConfigManager()

        
    def get_historical_data(self, symbol: str, lookback_days: int):
        
        """Get historical data, either from CSV or by downloading"""
        try:
           
            # Check if we have enough recent data
            end_date = datetime.now(tz=timezone.utc)
            start_date = end_date - timedelta(days=lookback_days * 2)
            start_date = start_date.replace(tzinfo=timezone.utc)
             
            data = get_historical_data(symbol,start_date, end_date)
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()

    def merge_results(self, results: List[Dict], filtered_df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(results).merge(filtered_df, on='symbol', how='inner')
    
    def analyze_bottom_breakout(self, symbol: str, technical_criteria: TechnicalCriteria):
        
        try:
            data = self.get_historical_data(symbol, technical_criteria.lookback_days + 1)
            
            if data is None or len(data) < technical_criteria.lookback_days + 1:
                print("데이터 길이 불충분")
                return None
            
            # 바닥 계산 (lookback_days만큼의 과거 구간에서)
            recent_lows = data['Low'].iloc[-(technical_criteria.lookback_days + 1):-1] # 오늘은 제외
            bottom_price = recent_lows.min()
            bottom_date = recent_lows.idxmin()


            # Find the first date when price closed above breakout level
            # Start from the day after bottom_date
            data_after_bottom = data[data.index > bottom_date]
            
            
            breakout_price = bottom_price * technical_criteria.breakout_threshold
            stop_loss_price = bottom_price * technical_criteria.stop_loss_threshold

            # Find first breakout
            breakout_mask = data_after_bottom['Close'] >= breakout_price
            first_breakout_dates = data_after_bottom[breakout_mask]
            
            # Handle case where no breakout is found
            if len(first_breakout_dates) == 0:
                first_breakout_date = None
                days_since_first_breakout = None
            else:
                first_breakout_date = first_breakout_dates.index[0]
                days_since_first_breakout = (data.index[-1] - first_breakout_date).days

            
            # 오늘 종가
            current_price = data['Close'].iloc[-1]
            
            # 어제까지 종가들이 breakout_price 미만이어야 함
            prev_closes = data['Close'].iloc[-(technical_criteria.lookback_days):-1]
            has_broken_before = (prev_closes >= breakout_price).any()
            is_breakout_today = current_price >= breakout_price
            
            # 조건: 이전엔 돌파 안 했고 오늘 처음 돌파한 경우
            is_fresh_breakout = (not has_broken_before) and is_breakout_today

            # 돌파 상황
            breakout_status = "FIRST BREAKOUT" if is_fresh_breakout else ("ALREAY UP" if is_breakout_today  else "DOWN AGAIN AFTER BREAKOUT")

            avg_volume = data['Volume'].iloc[-11:-1].mean() # 어제까지 10일 평균
            recent_volume = data['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

            result = {
                'symbol': symbol,
                'current_price': current_price,
                'bottom_date': bottom_date,
                'bottom_price': bottom_price,
                'first_breakout_date': first_breakout_date,
                'days_since_first_breakout': days_since_first_breakout,
                'breakout_price': breakout_price,
                'stop_loss_price': stop_loss_price,
                'is_breakout_today': is_breakout_today,
                'is_fresh_breakout': is_fresh_breakout,
                'breakout_status': breakout_status,
                'price_from_bottom_pct': ((current_price - bottom_price) / bottom_price) * 100,
                'volume_ratio': volume_ratio,
                'avg_volume_10d': avg_volume,
                'analysis_date': datetime.now()
            }
            return result
        except Exception as e:
            self.logger.warning(f"{symbol} 분석 실패: {e}")
            return None

    def filterByFreshBreakout(self, results: List[Dict]) -> List[Dict]:
        return [r for r in results if r.get("is_fresh_breakout")]
    
    def batch_technical_analysis(self, symbols: List[str], technical_criteria: TechnicalCriteria) -> List[Dict]:
        """
        여러 종목에 대해 기술적 분석을 수행합니다.
        
        Args:
            symbols: 분석할 종목 심볼 리스트
            technical_criteria: 기술적 분석 기준
            
        Returns:
            List[Dict]: 분석 결과 리스트
        """
        
        self.logger.info(f"Starting technical analysis for {len(symbols)} symbols")
        results = []
        max_workers = 10

        # 병렬 처리로 속도 향상
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 작업 제출
            future_to_symbol = {
                executor.submit(self.analyze_bottom_breakout, symbol, technical_criteria): symbol 
                for symbol in symbols
            }
            
            # 결과 수집
            for future in concurrent.futures.as_completed(future_to_symbol):
                result = future.result()
                if result:
                    results.append(result)
        
        self.logger.info(f"✅ 2차 분석 완료: {len(results)}개 종목 분석 성공")
        
        
        return results
