from dataclasses import dataclass
from typing import List
import pandas as pd
import yfinance as yf
import os
import time
from typing import Dict
from datetime import datetime, timedelta
import concurrent.futures
from datetime import timezone

@dataclass
class ScreeningCriteria:
    """스크리닝 조건"""
    min_price: float = 10.0
    max_price: float = 1000.0
    min_volume: int = 100000
    min_market_cap: float = 1000000000  # 10억 달러
    sectors: List[str] = None
    bottom_breakout_pct: float = 5.0    # 바닥 돌파 %



class SmartStockScreener:
    """
    스마트 주식 스크리너
    - 단계별 필터링으로 효율성 극대화
    - 필요한 데이터만 선별적 다운로드
    """
    
    def __init__(self):
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        import logging
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)

class BasicInfoScreener(SmartStockScreener):
    """
    기본 정보만으로 1차 필터링
    - 가격, 거래량, 시가총액으로 대부분 걸러냄
    - 빠르고 API 호출 최소화
    """
    def __init__(self): 
        super().__init__()

    def get_sp500_info(self, filename: str) -> pd.DataFrame:

        if(os.path.exists(filename)):
            print("이미존재")
            saved_infos = bis.read_from_csv(filename)
        else:
            print("없음")
            symbols = bis.get_sp500_symbols()
            infos = bis.get_basic_info_batch(symbols)
            bis.save(infos, filename)  # Saves to data/basic_info.csv
            saved_infos = bis.read_from_csv(filename)

            saved_infos.head()
    
    def get_sp500_symbols(self) -> List[str]:
        """S&P 500 종목 리스트 가져오기"""
        try:
            # Wikipedia에서 S&P 500 목록 가져오기 (무료!)
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            tables = pd.read_html(url)
            sp500_table = tables[0]
            symbols = sp500_table['Symbol'].tolist()
            
            self.logger.info(f"S&P 500 종목 {len(symbols)}개 로드 완료")
            return symbols
            
        except Exception as e:
            self.logger.error(f"S&P 500 목록 로드 실패: {e}")
            # 백업: 주요 종목들
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK-B', 'JNJ', 'V']
    
    
    
    def get_basic_info_batch(self, symbols: List[str]) -> pd.DataFrame:
        """
        배치로 기본 정보 가져오기 (핵심!)
        - 한 번의 API 호출로 여러 종목 정보 수집
        """
        try:
            # 최대 100개씩 배치 처리
            batch_size = 10
            all_data = []
            
            for i in range(0, len(symbols), batch_size):

                batch_symbols = symbols[i:i+batch_size]
                symbols_str = ' '.join(batch_symbols)
                
                self.logger.info(f"배치 {i//batch_size + 1}: {len(batch_symbols)}개 종목 처리 중...")
                
                # yfinance로 배치 다운로드
                tickers = yf.Tickers(symbols_str)
                
                for symbol in batch_symbols:
                    try:
                        ticker = tickers.tickers[symbol]
                        info = ticker.info
                        
                        # 핵심 정보만 추출
                        basic_data = {
                            'symbol': symbol,
                            'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                            'volume': info.get('volume', info.get('regularMarketVolume', 0)),
                            'market_cap': info.get('marketCap', 0),
                            'sector': info.get('sector', 'Unknown'),
                            'industry': info.get('industry', 'Unknown'),
                            'pe_ratio': info.get('trailingPE', 0),
                            'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                            'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                        }
                        all_data.append(basic_data)
                        
                    except Exception as e:
                        self.logger.warning(f"{symbol} 정보 수집 실패: {e}")
                        continue
                
                # API 제한 방지를 위한 대기
                time.sleep(1)
            
            df = pd.DataFrame(all_data)
            self.logger.info(f"총 {len(df)}개 종목 기본 정보 수집 완료")
            return df
            
        except Exception as e:
            self.logger.error(f"기본 정보 수집 실패: {e}")
            return pd.DataFrame()
    
    
    def save(self, df: pd.DataFrame, filename: str) -> None:
        """
        데이터프레임을 CSV 파일로 저장
        
        Args:
            df: 저장할 데이터프레임
            filename: 저장할 파일 이름 (예: 'basic_info.csv')
        """
        try:
            # 저장 경로 설정
            save_path = f"data/{filename}"
            
            # 디렉토리가 없으면 생성
            os.makedirs("data", exist_ok=True)
            
            # CSV로 저장
            df.to_csv(save_path, index=False)
            self.logger.info(f"✅ 데이터 저장 완료: {save_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 데이터 저장 실패: {e}")
            raise
    
    def read_from_csv(self, filename: str) -> pd.DataFrame:
        """
        CSV 파일에서 데이터프레임 읽기
        
        Args:
            filename: 읽을 파일 이름 (예: 'basic_info.csv')
            
        Returns:
            pd.DataFrame: 읽어온 데이터프레임
        """
        try:
            # 파일 경로 설정
            file_path = f"data/{filename}"
            
            # 파일 존재 확인
            if not os.path.exists(file_path):
                self.logger.warning(f"⚠️ 파일이 존재하지 않음: {file_path}")
                return pd.DataFrame()
            
            # CSV 읽기
            df = pd.read_csv(file_path)
            self.logger.info(f"✅ CSV 파일 읽기 완료: {len(df)}개 종목")
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ 데이터 읽기 실패: {e}")
            return pd.DataFrame()
    

    def apply_basic_filters(self, df: pd.DataFrame, criteria: ScreeningCriteria) -> pd.DataFrame:
        """기본 필터 적용 - 대부분 종목이 여기서 걸러짐!"""
        
        initial_count = len(df)
        self.logger.info(f"1차 필터링 시작: {initial_count}개 종목 스크리닝 수행")
        
        # 가격 필터
        df = df[(df['price'] >= criteria.min_price) & (df['price'] <= criteria.max_price)]
        self.logger.info(f"가격 필터 후: {len(df)}개 ({initial_count - len(df)}개 제거)")
        
        # 거래량 필터
        df = df[df['volume'] >= criteria.min_volume]
        self.logger.info(f"거래량 필터 후: {len(df)}개")
        
        # 시가총액 필터
        df = df[df['market_cap'] >= criteria.min_market_cap]
        self.logger.info(f"시가총액 필터 후: {len(df)}개")
        
        # 섹터 필터 (선택적)
        if criteria.sectors:
            df = df[df['sector'].isin(criteria.sectors)]
            self.logger.info(f"섹터 필터 후: {len(df)}개")
        
        # 결측치 제거
        df = df.dropna(subset=['price', 'volume', 'market_cap'])
        
        self.logger.info(f"✅ 1차 필터링 완료: {initial_count}개 → {len(df)}개 (제거율: {(1-len(df)/initial_count)*100:.1f}%)")
        
        return df

