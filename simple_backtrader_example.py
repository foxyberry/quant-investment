#!/usr/bin/env python3
"""
Simple backtrader example for individual stocks
"""

from strategies.backtrader_engine import BacktraderEngine
from strategies.backtrader_strategy import BreakoutStrategy, BreakoutStrategyWithVolume
from screener.technical_criteria import TechnicalCriteria
from datetime import timedelta
from utils.timezone_utils import now, get_valid_backtest_dates, validate_trading_date
import backtrader as bt
import pandas as pd
import yfinance as yf

def main():
    # Get valid trading dates
    print("📅 Getting valid trading dates...")
    start_date, end_date = get_valid_backtest_dates(days_back=180)
    
    print(f"📅 Backtesting period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"📅 Start date is trading day: {start_date.strftime('%A')}")
    print(f"📅 End date is trading day: {end_date.strftime('%A')}")
    
    # Get data
    symbol = "AAPL"
    print(f"📥 Fetching data for {symbol}...")
    
    # Download data
    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start_date, end=end_date)
    
    if data.empty:
        print("❌ No data available")
        return
    
    print(f"✅ Downloaded {len(data)} days of data")
    
    # Create cerebro
    cerebro = bt.Cerebro()
    
    # Add data
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    
    # Add strategy
    cerebro.addstrategy(SimpleStrategy)
    
    # Set initial cash
    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)
    
    # Run backtest
    print(f"💰 Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    print(f"💰 Final Portfolio Value: ${final_value:.2f}")
    
    # Calculate returns
    total_return = (final_value - initial_cash) / initial_cash * 100
    print(f"📈 Total Return: {total_return:.2f}%")
    
    # Plot results
    print("📊 Generating plot...")
    cerebro.plot()

class SimpleStrategy(bt.Strategy):
    def __init__(self):
        self.dataclose = self.datas[0].close
        
    def next(self):
        if not self.position:
            if self.dataclose[0] > self.dataclose[-1]:
                self.buy()
        else:
            if self.dataclose[0] < self.dataclose[-1]:
                self.sell()

if __name__ == "__main__":
    main() 