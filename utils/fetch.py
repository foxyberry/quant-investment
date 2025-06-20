import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from utils.config_manager import ConfigManager
from utils.timezone_utils import make_timezone_aware, convert_dataframe_timezone

config = ConfigManager()

def get_cache_path(symbol: str) -> str:
    file_path = config.get_history_file_path(symbol)
    return file_path


def load_cached_data(symbol: str):
    """Load cached data from CSV with proper timezone handling"""
    path = get_cache_path(symbol)
    if os.path.exists(path):
        try:
            # Load CSV without parsing dates first
            df = pd.read_csv(path, index_col=0)
            
            # Convert index to datetime with proper timezone handling
            if not pd.api.types.is_datetime64_any_dtype(df.index):
                # First try with utc=True to handle mixed timezones properly
                try:
                    df.index = pd.to_datetime(df.index, utc=True)
                except:
                    df.index = pd.to_datetime(df.index)
            
            # If the index has timezone info in string format, convert properly
            if df.index.dtype == 'object':
                # Try to parse as timezone-aware datetime strings
                try:
                    df.index = pd.to_datetime(df.index, utc=True)
                except:
                    df.index = pd.to_datetime(df.index)
            
            return df
        except Exception as e:
            print(f"❌ 캐시 로드 실패: {e}")
    return None


def save_data_to_cache(symbol: str, df: pd.DataFrame):
    path = get_cache_path(symbol)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path)


def fetch_yfinance_data(symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    
    print(f"📥 {symbol} 데이터 다운로드 중... ({start_date.date()} ~ {end_date.date()})")
    ticker = yf.Ticker(symbol.replace('.', '-'))
    df = ticker.history(start=start_date, end=end_date)

    if not df.empty:
        save_data_to_cache(symbol, df)
    else:
        print("⚠️ yfinance로부터 데이터 없음")

    return df


def history_data(symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    ticker = yf.Ticker(symbol.replace('.', '-'))
    data = ticker.history(start=start_date, end=end_date)
    return data

def get_historical_data(symbol: str, start_date: datetime, end_date: datetime):
    """
    Get historical data for a symbol with proper timezone handling
    
    Args:
        symbol: Stock symbol
        start_date: Start date (will be made timezone-aware)
        end_date: End date (will be made timezone-aware)
        
    Returns:
        DataFrame with historical data filtered to the specified date range
    """
    # Ensure dates are timezone-aware
    start_date = make_timezone_aware(start_date)
    end_date = make_timezone_aware(end_date)
    
    df = load_cached_data(symbol)
    
    if df is not None and not df.empty:
        # Ensure DataFrame index is timezone-aware
        df = convert_dataframe_timezone(df)
        
        first_date = df.index[0]
        last_date = df.index[-1]
        
        # Check if we have enough data in cache
        if last_date >= end_date and first_date <= start_date:
            # Filter the data to only include the requested date range
            filtered_df = df[(df.index >= start_date) & (df.index <= end_date)]
            print(f"✅ Using cached data for {symbol}: {len(filtered_df)} days")
            return filtered_df
    
    print(f"🔄 캐시 부족: {symbol}, yfinance로부터 다운로드 시도")
    # Download with some buffer to ensure we have enough data
    buffer_start = start_date - timedelta(days=2)
    buffer_end = end_date + timedelta(days=2)
    
    downloaded_df = fetch_yfinance_data(symbol, buffer_start, buffer_end)
    
    if not downloaded_df.empty:
        # Ensure downloaded data is timezone-aware
        downloaded_df = convert_dataframe_timezone(downloaded_df)
        
        # Filter to the requested date range
        filtered_df = downloaded_df[(downloaded_df.index >= start_date) & (downloaded_df.index <= end_date)]
        print(f"✅ Downloaded and filtered data for {symbol}: {len(filtered_df)} days")
        return filtered_df
    
    return downloaded_df
