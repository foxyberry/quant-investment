import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


def visualize_breakout_analysis(symbol: str, breakout_df: pd.DataFrame, lookback_days: int = 20):
    """
    Visualize breakout analysis for a given stock using pre-calculated breakout data
    
    Args:
        symbol: Stock symbol
        breakout_df: DataFrame containing breakout analysis results
        lookback_days: Number of days to look back for analysis
    """
    # Get historical data
    history_dir = "data/history"
    file_path = os.path.join(history_dir, f"{symbol}_history.csv")
    
    if os.path.exists(file_path):
        data = pd.read_csv(file_path, index_col=0, parse_dates=True)
    else:
        end_date = datetime.now(tz=timezone.utc)
        start_date = end_date - timedelta(days=lookback_days * 2)
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date)
    
    if data.empty:
        print(f"No data available for {symbol}")
        return
    
    # Get breakout data from breakout_df
    symbol_data = breakout_df[breakout_df['symbol'] == symbol].iloc[0]
    bottom_price = symbol_data['bottom_price']
    breakout_price = symbol_data['breakout_price']
    stop_loss_price = symbol_data['stop_loss_price']
    bottom_date = pd.to_datetime(symbol_data['bottom_date'])
    
    # Create the plot
    plt.figure(figsize=(15, 8))
    sns.set_style("whitegrid")
    
    # Plot price action
    plt.plot(data.index, data['Close'], label='Close Price', color='blue', linewidth=2)
    
    # Plot bottom and breakout levels
    plt.axhline(y=bottom_price, color='red', linestyle='--', label='Bottom Price')
    plt.axhline(y=breakout_price, color='green', linestyle='--', label='Breakout Level (5%)')
    plt.axhline(y=stop_loss_price, color='blue', linestyle='--', label='Stop Loss Price')
    
    # Mark the bottom point
    plt.scatter(bottom_date, bottom_price, color='red', s=100, zorder=5, label='Bottom Point')
    
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
    breakout_status = "BREAKOUT" if current_price >= breakout_price else "NO BREAKOUT"
    price_from_bottom_pct = ((current_price - bottom_price) / bottom_price) * 100
    
    info_text = (
        f'Current Price: ${current_price:.2f}\n'
        f'Bottom Price: ${bottom_price:.2f}\n'
        f'Bottom Date: {bottom_date.strftime("%Y-%m-%d")}\n'
        f'Price from Bottom: {price_from_bottom_pct:.1f}%\n'
        f'Breakout Status: {breakout_status}'
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
        symbol = row['symbol']
        print(f"\nAnalyzing {symbol}...")
        visualize_breakout_analysis(symbol, breakout_df)
        print("\n" + "="*50 + "\n") 
