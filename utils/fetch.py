import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional


def get_cache_path(symbol: str) -> str:
    return os.path.join("data", "history", f"{symbol}_history.csv")


def load_cached_data(symbol: str) -> Optional[pd.DataFrame]:
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


def fetch_yfinance_data(symbol: str, lookback_days: int = 20) -> pd.DataFrame:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days * 2)

    print(f"📥 {symbol} 데이터 다운로드 중... ({start_date.date()} ~ {end_date.date()})")
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date, end=end_date)

    if not df.empty:
        save_data_to_cache(symbol, df)
    else:
        print("⚠️ yfinance로부터 데이터 없음")

    return df


def get_historical_data(symbol: str, lookback_days: int = 20) -> Optional[pd.DataFrame]:
    df = load_cached_data(symbol)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days * 2)

    if df is not None and not df.empty and df.index[-1] >= start_date:
        print(f"✅ 캐시된 데이터 사용: {symbol}")
        return df

    print(f"🔄 캐시 부족: {symbol}, yfinance로부터 다운로드 시도")
    return fetch_yfinance_data(symbol, lookback_days)
