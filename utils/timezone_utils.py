"""
Timezone utilities for US stock market operations
"""
import pytz
from datetime import datetime, timezone, timedelta
from typing import Union, Optional
import pandas_market_calendars as mcal
import pandas as pd
from typing import List
from functools import lru_cache

# US Eastern timezone for stock market operations
US_EASTERN = pytz.timezone('US/Eastern')

def now() -> datetime:
    """Get current time in US Eastern timezone"""
    return datetime.now(US_EASTERN)

def get_us_eastern_timezone():
    """Get US Eastern timezone for stock market operations"""
    return US_EASTERN

@lru_cache(maxsize=1)
def get_market_calendar():
    """Get NYSE market calendar"""
    return mcal.get_calendar('NYSE')

def is_trading_day(date: Union[datetime, str]) -> bool:
    """
    Check if a date is a trading day (not weekend or holiday)

    Args:
        date: datetime or string (YYYY-MM-DD)

    Returns:
        True if it's a trading day, False otherwise
    """
    calendar = get_market_calendar()

    # 안전하게 date 객체로 변환
    if isinstance(date, datetime):
        date_only = date.date()
    elif isinstance(date, str):
        date_only = datetime.strptime(date, "%Y-%m-%d").date()
    elif isinstance(date, (pd.Timestamp,)):
        date_only = date.date()
    else:
        date_only = date  # datetime.date 타입일 경우

    valid_days = calendar.valid_days(start_date=date_only, end_date=date_only)
    return not valid_days.empty


def get_last_trading_day(end_date: Optional[datetime] = None) -> datetime:
    """
    Get the last trading day before or on the given date

    Args:
        end_date: datetime to find last trading day for (default: now)

    Returns:
        Last trading day as timezone-aware datetime in US Eastern
    """
    calendar = get_market_calendar()

    if end_date is None:
        end_date = now()

    # Ensure timezone-aware in US Eastern
    end_date = make_timezone_aware(end_date)

    # Convert to date only
    date_only = end_date.date()

    # Look back 30 days to ensure buffer for long holiday periods
    lookback_start = date_only - timedelta(days=30)
    valid_days = calendar.valid_days(start_date=lookback_start, end_date=date_only)

    if not valid_days.empty:
        last_day = valid_days[-1].to_pydatetime()
        return make_timezone_aware(datetime.combine(last_day.date(), datetime.min.time()))
    else:
        raise ValueError(f"No trading days found between {lookback_start} and {date_only}")


def get_next_trading_day(start_date: Optional[datetime] = None) -> datetime:
    """
    Get the next trading day on or after the given date

    Args:
        start_date: reference date (defaults to now)

    Returns:
        Next trading day as timezone-aware datetime in US Eastern
    """
    calendar = get_market_calendar()

    if start_date is None:
        start_date = now()

    # Ensure timezone-aware in US Eastern
    start_date = make_timezone_aware(start_date)

    date_only = start_date.date()
    lookahead_end = date_only + timedelta(days=30)
    valid_days = calendar.valid_days(start_date=date_only, end_date=lookahead_end)

    if not valid_days.empty:
        next_day = valid_days[0].to_pydatetime()
        return make_timezone_aware(datetime.combine(next_day.date(), datetime.min.time()))
    else:
        raise ValueError(f"No trading days found between {date_only} and {lookahead_end}")


def get_trading_days_between(start_date: datetime, end_date: datetime) -> List[datetime]:
    """
    Get all trading days between two dates (inclusive)
    
    Args:
        start_date: start date
        end_date: end date
        
    Returns:
        List of trading days as datetime objects
    """
    calendar = get_market_calendar()
    # Use schedule method to get trading days
    schedule = calendar.schedule(start_date=start_date, end_date=end_date)
    trading_days = schedule.index.date.tolist()
    return [US_EASTERN.localize(datetime.combine(day, datetime.min.time())) for day in trading_days]

def get_valid_backtest_dates(days_back: int = 365) -> tuple[datetime, datetime]:
    """
    Get valid start and end dates for backtesting

    Args:
        days_back: number of trading days to go back from most recent date

    Returns:
        Tuple of (start_date, end_date) as timezone-aware datetimes in US Eastern
    """
    calendar = get_market_calendar()
    current_time = now()

    # 가장 최근의 거래일 (오늘이 아니면 조정)
    end_date = get_last_trading_day(current_time)
    end_date_only = end_date.date()

    # 넉넉히 캘린더 확보
    start_candidate = end_date_only - timedelta(days=days_back *2)
    schedule = calendar.valid_days(start_date=start_candidate, end_date=end_date_only)

    if len(schedule) < days_back:
        raise ValueError(f"Not enough trading days found. Only {len(schedule)} available.")

    start_day = schedule[-days_back].to_pydatetime()

    # 결과는 timezone-aware로 반환
    start_dt = make_timezone_aware(datetime.combine(start_day.date(), datetime.min.time()))
    end_dt = make_timezone_aware(datetime.combine(end_date_only, datetime.min.time()))

    return start_dt, end_dt


