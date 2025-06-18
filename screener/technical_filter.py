import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from screener.technical_criteria import TechnicalCriteria
import concurrent.futures
from datetime import timezone
from utils.config_manager import ConfigManager
import os

class TechnicalScreener:
    """
    기술적 분석 기반 스크리너
    - 바닥 가격 대비 5% 돌파 조건
    - 거래량 증가 조건 등
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = ConfigManager()

    def save_history_data(self, symbol: str, data: pd.DataFrame) -> None:
        """Save historical data to CSV"""
        try:
            file_path = self.config.get_history_file_path(symbol)
            data.to_csv(file_path, index=True)
            self.logger.info(f"✅ Saved historical data for {symbol}")
        except Exception as e:
            self.logger.error(f"❌ Failed to save historical data for {symbol}: {e}")
            return None
        
    def load_history_data(self, symbol: str) -> pd.DataFrame:
        """Load historical data from CSV if exists"""
        try:
            file_path = self.config.get_history_file_path(symbol)
            if os.path.exists(file_path):
                data = pd.read_csv(file_path, index_col=0, parse_dates=True)
                self.logger.info(f"✅ Loaded historical data for {symbol}")
                return data
            return None 
        except Exception as e:
            self.logger.error(f"❌ Failed to load historical data for {symbol}: {e}")
            return None
        
    def get_historical_data(self, symbol: str, lookback_days: int) -> Optional[pd.DataFrame]:
        
        """Get historical data, either from CSV or by downloading"""
        try:
            # Try to load from CSV first
            data = self.load_history_data(symbol)
            
            # Check if we have enough recent data
            end_date = datetime.now(tz=timezone.utc)
            start_date = end_date - timedelta(days=lookback_days * 2)
            start_date = start_date.replace(tzinfo=timezone.utc)
            
            if data is not None:
                if data.index[-1] >= start_date:
                    self.logger.info(f"Using cached data for {symbol}")
                    return data
            
            # If no cached data or data is too old, download new data
            self.logger.info(f"Downloading new data for {symbol}")
            
            ticker = yf.Ticker(symbol.replace('.', '-'))
            data = ticker.history(start=start_date, end=end_date)
            
            if not data.empty:
                self.save_history_data(symbol, data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()

    def analyze_bottom_breakout(self, symbol: str, technical_criteria: TechnicalCriteria) -> Optional[Dict]:
        
        try:
            data = self.get_historical_data(symbol, technical_criteria.lookback_days)
            
            if data is None or len(data) < technical_criteria.lookback_days + 1:
                return None
            
            recent_lows = data['Low'].iloc[-(technical_criteria.lookback_days + 1):-1]
            bottom_price = recent_lows.min()
            bottom_date = recent_lows.idxmin()
            
            breakout_price = bottom_price * technical_criteria.breakout_threshold
            stop_loss_price = bottom_price * technical_criteria.stop_loss_threshold
            
            current_price = data['Close'].iloc[-1]
            
            prev_closes = data['Close'].iloc[-(technical_criteria.lookback_days):-1]
            has_broken_before = (prev_closes >= breakout_price).any()
            is_breakout_today = current_price >= breakout_price
            is_fresh_breakout = (not has_broken_before) and is_breakout_today

            avg_volume = data['Volume'].iloc[-11:-1].mean()
            recent_volume = data['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

            result = {
                'symbol': symbol,
                'current_price': current_price,
                'bottom_date': bottom_date,
                'bottom_price': bottom_price,
                'breakout_price': breakout_price,
                'stop_loss_price': stop_loss_price,
                'is_breakout_today': is_breakout_today,
                'is_fresh_breakout': is_fresh_breakout,
                'price_from_bottom_pct': ((current_price - bottom_price) / bottom_price) * 100,
                'volume_ratio': volume_ratio,
                'avg_volume_10d': avg_volume,
                'analysis_date': datetime.now()
            }
            return result
        except Exception as e:
            self.logger.warning(f"{symbol} 분석 실패: {e}")
            return None

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
