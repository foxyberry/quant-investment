import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timezone, timedelta
from typing import Union, Dict, Any
import logging
from utils.fetch import get_historical_data

logger = logging.getLogger(__name__)

def visualize_breakout_analysis(symbol: str, symbol_data: Union[pd.Series, Dict[str, Any]], lookback_days: int = 20):
    """
    Visualize breakout analysis for a given stock using pre-calculated breakout data
    
    Args:
        symbol: Stock symbol
        symbol_data: DataFrame row or dictionary containing breakout analysis results
        lookback_days: Number of days to look back for analysis
    """
    try:
        # Get historical data for visualization
        end_date = datetime.now(tz=timezone.utc)
        start_date = end_date - timedelta(days=lookback_days * 2)
        data = get_historical_data(symbol, start_date, end_date)
        
        if data is None or data.empty:
            logger.warning(f"No historical data available for {symbol}")
            return
        
        # Extract breakout data from symbol_data
        if isinstance(symbol_data, pd.Series):
            # Handle DataFrame row
            bottom_price = symbol_data['bottom_price']
            breakout_price = symbol_data['breakout_price']
            stop_loss_price = symbol_data['stop_loss_price']
            bottom_date = pd.to_datetime(symbol_data['bottom_date'])
            breakout_status = symbol_data['breakout_status']
            first_breakout_date = symbol_data.get('first_breakout_date')
            days_since_first_breakout = symbol_data.get('days_since_first_breakout')
        else:
            # Handle dictionary
            bottom_price = symbol_data['bottom_price']
            breakout_price = symbol_data['breakout_price']
            stop_loss_price = symbol_data['stop_loss_price']
            bottom_date = pd.to_datetime(symbol_data['bottom_date'])
            breakout_status = symbol_data['breakout_status']
            first_breakout_date = symbol_data.get('first_breakout_date')
            days_since_first_breakout = symbol_data.get('days_since_first_breakout')

        # Handle case where first_breakout_date might be None
        if pd.isna(first_breakout_date) or first_breakout_date is None:
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
        
        # Plot key levels
        plt.axhline(y=bottom_price, color='red', linestyle='--', alpha=0.7, label=f'Bottom Price (${bottom_price:.2f})')
        plt.axhline(y=breakout_price, color='green', linestyle='--', alpha=0.7, label=f'Breakout Level (${breakout_price:.2f})')
        plt.axhline(y=stop_loss_price, color='orange', linestyle='--', alpha=0.7, label=f'Stop Loss (${stop_loss_price:.2f})')
        
        # Mark the bottom point
        plt.scatter(bottom_date, bottom_price, color='red', s=100, zorder=5, label='Bottom Point')
        
        # Mark first breakout point if it exists
        if not pd.isna(first_breakout_date) and first_breakout_date is not None:
            plt.scatter(pd.to_datetime(first_breakout_date), breakout_price, 
                       color='green', s=100, zorder=5, label='First Breakout')
        
        # Add volume bars at the bottom
        ax2 = plt.twinx()
        ax2.bar(data.index, data['Volume'], alpha=0.3, color='gray', label='Volume')
        ax2.set_ylabel('Volume', fontsize=12)
        
        # Customize the plot
        plt.title(f'{symbol} Breakout Analysis - Status: {breakout_status}', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Price ($)', fontsize=12)
        
        # Add legend
        lines1, labels1 = plt.gca().get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
        
        # Show current price and analysis info
        current_price = data['Close'].iloc[-1]
        price_change_from_bottom = ((current_price - bottom_price) / bottom_price) * 100
        price_distance_from_breakout = ((current_price - breakout_price) / breakout_price) * 100
        
        info_text = (
            f'Current Price: ${current_price:.2f}\n'
            f'Change from Bottom: {price_change_from_bottom:.1f}%\n'
            f'Distance from Breakout: {price_distance_from_breakout:.1f}%\n'
            f'Bottom Date: {bottom_date.strftime("%Y-%m-%d")}\n'
            f'First Breakout: {first_breakout_date_str}\n'
            f'Days Since Breakout: {days_since_str}'
        )
        
        # Color the info box based on breakout status
        box_color = {
            'FIRST BREAKOUT': 'lightgreen',
            'ALREADY UP': 'lightblue', 
            'DOWN AGAIN AFTER BREAKOUT': 'lightyellow'
        }.get(breakout_status, 'white')
        
        plt.text(0.02, 0.98, info_text,
                 transform=plt.gca().transAxes, fontsize=11,
                 bbox=dict(facecolor=box_color, alpha=0.8, boxstyle='round,pad=0.5'),
                 verticalalignment='top')
        
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        logger.error(f"Error visualizing {symbol}: {e}")

def visualize_all_breakouts(breakout_df: pd.DataFrame, max_plots: int = 10):
    """
    Visualize breakout analysis for symbols in the breakout DataFrame
    
    Args:
        breakout_df: DataFrame containing breakout analysis results
        max_plots: Maximum number of plots to generate (to avoid overwhelming output)
    """
    if breakout_df.empty:
        logger.warning("No breakout data to visualize")
        return
    
    logger.info(f"Generating visualizations for {min(len(breakout_df), max_plots)} symbols...")
    
    # Sort by breakout status to prioritize fresh breakouts
    priority_order = ['FIRST BREAKOUT', 'ALREADY UP', 'DOWN AGAIN AFTER BREAKOUT']
    if 'breakout_status' in breakout_df.columns:
        breakout_df_sorted = breakout_df.copy()
        breakout_df_sorted['status_priority'] = breakout_df_sorted['breakout_status'].map(
            {status: i for i, status in enumerate(priority_order)}
        ).fillna(99)
        breakout_df_sorted = breakout_df_sorted.sort_values('status_priority')
    else:
        breakout_df_sorted = breakout_df
    
    plot_count = 0
    for _, row in breakout_df_sorted.iterrows():
        if plot_count >= max_plots:
            logger.info(f"Reached maximum plot limit ({max_plots}). Stopping visualization.")
            break
            
        try:
            visualize_breakout_analysis(row['symbol'], row)
            plot_count += 1
        except Exception as e:
            logger.error(f"Failed to visualize {row.get('symbol', 'unknown')}: {e}")
            continue 
