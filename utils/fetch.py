import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from utils.config_manager import ConfigManager

config = ConfigManager()

def get_cache_path(symbol: str) -> str:
    file_path = config.get_history_file_path(symbol)
    return file_path


def load_cached_data(symbol: str):
    path = get_cache_path(symbol)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
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
    
    df = load_cached_data(symbol)
    
    if df is not None and not df.empty and df.index[-1] >= start_date:
        return df

    print(f"🔄 캐시 부족: {symbol}, yfinance로부터 다운로드 시도")
    return fetch_yfinance_data(symbol, start_date, end_date)
