import yfinance as yf
import pandas as pd
import time
import logging
from typing import List
from .screening_criteria import ScreeningCriteria
import os
from utils.config_manager import ConfigManager
from datetime import datetime

class BasicInfoScreener():
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.config = ConfigManager()
        
    def _is_file_up_to_date(self, file_path: str, max_age_days: int = 1) -> bool:
        """
        Check if the file is up to date
        
        Args:
            file_path: Path to the file to check
            max_age_days: Maximum age of the file in days
            
        Returns:
            bool: True if file is up to date, False otherwise
        """
        if not os.path.exists(file_path):
            self.logger.info(f"File does not exist: {file_path}")
            return False
            
        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        current_time = datetime.now()
        age = current_time - file_time
        
        is_up_to_date = age.days < max_age_days
        if not is_up_to_date:
            self.logger.info(f"File is {age.days} days old, needs update")
        else:
            self.logger.info(f"File is {age.days} days old, still valid")
            
        return is_up_to_date

    def get_snp500_basic_info(self) -> pd.DataFrame:
        """Get S&P 500 basic information"""
        self.logger.info("Getting S&P 500 basic info")
        filename = self.config.get_basic_info_file()
        
        # Check if file exists and is up to date
        if os.path.exists(filename) and self._is_file_up_to_date(filename):
            self.logger.info("Using cached S&P 500 basic info")
            df = self._read_from_csv(filename)
            df['symbol'] = df['symbol'].str.upper()
            return df
        else:
            self.logger.info("Fetching fresh S&P 500 basic info")
            infos = self._get_basic_info_batch(self.get_sp500_symbols())
            self._save(infos, filename)
            return infos

    def _save(self, df: pd.DataFrame, save_path: str) -> None:
            """
            데이터프레임을 CSV 파일로 저장
            
            Args:
                df: 저장할 데이터프레임
                filename: 저장할 파일 이름 (예: 'data/basic_info.csv')
            """
            try:
                
                # CSV로 저장
                df.to_csv(save_path, index=False)
                self.logger.info(f"✅ 데이터 저장 완료: {save_path}")
                
            except Exception as e:
                self.logger.error(f"❌ 데이터 저장 실패: {e}")
                raise
        
    def _read_from_csv(self, file_path: str) -> pd.DataFrame:
        """
        CSV 파일에서 데이터프레임 읽기
        
        Args:
            filename: 읽을 파일 이름 (예: 'basic_info.csv')
            
        Returns:
            pd.DataFrame: 읽어온 데이터프레임
        """
        
        try:
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
            
    def get_sp500_symbols(self) -> List[str]:
        """S&P 500 종목 리스트 가져오기"""
        self.logger.info("Getting S&P 500 symbols")
        try:
            filename = self.config.get_snp500_info_file()
            
            # Check if file exists and is up to date
            if os.path.exists(filename) and self._is_file_up_to_date(filename):
                self.logger.info("Using cached S&P 500 symbols")
                df = self._read_from_csv(filename)
                return df['symbol'].tolist()
            else:
                self.logger.info("Fetching fresh S&P 500 symbols from Wikipedia")
                url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
                tables = pd.read_html(url)
                sp500_table = tables[0]
                symbols = sp500_table['Symbol'].tolist()
                
                # Convert list to DataFrame before saving
                symbols_df = pd.DataFrame({'symbol': symbols})
                self._save(symbols_df, filename)
                return symbols
                
        except Exception as e:
            self.logger.error(f"S&P 500 목록 로드 실패: {e}")
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']

    def _get_basic_info_batch(self, symbols: List[str]) -> pd.DataFrame:
        """
        배치 단위로 주식 기본 정보를 수집합니다.
        
        Args:
            symbols: 수집할 주식 심볼 리스트
            
        Returns:
            pd.DataFrame: 수집된 기본 정보를 담은 데이터프레임
        """
        self.logger.info(f"Starting batch data collection for {len(symbols)} symbols")
        batch_size = 50
        all_data = []
        total_batches = (len(symbols) + batch_size - 1) // batch_size

        for i in range(0, len(symbols), batch_size):
            batch_num = (i // batch_size) + 1
            batch_symbols = symbols[i:i+batch_size]
            self.logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_symbols)} symbols)")
            
            # Handle special symbols (replace dots with hyphens)
            processed_symbols = [symbol.replace('.', '-') for symbol in batch_symbols]
            tickers = yf.Tickers(' '.join(processed_symbols))

            for idx, symbol in enumerate(batch_symbols):
                try:
                    
                    # Use the processed symbol for yfinance but keep original for storage
                    processed_symbol = processed_symbols[idx]
                    ticker = tickers.tickers[processed_symbol]
                    info = ticker.info
                    
                    # Get the latest trading date
                    history = ticker.history(period='1d')
                    latest_date = history.index[-1] if not history.empty else None
                    
                    basic_data = {
                        'symbol': symbol,  # Store original symbol
                        'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                        'volume': info.get('volume', info.get('regularMarketVolume', 0)),
                        'market_cap': info.get('marketCap', 0),
                        'sector': info.get('sector', 'Unknown'),
                        'industry': info.get('industry', 'Unknown'),
                        'last_updated': latest_date.strftime('%Y-%m-%d') if latest_date else None,
                        'data_date': pd.Timestamp.now().strftime('%Y-%m-%d')
                    }
                    all_data.append(basic_data)
                    self.logger.debug(f"Successfully collected data for {symbol}")

                except Exception as e:
                    self.logger.warning(f"Failed to collect data for {symbol}: {e}")
                    continue

            self.logger.info(f"Completed batch {batch_num}/{total_batches}")
            time.sleep(1)  # API 제한 회피

        df = pd.DataFrame(all_data)
        self.logger.info(f"Data collection completed. Collected data for {len(df)} symbols")
        return df

    def apply_basic_filters(self, df: pd.DataFrame, criteria: ScreeningCriteria) -> pd.DataFrame:
        
        initial_count = len(df)
        self.logger.info(f"Applying basic filters to {initial_count} stocks")
        
        df = df[(df['price'] >= criteria.min_price) & (df['price'] <= criteria.max_price)]
        self.logger.info(f"After price filter: {len(df)} stocks")
        
        df = df[df['volume'] >= criteria.min_volume]
        self.logger.info(f"After volume filter: {len(df)} stocks")
        
        df = df[df['market_cap'] >= criteria.min_market_cap]
        self.logger.info(f"After market cap filter: {len(df)} stocks")

        if criteria.sectors:
            df = df[df['sector'].isin(criteria.sectors)]
            self.logger.info(f"After sector filter: {len(df)} stocks")

        final_count = len(df)
        self.logger.info(f"Filtering completed. {initial_count - final_count} stocks filtered out")
        return df.reset_index(drop=True)