def validate_trading_date(date: datetime, description: str = "date", direction: str = "backward") -> datetime:
    """
    Validate and adjust a date to ensure it's a trading day

    Args:
        date: date to validate
        description: for log message
        direction: "backward" or "forward" adjustment

    Returns:
        Adjusted valid trading date
    """
    if not is_trading_day(date):
        if direction == "forward":
            adjusted_date = get_next_trading_day(date)
        else:
            adjusted_date = get_last_trading_day(date)
        print(f"⚠️ {description} {date.strftime('%Y-%m-%d')} is not a trading day. "
              f"Adjusted to {adjusted_date.strftime('%Y-%m-%d')}")
        return adjusted_date
    return make_timezone_aware(date)


def make_timezone_aware(dt: datetime, target_tz: pytz.timezone = US_EASTERN) -> datetime:
    """
    Make a datetime timezone-aware, converting to target timezone
    
    Args:
        dt: datetime object (timezone-naive or timezone-aware)
        target_tz: target timezone (default: US Eastern)
        
    Returns:
        timezone-aware datetime in target timezone
    """
    if dt.tzinfo is None:
        # If naive, localize to target timezone
        return target_tz.localize(dt)
    else:
        # If already aware, convert to target timezone
        return dt.astimezone(target_tz)

def make_timezone_naive(dt: datetime, source_tz: pytz.timezone = US_EASTERN) -> datetime:
    """
    Make a datetime timezone-naive, assuming it's in source timezone
    
    Args:
        dt: datetime object (timezone-naive or timezone-aware)
        source_tz: source timezone if dt is naive (default: US Eastern)
        
    Returns:
        timezone-naive datetime
    """
    if dt.tzinfo is None:
        # If naive, assume it's in source timezone, localize then remove
        return source_tz.localize(dt).replace(tzinfo=None)
    else:
        # If aware, convert to source timezone then remove
        return dt.astimezone(source_tz).replace(tzinfo=None)

def get_current_market_time() -> datetime:
    """
    Get current time in US Eastern timezone (market time)
    
    Returns:
        current datetime in US Eastern timezone
    """
    return datetime.now(US_EASTERN)

def get_market_date_range(days_back: int = 365) -> tuple[datetime, datetime]:
    """
    Get a date range for market operations
    
    Args:
        days_back: number of days to go back from current market time
        
    Returns:
        tuple of (start_date, end_date) in US Eastern timezone
    """
    end_date = get_current_market_time()
    start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0) - \
                 timedelta(days=days_back)
    
    start_date = make_timezone_aware(start_date)
    return start_date, end_date

def convert_dataframe_timezone(df: 'pd.DataFrame', target_tz: pytz.timezone = US_EASTERN) -> 'pd.DataFrame':
    """
    Convert DataFrame index timezone to target timezone
    
    Args:
        df: DataFrame with datetime index
        target_tz: target timezone (default: US Eastern)
        
    Returns:
        DataFrame with converted timezone
    """
    # Ensure the index is a DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        # Convert to DatetimeIndex if it's not already
        df.index = pd.to_datetime(df.index)
    
    # Now we can safely access timezone properties
    if df.index.tz is None:
        # If naive, localize to target timezone
        df.index = df.index.tz_localize(target_tz)
    else:
        # If aware, convert to target timezone
        df.index = df.index.tz_convert(target_tz)
    return df

def prepare_dataframe_for_backtrader(df: 'pd.DataFrame') -> 'pd.DataFrame':
    """
    Prepare DataFrame for backtrader (timezone-naive in US Eastern)

    Args:
        df: DataFrame with datetime index

    Returns:
        DataFrame with timezone-naive datetime index in US Eastern time
    """
    # Make a copy to avoid modifying the original
    df_copy = df.copy()
    
    # 1. Ensure the index is a DatetimeIndex
    if not isinstance(df_copy.index, pd.DatetimeIndex):
        # Try to convert to DatetimeIndex with UTC handling
        try:
            df_copy.index = pd.to_datetime(df_copy.index, utc=True)
        except:
            # If UTC conversion fails, try without
            df_copy.index = pd.to_datetime(df_copy.index)
    
    # 2. Handle timezone conversion
    if df_copy.index.tz is None:
        # If naive, localize to US Eastern first
        df_copy.index = df_copy.index.tz_localize(US_EASTERN)
    else:
        # If aware, convert to US Eastern
        df_copy.index = df_copy.index.tz_convert(US_EASTERN)

    # 3. Convert to naive datetime for backtrader
    # Use tz_localize(None) which removes timezone info while keeping the time in that timezone
    df_copy.index = df_copy.index.tz_localize(None)
    
    return df_copy