#!/usr/bin/env python3
"""
Global Stock Dual Momentum Strategy for 2025
Based on Gary Antonacci's dual momentum approach

Strategy:
1. Relative Momentum: Select highest 6-month return among SPY, VEA, VWO
2. Absolute Momentum: If selected asset's 6-month return > 6-month T-Bill return, 
   invest 100% in that asset; otherwise invest 100% in BIL
3. Rebalance monthly using month-end prices
4. Analysis period: 2025-01-01 to 2025-12-31

Requirements: yfinance, pandas, numpy
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class GlobalDualMomentumStrategy:
    """
    Implementation of Global Stock Dual Momentum Strategy
    """
    
    def __init__(self):
        self.tickers = {
            'SPY': 'SPDR S&P 500 ETF Trust',
            'VEA': 'Vanguard FTSE Developed Markets ETF',  
            'VWO': 'Vanguard FTSE Emerging Markets ETF',
            'BIL': 'SPDR Bloomberg 1-3 Month T-Bill ETF',
            '^IRX': '13-Week Treasury Bill Yield'
        }
        
        self.risky_assets = ['SPY', 'VEA', 'VWO']
        self.safe_asset = 'BIL'
        self.tbill_ticker = '^IRX'
        
        # Strategy parameters
        self.lookback_months = 6
        self.rebalance_frequency = 'M'  # Monthly
        
        # Data storage
        self.price_data = {}
        self.monthly_prices = {}
        self.signals = []
        self.portfolio_values = []
        
    def fetch_data(self, start_date='2024-06-01', end_date='2025-12-31'):
        """
        Fetch price data for all tickers
        Start from mid-2024 to ensure 6-month lookback for January 2025
        """
        print("Fetching data for all tickers...")
        
        for ticker in self.tickers.keys():
            try:
                print(f"  Downloading {ticker} ({self.tickers[ticker]})...")
                
                # Download data for single ticker
                yf_ticker = yf.Ticker(ticker)
                data = yf_ticker.history(start=start_date, end=end_date)
                
                if data.empty:
                    raise ValueError(f"No data received for {ticker}")
                
                # For T-Bill yield, use Close price as yield percentage
                if ticker == '^IRX':
                    # T-Bill yield is already in percentage format
                    self.price_data[ticker] = data['Close'].dropna()
                else:
                    # For ETFs, use Close prices (yfinance history already adjusts for splits/dividends)
                    self.price_data[ticker] = data['Close'].dropna()
                
                print(f"    ✅ {ticker}: {len(self.price_data[ticker])} days of data")
                print(f"       Date range: {self.price_data[ticker].index[0].date()} to {self.price_data[ticker].index[-1].date()}")
                
            except Exception as e:
                print(f"    ❌ Error downloading {ticker}: {e}")
                raise
        
        print(f"\n✅ Data fetching completed for {len(self.price_data)} tickers")
        
    def extract_month_end_prices(self):
        """
        Extract month-end prices for all assets
        """
        print("\nExtracting month-end prices...")
        
        for ticker in self.tickers.keys():
            if ticker not in self.price_data:
                continue
                
            # Convert to monthly data (last business day of month)
            if ticker == '^IRX':
                # For T-Bill yield, we'll take the last available yield for each month
                monthly_data = self.price_data[ticker].resample('M').last()
            else:
                # For price data, use last trading day of month
                monthly_data = self.price_data[ticker].resample('M').last()
            
            self.monthly_prices[ticker] = monthly_data.dropna()
            
            print(f"  {ticker}: {len(self.monthly_prices[ticker])} month-end observations")
            
        print("✅ Month-end price extraction completed")
        
    def calculate_momentum_returns(self, prices, months_back=6):
        """
        Calculate rolling momentum returns over specified months
        """
        if len(prices) < months_back:
            return pd.Series(index=prices.index, dtype=float)
            
        # Calculate percentage returns over the lookback period
        momentum_returns = (prices / prices.shift(months_back) - 1) * 100
        
        return momentum_returns.dropna()
    
    def calculate_tbill_cumulative_return(self, tbill_yields, months_back=6):
        """
        Calculate cumulative T-Bill return over specified months
        T-Bill yields are annualized, so we need to convert to monthly and compound
        """
        if len(tbill_yields) < months_back:
            return pd.Series(index=tbill_yields.index, dtype=float)
        
        # Convert annual yield to monthly yield (divide by 12)
        monthly_yields = tbill_yields / 12
        
        # Calculate cumulative return over lookback period
        cumulative_returns = pd.Series(index=tbill_yields.index, dtype=float)
        
        for i in range(months_back, len(tbill_yields)):
            # Get the last 6 months of yields and compound them
            period_yields = monthly_yields.iloc[i-months_back:i]
            # Compound the monthly yields: (1+r1)*(1+r2)*...*(1+r6) - 1
            cumulative_return = ((1 + period_yields/100).prod() - 1) * 100
            cumulative_returns.iloc[i] = cumulative_return
            
        return cumulative_returns.dropna()
    
    def generate_signals(self):
        """
        Generate monthly allocation signals for 2025
        """
        print("\nGenerating allocation signals for 2025...")
        
        # Calculate momentum returns for risky assets
        momentum_data = {}
        for ticker in self.risky_assets:
            momentum_data[ticker] = self.calculate_momentum_returns(
                self.monthly_prices[ticker], self.lookback_months
            )
        
        # Calculate T-Bill cumulative returns
        tbill_returns = self.calculate_tbill_cumulative_return(
            self.monthly_prices[self.tbill_ticker], self.lookback_months
        )
        
        # Create DataFrame for easier analysis
        momentum_df = pd.DataFrame(momentum_data)
        
        # Filter for 2025 dates only - handle timezone-aware comparison
        start_2025 = pd.Timestamp('2025-01-01')
        end_2025 = pd.Timestamp('2025-12-31')
        
        # Make timestamps timezone-aware to match the data
        if momentum_df.index.tz is not None:
            start_2025 = start_2025.tz_localize(momentum_df.index.tz)
            end_2025 = end_2025.tz_localize(momentum_df.index.tz)
        
        momentum_df_2025 = momentum_df[(momentum_df.index >= start_2025) & 
                                       (momentum_df.index <= end_2025)]
        
        # Handle T-Bill returns timezone similarly
        if tbill_returns.index.tz is not None:
            if start_2025.tz is None:
                start_2025 = start_2025.tz_localize(tbill_returns.index.tz)
                end_2025 = end_2025.tz_localize(tbill_returns.index.tz)
            else:
                start_2025 = start_2025.tz_convert(tbill_returns.index.tz)
                end_2025 = end_2025.tz_convert(tbill_returns.index.tz)
        
        tbill_returns_2025 = tbill_returns[(tbill_returns.index >= start_2025) & 
                                           (tbill_returns.index <= end_2025)]
        
        # Generate signals for each month in 2025
        for date in momentum_df_2025.index:
            try:
                # Step 1: Relative Momentum - find asset with highest 6-month return
                monthly_returns = momentum_df_2025.loc[date]
                best_asset = monthly_returns.idxmax()
                best_return = monthly_returns[best_asset]
                
                # Step 2: Absolute Momentum - compare to T-Bill return
                tbill_return = tbill_returns_2025.loc[date] if date in tbill_returns_2025.index else 0
                
                # Decision logic
                if best_return > tbill_return:
                    # Invest in the best performing risky asset
                    selected_asset = best_asset
                    allocation_reason = f"Relative winner with {best_return:.2f}% > T-Bill {tbill_return:.2f}%"
                else:
                    # Invest in safe asset (BIL)
                    selected_asset = self.safe_asset
                    allocation_reason = f"Best risky asset {best_return:.2f}% <= T-Bill {tbill_return:.2f}%"
                
                # Store signal
                signal = {
                    'date': date,
                    'selected_asset': selected_asset,
                    'spy_return': monthly_returns['SPY'],
                    'vea_return': monthly_returns['VEA'], 
                    'vwo_return': monthly_returns['VWO'],
                    'best_asset': best_asset,
                    'best_return': best_return,
                    'tbill_return': tbill_return,
                    'reason': allocation_reason
                }
                
                self.signals.append(signal)
                
                print(f"  {date.strftime('%Y-%m')}: {selected_asset} - {allocation_reason}")
                
            except Exception as e:
                print(f"  ❌ Error processing {date}: {e}")
                continue
        
        print(f"\n✅ Generated {len(self.signals)} monthly signals for 2025")
        
    def calculate_portfolio_performance(self):
        """
        Calculate portfolio performance for 2025
        """
        print("\nCalculating portfolio performance...")
        
        if not self.signals:
            print("❌ No signals available for performance calculation")
            return
        
        portfolio_values = [100]  # Start with $100
        monthly_returns = []
        
        for i, signal in enumerate(self.signals):
            current_date = signal['date']
            selected_asset = signal['selected_asset']
            
            # Get the monthly return for the selected asset
            if i == 0:
                # For first month, we need the return from previous month to current month
                prev_date = current_date - pd.DateOffset(months=1)
                if (selected_asset in self.monthly_prices and 
                    prev_date in self.monthly_prices[selected_asset].index and
                    current_date in self.monthly_prices[selected_asset].index):
                    
                    prev_price = self.monthly_prices[selected_asset][prev_date]
                    curr_price = self.monthly_prices[selected_asset][current_date]
                    monthly_return = (curr_price / prev_price - 1)
                else:
                    monthly_return = 0
            else:
                # For subsequent months, use the return from previous signal date to current
                prev_date = self.signals[i-1]['date']
                if (selected_asset in self.monthly_prices and 
                    prev_date in self.monthly_prices[selected_asset].index and
                    current_date in self.monthly_prices[selected_asset].index):
                    
                    prev_price = self.monthly_prices[selected_asset][prev_date]
                    curr_price = self.monthly_prices[selected_asset][current_date]
                    monthly_return = (curr_price / prev_price - 1)
                else:
                    monthly_return = 0
            
            # Update portfolio value
            new_value = portfolio_values[-1] * (1 + monthly_return)
            portfolio_values.append(new_value)
            monthly_returns.append(monthly_return)
            
        self.portfolio_values = portfolio_values[1:]  # Remove initial value
        self.monthly_returns = monthly_returns
        
        print(f"✅ Portfolio performance calculated for {len(self.portfolio_values)} periods")
        
    def calculate_performance_metrics(self):
        """
        Calculate performance metrics: CAGR, MDD, Volatility, Sharpe Ratio
        """
        if not self.portfolio_values or not self.monthly_returns:
            print("❌ No portfolio data available for metrics calculation")
            return {}
        
        print("\nCalculating performance metrics...")
        
        # Convert to numpy arrays for easier calculation
        returns = np.array(self.monthly_returns)
        portfolio_values = np.array(self.portfolio_values)
        
        # CAGR (annualized return)
        total_return = (portfolio_values[-1] / 100 - 1)  # Starting value was 100
        num_years = len(returns) / 12  # Convert months to years
        cagr = (1 + total_return) ** (1/num_years) - 1 if num_years > 0 else 0
        
        # Maximum Drawdown
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        max_drawdown = np.min(drawdown)
        
        # Annualized Volatility
        monthly_vol = np.std(returns, ddof=1)
        annual_vol = monthly_vol * np.sqrt(12)
        
        # Sharpe Ratio (using average T-Bill return as risk-free rate)
        avg_tbill_annual = np.mean([s['tbill_return'] for s in self.signals]) * 2  # Approximate annualization
        risk_free_rate = avg_tbill_annual / 100 if avg_tbill_annual else 0.02  # Default 2% if no T-Bill data
        
        excess_return = cagr - risk_free_rate
        sharpe_ratio = excess_return / annual_vol if annual_vol > 0 else 0
        
        metrics = {
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe_ratio,
            'total_return_2025': total_return,
            'risk_free_rate': risk_free_rate
        }
        
        print("✅ Performance metrics calculated")
        return metrics
        
    def display_results(self):
        """
        Display comprehensive results
        """
        print("\n" + "="*80)
        print("          GLOBAL STOCK DUAL MOMENTUM STRATEGY - 2025 RESULTS")
        print("="*80)
        
        # Performance Metrics
        metrics = self.calculate_performance_metrics()
        
        if metrics:
            print(f"\n📊 PERFORMANCE METRICS (2025)")
            print("-" * 40)
            print(f"CAGR:                    {metrics['cagr']:.2%}")
            print(f"Total Return (2025):     {metrics['total_return_2025']:.2%}")
            print(f"Maximum Drawdown:        {metrics['max_drawdown']:.2%}")
            print(f"Annualized Volatility:   {metrics['annual_volatility']:.2%}")
            print(f"Sharpe Ratio:            {metrics['sharpe_ratio']:.3f}")
            print(f"Risk-Free Rate Used:     {metrics['risk_free_rate']:.2%}")
        
        # Monthly Signals
        print(f"\n📅 MONTHLY ALLOCATION SIGNALS (2025)")
        print("-" * 80)
        print(f"{'Month':<8} {'Asset':<6} {'SPY':<8} {'VEA':<8} {'VWO':<8} {'T-Bill':<8} {'Reason'}")
        print("-" * 80)
        
        for signal in self.signals:
            month_str = signal['date'].strftime('%Y-%m')
            asset = signal['selected_asset']
            spy_ret = f"{signal['spy_return']:.1f}%"
            vea_ret = f"{signal['vea_return']:.1f}%"
            vwo_ret = f"{signal['vwo_return']:.1f}%"
            tbill_ret = f"{signal['tbill_return']:.1f}%"
            reason = "Risk On" if asset != 'BIL' else "Risk Off"
            
            print(f"{month_str:<8} {asset:<6} {spy_ret:<8} {vea_ret:<8} {vwo_ret:<8} {tbill_ret:<8} {reason}")
        
        # Asset Allocation Summary
        asset_counts = {}
        for signal in self.signals:
            asset = signal['selected_asset']
            asset_counts[asset] = asset_counts.get(asset, 0) + 1
        
        print(f"\n📋 ALLOCATION SUMMARY (2025)")
        print("-" * 40)
        for asset, count in sorted(asset_counts.items()):
            percentage = (count / len(self.signals)) * 100
            asset_name = self.tickers.get(asset, asset)
            print(f"{asset} ({asset_name:<30}): {count:>2} months ({percentage:>5.1f}%)")
        
        # Cumulative Returns
        if self.portfolio_values:
            print(f"\n📈 CUMULATIVE RETURN PROGRESSION (2025)")
            print("-" * 50)
            for i, signal in enumerate(self.signals):
                month_str = signal['date'].strftime('%Y-%m')
                cum_return = (self.portfolio_values[i] / 100 - 1)
                print(f"{month_str}: {cum_return:>8.2%} (Portfolio Value: ${self.portfolio_values[i]:.2f})")
        
        print("\n" + "="*80)
        
    def run_strategy(self):
        """
        Execute the complete strategy analysis
        """
        print("🚀 Starting Global Stock Dual Momentum Strategy Analysis for 2025")
        print("="*80)
        
        try:
            # Step 1: Fetch data
            self.fetch_data()
            
            # Step 2: Extract month-end prices
            self.extract_month_end_prices()
            
            # Step 3: Generate signals
            self.generate_signals()
            
            # Step 4: Calculate performance
            self.calculate_portfolio_performance()
            
            # Step 5: Display results
            self.display_results()
            
            print("\n✅ Strategy analysis completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Strategy analysis failed: {e}")
            raise


def main():
    """
    Main execution function
    """
    strategy = GlobalDualMomentumStrategy()
    strategy.run_strategy()


if __name__ == "__main__":
    main()