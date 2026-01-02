import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from utils.config_manager import ConfigManager
from utils.timezone_utils import make_timezone_aware, get_current_market_time

config = ConfigManager()

def get_options_cache_path(symbol: str, option_type: str, expiry: str) -> str:
    """Get cache path for options data"""
    cache_dir = os.path.join('data', 'options', symbol)
    filename = f"{symbol}_{option_type}_{expiry}.csv"
    return os.path.join(cache_dir, filename)

def get_options_volume_cache_path(symbol: str) -> str:
    """Get cache path for options volume history"""
    cache_dir = os.path.join('data', 'options_volume')
    filename = f"{symbol}_volume_history.csv"
    return os.path.join(cache_dir, filename)

def load_cached_options_data(symbol: str, option_type: str, expiry: str) -> Optional[pd.DataFrame]:
    """Load cached options data from CSV"""
    path = get_options_cache_path(symbol, option_type, expiry)
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            # Check if data is from today
            if not df.empty and 'timestamp' in df.columns:
                last_update = pd.to_datetime(df['timestamp'].iloc[-1])
                if last_update.date() == datetime.now().date():
                    return df
        except Exception as e:
            print(f"Error loading cache for {symbol}: {e}")
    return None

def save_options_data_to_cache(symbol: str, option_type: str, expiry: str, df: pd.DataFrame):
    """Save options data to cache"""
    path = get_options_cache_path(symbol, option_type, expiry)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df['timestamp'] = datetime.now()
    df.to_csv(path)

def fetch_options_chain(symbol: str) -> Dict:
    """
    Fetch complete options chain for a symbol
    
    Returns:
        Dict with 'calls' and 'puts' DataFrames for all expiration dates
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # Get available expiration dates
        expirations = ticker.options
        
        if not expirations:
            print(f"No options available for {symbol}")
            return {'calls': pd.DataFrame(), 'puts': pd.DataFrame()}
        
        all_calls = []
        all_puts = []
        
        # Fetch data for each expiration
        for expiry in expirations[:5]:  # Limit to first 5 expirations for performance
            try:
                opt = ticker.option_chain(expiry)
                
                # Add expiration date to the data
                opt.calls['expiry'] = expiry
                opt.puts['expiry'] = expiry
                
                all_calls.append(opt.calls)
                all_puts.append(opt.puts)
                
                # Cache individual expiry data
                save_options_data_to_cache(symbol, 'calls', expiry, opt.calls)
                save_options_data_to_cache(symbol, 'puts', expiry, opt.puts)
                
            except Exception as e:
                print(f"Error fetching {expiry} options for {symbol}: {e}")
                continue
        
        # Combine all expirations
        calls_df = pd.concat(all_calls, ignore_index=True) if all_calls else pd.DataFrame()
        puts_df = pd.concat(all_puts, ignore_index=True) if all_puts else pd.DataFrame()
        
        return {'calls': calls_df, 'puts': puts_df}
        
    except Exception as e:
        print(f"Error fetching options for {symbol}: {e}")
        return {'calls': pd.DataFrame(), 'puts': pd.DataFrame()}

def get_options_volume_history(symbol: str, days: int = 5) -> pd.DataFrame:
    """
    Get historical options volume data for calculating averages
    
    Args:
        symbol: Stock symbol
        days: Number of days to look back
        
    Returns:
        DataFrame with historical volume data
    """
    path = get_options_volume_cache_path(symbol)
    
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            # Filter to last N days
            cutoff_date = datetime.now() - timedelta(days=days)
            return df[df.index > cutoff_date]
        except Exception as e:
            print(f"Error loading volume history: {e}")
    
    return pd.DataFrame()

def save_options_volume_history(symbol: str, volume_data: Dict):
    """
    Save current options volume to history
    
    Args:
        symbol: Stock symbol
        volume_data: Dict with 'call_volume', 'put_volume', 'total_volume'
    """
    path = get_options_volume_cache_path(symbol)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Load existing or create new
    if os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        df = pd.DataFrame()
    
    # Add new row
    new_row = pd.DataFrame([volume_data], index=[datetime.now()])
    df = pd.concat([df, new_row])
    
    # Keep only last 30 days
    cutoff_date = datetime.now() - timedelta(days=30)
    df = df[df.index > cutoff_date]
    
    df.to_csv(path)

def calculate_volume_metrics(options_df: pd.DataFrame) -> Dict:
    """
    Calculate volume metrics from options DataFrame
    
    Returns:
        Dict with total_volume, avg_volume, top_strikes info
    """
    if options_df.empty:
        return {
            'total_volume': 0,
            'total_open_interest': 0,
            'avg_volume': 0,
            'top_strikes': []
        }
    
    # Calculate totals
    total_volume = options_df['volume'].sum() if 'volume' in options_df.columns else 0
    total_oi = options_df['openInterest'].sum() if 'openInterest' in options_df.columns else 0
    
    # Find top strikes by volume
    top_strikes = []
    if 'volume' in options_df.columns and 'strike' in options_df.columns:
        top_5 = options_df.nlargest(5, 'volume')[['strike', 'volume', 'openInterest', 'expiry']]
        top_strikes = top_5.to_dict('records')
    
    return {
        'total_volume': total_volume,
        'total_open_interest': total_oi,
        'avg_volume': total_volume / len(options_df) if len(options_df) > 0 else 0,
        'top_strikes': top_strikes
    }

def detect_unusual_activity(symbol: str, current_metrics: Dict, threshold: float = 2.0) -> Dict:
    """
    Detect unusual options activity based on historical averages
    
    Args:
        symbol: Stock symbol
        current_metrics: Current volume metrics
        threshold: Multiplier for unusual activity (default 2.0 = 2x normal)
        
    Returns:
        Dict with detection results
    """
    # Get historical data
    history = get_options_volume_history(symbol, days=5)
    
    if history.empty or len(history) < 2:
        return {
            'is_unusual': False,
            'reason': 'Insufficient historical data',
            'current_volume': current_metrics.get('total_volume', 0),
            'avg_volume': 0,
            'ratio': 0
        }
    
    # Calculate average
    avg_volume = history['total_volume'].mean() if 'total_volume' in history.columns else 0
    current_volume = current_metrics.get('total_volume', 0)
    
    if avg_volume > 0:
        ratio = current_volume / avg_volume
        is_unusual = ratio >= threshold
    else:
        ratio = 0
        is_unusual = False
    
    return {
        'is_unusual': is_unusual,
        'reason': f"Volume is {ratio:.1f}x the 5-day average" if is_unusual else "Normal activity",
        'current_volume': current_volume,
        'avg_volume': avg_volume,
        'ratio': ratio,
        'threshold': threshold
    }