"""
Stock data fetching utilities
주가 데이터 조회 유틸리티

Usage:
    from utils.fetch import get_ohlcv

    # Simple interface
    data = get_ohlcv("AAPL", days=365)
    data = get_ohlcv("005930.KS", days=365)  # Korean stock
"""

import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from utils.config_manager import ConfigManager
from utils.timezone_utils import make_timezone_aware, convert_dataframe_timezone

config = ConfigManager()

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"

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


def get_ohlcv(
    ticker: str,
    days: int = 365,
    use_cache: bool = True
) -> pd.DataFrame:
    """
    단일 종목 OHLCV 데이터 조회

    Args:
        ticker: 종목 코드 (예: "AAPL", "005930.KS")
        days: 조회 기간 (일 수, 기본 365일)
        use_cache: 캐시 사용 여부

    Returns:
        DataFrame with columns: open, high, low, close, volume
        (lowercase column names for consistency)
    """
    cache_file = CACHE_DIR / f"{ticker.replace('.', '_')}_ohlcv.csv"

    # Try cache first
    if use_cache and cache_file.exists():
        try:
            cached = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            cache_age = (datetime.now() - cached.index[-1].replace(tzinfo=None)).days

            # Use cache if it's recent (less than 1 day old for last data point)
            if cache_age <= 1 and len(cached) >= days * 0.7:
                return _normalize_columns(cached.tail(days))
        except Exception:
            pass

    # Fetch from yfinance
    try:
        yf_ticker = yf.Ticker(ticker)
        period = _days_to_period(days)
        data = yf_ticker.history(period=period, auto_adjust=True)

        if data.empty:
            raise ValueError(f"No data found for ticker: {ticker}")

        # Save to cache
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            data.to_csv(cache_file)

        return _normalize_columns(data)

    except Exception as e:
        raise ValueError(f"Failed to fetch data for {ticker}: {e}")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼명을 소문자로 통일"""
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # Ensure required columns exist
    required = ['open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Select only required columns
    return df[required]


def _days_to_period(days: int) -> str:
    """일 수를 yfinance period 문자열로 변환"""
    if days <= 5:
        return "5d"
    elif days <= 30:
        return "1mo"
    elif days <= 90:
        return "3mo"
    elif days <= 180:
        return "6mo"
    elif days <= 365:
        return "1y"
    elif days <= 730:
        return "2y"
    elif days <= 1825:
        return "5y"
    else:
        return "max"


def get_current_price(ticker: str) -> Optional[float]:
    """
    현재가 조회

    Args:
        ticker: 종목 코드

    Returns:
        현재가 (없으면 None)
    """
    try:
        yf_ticker = yf.Ticker(ticker)
        data = yf_ticker.history(period="5d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception:
        pass
    return None
