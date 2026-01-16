# Backtrader Integration for Quant Investment

This document explains how to use the backtrader library integration with your existing quant investment system.

## Overview

The backtrader integration provides a comprehensive backtesting framework that:
- Implements your breakout strategy using backtrader's powerful engine
- Integrates seamlessly with your existing screening and technical analysis
- Provides detailed performance metrics and visualizations
- Supports multiple strategy variants

## Installation

1. Install backtrader:
```bash
pip install backtrader>=1.9.76
```

2. All other dependencies are already in your `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Files Structure

```
engine/
├── backtrader_strategy.py      # Backtrader strategy implementations
├── backtrader_engine.py        # Backtrader engine wrapper
└── bottom_breakout.py          # Your existing strategy

scripts/
├── screening/                  # Screening scripts
└── backtesting/                # Backtesting scripts

docs/examples/
├── backtesting_template.py     # Template for new backtests
└── simple_backtrader_example.py # Simple example
```

## Strategy Classes

### 1. BreakoutStrategy
Basic breakout strategy that implements your existing logic:
- Identifies bottom price in lookback period
- Buys when price breaks above breakout level (5% above bottom)
- Sells when price hits stop loss (5% below bottom)

### 2. BreakoutStrategyWithVolume
Enhanced version with volume confirmation:
- Same breakout logic as basic strategy
- Additional volume confirmation requirement
- Only buys when volume is 1.5x above 10-day average

## Usage Examples

### Quick Start - Simple Example

```bash
python simple_backtrader_example.py
```

This will:
- Test 3 popular stocks (AAPL, MSFT, GOOGL)
- Run backtests for the last 6 months
- Generate interactive plots for each stock
- Compare different strategy variants

### Full Integration - Main Script

```bash
python backtrader_main.py
```

This will:
- Use your existing screening system to filter S&P 500 stocks
- Apply your basic filters (price, volume, market cap)
- Run backtests on filtered stocks
- Generate comprehensive reports and visualizations
- Save results to CSV files

### Custom Backtesting

```python
from engine.backtrader_engine import BacktraderEngine
from engine.backtrader_strategy import BreakoutStrategy
from screener.technical_criteria import TechnicalCriteria
from datetime import datetime, timedelta

# Initialize engine
backtester = BacktraderEngine(initial_capital=100000, commission=0.001)

# Set parameters
technical_criteria = TechnicalCriteria(
    lookback_days=20,
    breakout_threshold=1.05,
    stop_loss_threshold=0.98,
    volume_threshold=1.5
)

# Run backtest
result = backtester.run_backtest(
    symbol='AAPL',
    start_date=datetime.now() - timedelta(days=365),
    end_date=datetime.now(),
    technical_criteria=technical_criteria,
    strategy_class=BreakoutStrategy,
    plot_results=True
)

# Print results
print(f"Total Return: {result['total_return']:.2%}")
print(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {result['max_drawdown']:.2%}")
```

## Performance Metrics

The backtrader integration provides comprehensive performance metrics:

### Returns
- **Total Return**: Overall strategy performance
- **Buy & Hold Return**: Benchmark comparison
- **Sharpe Ratio**: Risk-adjusted returns

### Risk Metrics
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Volatility**: Standard deviation of returns

### Trading Metrics
- **Total Trades**: Number of buy/sell transactions
- **Win Rate**: Percentage of profitable trades
- **Average Trade**: Average profit/loss per trade

## Visualization Features

### Interactive Charts
- Candlestick charts with buy/sell signals
- Portfolio value over time
- Drawdown analysis
- Volume analysis

### Performance Reports
- Strategy comparison tables
- Risk metrics summary
- Trade analysis breakdown

## Integration with Existing System

The backtrader integration works seamlessly with your existing code:

1. **Screening**: Uses your `BasicInfoScreener` to filter stocks
2. **Technical Analysis**: Uses your `TechnicalCriteria` parameters
3. **Data Fetching**: Uses your existing `get_historical_data` function
4. **Configuration**: Uses your `ConfigManager` for parameters

## Configuration

All parameters are configurable through your existing YAML files:

```yaml
# config/screening_criteria.yaml
technical_analysis:
  lookback_days: 20
  volume_threshold: 1.5
  breakout_threshold: 1.05
  stop_loss_threshold: 0.95
```

## Advanced Features

### Strategy Comparison
Compare different strategy variants:
```python
comparison = backtester.compare_strategies(
    symbol='AAPL',
    start_date=start_date,
    end_date=end_date,
    technical_criteria=technical_criteria
)
```

### Batch Backtesting
Test multiple stocks efficiently:
```python
results = backtester.batch_backtest(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    start_date=start_date,
    end_date=end_date,
    technical_criteria=technical_criteria
)
```

### Custom Strategy Development
Create your own strategies by inheriting from `bt.Strategy`:
```python
class MyCustomStrategy(bt.Strategy):
    def __init__(self):
        # Your custom indicators
        pass
    
    def next(self):
        # Your custom logic
        pass
```

## Troubleshooting

### Common Issues

1. **Data Format**: Ensure your data has required columns (Open, High, Low, Close, Volume)
2. **Date Range**: Make sure you have enough historical data for your lookback period
3. **Memory**: Large datasets may require more memory; consider reducing the date range

### Error Messages

- `Missing required column`: Check your data format
- `Not enough data`: Increase your date range or reduce lookback period
- `Strategy failed`: Check your strategy logic and parameters

## Performance Tips

1. **Data Caching**: Your existing caching system works with backtrader
2. **Parallel Processing**: Consider running multiple backtests in parallel
3. **Memory Management**: Close plots when not needed to free memory

## Next Steps

1. Run the simple example to get familiar with the system
2. Try the main script with your filtered stocks
3. Experiment with different parameters
4. Develop custom strategies based on your research
5. Integrate with your live trading system

## Support

For issues or questions:
1. Check the backtrader documentation: https://www.backtrader.com/
2. Review your strategy logic and parameters
3. Test with simple examples first
4. Use the logging system for debugging 