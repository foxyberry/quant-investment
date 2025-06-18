import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timezone, timedelta
from utils.fetch import get_historical_data


def visualize_breakout_analysis(symbol: str, symbol_data: pd.DataFrame, lookback_days: int = 20):
    """
    Visualize breakout analysis for a given stock using pre-calculated breakout data
    
    Args:
        symbol: Stock symbol
        breakout_df: DataFrame containing breakout analysis results
        lookback_days: Number of days to look back for analysis
    """
    # Get historical data
    
    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=lookback_days * 2)
    data = get_historical_data(symbol, start_date, end_date)
    
    # Get breakout data from breakout_df
    bottom_price = symbol_data['bottom_price']
    breakout_price = symbol_data['breakout_price']
    stop_loss_price = symbol_data['stop_loss_price']
    bottom_date = pd.to_datetime(symbol_data['bottom_date'])
    breakout_status = symbol_data['breakout_status']
    first_breakout_date = symbol_data['first_breakout_date']
    days_since_first_breakout = symbol_data['days_since_first_breakout']

    # Handle case where first_breakout_date might be None
    if pd.isna(first_breakout_date):
        first_breakout_date_str = "No breakout yet"
        days_since_str = "N/A"
    else:
        first_breakout_date_str = pd.to_datetime(first_breakout_date).strftime("%Y-%m-%d")
        days_since_str = str(days_since_first_breakout) if days_since_first_breakout is not None else "N/A"
    
    # Create the plot
    plt.figure(figsize=(15, 8))
    sns.set_style("whitegrid")
    
    # Plot price action
    plt.plot(data.index, data['Close'], label='Close Price', color='blue', linewidth=2)
    
    # Plot bottom and breakout levels
    plt.axhline(y=bottom_price, color='red', linestyle='--', label='Bottom Price')
    plt.axhline(y=breakout_price, color='green', linestyle='--', label='Breakout Level (5%)')
    plt.axhline(y=stop_loss_price, color='blue', linestyle='--', label='Stop Loss Price (5%)')
    
    # Mark the bottom point
    plt.scatter(bottom_date, bottom_price, color='red', s=100, zorder=5, label='Bottom Point')
    
    # Mark first breakout point if it exists
    if not pd.isna(first_breakout_date):
        plt.scatter(pd.to_datetime(first_breakout_date), breakout_price, color='green', s=100, zorder=5, label='First Breakout')
    
    # Add volume bars at the bottom
    ax2 = plt.twinx()
    ax2.bar(data.index, data['Volume'], alpha=0.3, color='gray', label='Volume')
    
    # Customize the plot
    plt.title(f'{symbol} Breakout Analysis', fontsize=15, pad=15)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price ($)', fontsize=12)
    ax2.set_ylabel('Volume', fontsize=12)
    
    # Add legend
    lines1, labels1 = plt.gca().get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    # Show current price and breakout status
    current_price = data['Close'].iloc[-1]
    
    price_from_breakout_price = ((current_price - breakout_price) / bottom_price) * 100
    
    info_text = (
        f'Current Price: ${current_price:.2f}\n'
        f'Bottom Price: ${bottom_price:.2f}\n'
        f'Bottom Date: {bottom_date.strftime("%Y-%m-%d")}\n'
        f'Price from Breakout Price: {price_from_breakout_price:.1f}%\n'
        f'Breakout Status: {breakout_status}\n'
        f'First Breakout Date: {first_breakout_date_str}\n'
        f'Days Since First Breakout: {days_since_str}'
    )
    
    plt.text(0.02, 0.98, info_text,
             transform=plt.gca().transAxes, fontsize=12,
             bbox=dict(facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.show()

def visualize_all_breakouts(breakout_df: pd.DataFrame):
    """
    Visualize breakout analysis for all symbols in the breakout DataFrame
    
    Args:
        breakout_df: DataFrame containing breakout analysis results
    """
    for _, row in breakout_df.iterrows():
        visualize_breakout_analysis(row['symbol'], row)
        print("\n" + "="*50 + "\n") 