class TechnicalScreener(SmartStockScreener):
    """
    기술적 분석 기반 2차 필터링
    - 1차 통과 종목들만 상세 분석
    - 바닥 돌파 등 구체적 조건 확인
    """
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.history_dir = "data/history"
        os.makedirs(self.history_dir, exist_ok=True)
    
    def get_history_file_path(self, symbol: str) -> str:
        """Get the path for storing historical data"""
        return os.path.join(self.history_dir, f"{symbol}_history.csv")
    
    def save_history_data(self, symbol: str, data: pd.DataFrame) -> None:
        """Save historical data to CSV"""
        try:
            file_path = self.get_history_file_path(symbol)
            data.to_csv(file_path)
            self.logger.info(f"✅ Historical data saved for {symbol}")
        except Exception as e:
            self.logger.error(f"❌ Failed to save historical data for {symbol}: {e}")
    
    def load_history_data(self, symbol: str) -> pd.DataFrame:
        """Load historical data from CSV if exists"""
        try:
            file_path = self.get_history_file_path(symbol)
            if os.path.exists(file_path):
                data = pd.read_csv(file_path, index_col=0, parse_dates=True)
                self.logger.info(f"✅ Loaded historical data for {symbol}")
                return data
            return None
        except Exception as e:
            self.logger.error(f"❌ Failed to load historical data for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol: str, lookback_days: int = 20) -> pd.DataFrame:
    
        """Get historical data, either from CSV or by downloading"""
        try:
            # Try to load from CSV first
            data = self.load_history_data(symbol)
            
            # Check if we have enough recent data
            
            start_date = end_date - timedelta(days=lookback_days * 2)
            start_date = end_date - timedelta(days=lookback_days * 2)
            start_date = start_date.replace(tzinfo=timezone.utc)
            
            if data is not None:
                if data.index[-1] >= start_date:
                    self.logger.info(f"Using cached data for {symbol}")
                    return data
            
            # If no cached data or data is too old, download new data
            self.logger.info(f"Downloading new data for {symbol}")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if not data.empty:
                self.save_history_data(symbol, data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()
    

    def analyze_bottom_breakout(self, symbol: str, lookback_days: int = 20) -> Dict:
        """바닥 돌파 분석 (친구 전략 적용)"""
        try:
            # Get historical data (from cache or download)
            data = self.get_historical_data(symbol, lookback_days)
            
            if len(data) < lookback_days:
                return None
            
            # 최근 N일 최저점 (바닥)
            recent_lows = data['Low'].tail(lookback_days)
            bottom_date = recent_lows.idxmin()
            bottom_price = recent_lows.min()
            
            
            # 현재가
            current_price = data['Close'].iloc[-1]
            
            # 바닥 돌파 확인
            breakout_price = bottom_price * 1.05  # 5% 돌파

            # stop loss 값 설정
            stop_loss_price = bottom_price * 0.95
            
            # 거래량 증가 확인
            avg_volume = data['Volume'].tail(10).mean()
            recent_volume = data['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0
            
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'bottom_date': bottom_date,
                'bottom_price': bottom_price,
                'breakout_price': breakout_price,
                'stop_loss_price': stop_loss_price,
                'is_breakout': current_price >= breakout_price,
                'price_from_bottom_pct': ((current_price - bottom_price) / bottom_price) * 100,
                'volume_ratio': volume_ratio,
                'avg_volume_10d': avg_volume,
                'analysis_date': datetime.now()
            }
            
            return result
            
        except Exception as e:
            self.logger.warning(f"{symbol} 기술적 분석 실패: {e}")
            return None
    
    def batch_technical_analysis(self, symbols: List[str], max_workers: int = 10) -> List[Dict]:
        """병렬 처리로 기술적 분석 (속도 향상!)"""
        
        self.logger.info(f"2차 기술적 분석 시작: {len(symbols)}개 종목")
        
        results = []
        
        # 병렬 처리로 속도 향상
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 작업 제출
            future_to_symbol = {
                executor.submit(self.analyze_bottom_breakout, symbol): symbol 
                for symbol in symbols
            }
            
            # 결과 수집
            for future in concurrent.futures.as_completed(future_to_symbol):
                result = future.result()
                if result:
                    results.append(result)
        
        self.logger.info(f"✅ 2차 분석 완료: {len(results)}개 종목 분석 성공")
        
        return results
