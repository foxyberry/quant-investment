# quant-investment

Quantitative investment strategy development and backtesting project

[한국어 README](README_KO.md)

## Stack
- **Backtesting.py** - Strategy backtesting framework
- **yfinance** - Stock data collection
- **pykrx** - Korean stock data (KOSPI/KOSDAQ)
- **pandas/numpy** - Data processing
- **matplotlib/seaborn** - Visualization

## Installation

```bash
pip install -r requirements.txt
```

### Version Check
```bash
pip show yfinance
# Name: yfinance
# Version: 0.2.63
```

## Project Structure

```
quant-investment/
├── run.py                        # Main entry point (strategy orchestrator)
│
├── config/                       # Configuration files
│   ├── base_config.yaml          # Base settings
│   ├── portfolio.yaml            # Portfolio holdings & sell conditions
│   ├── korean_screening.yaml     # Korean stock screening settings
│   └── screening_criteria.yaml   # Technical screening criteria
│
├── engine/                       # Backtesting engine
│   ├── backtesting_engine.py     # Backtesting.py wrapper
│   ├── metrics.py                # Performance metrics (Sharpe, MDD, etc.)
│   └── strategies/               # Trading strategies
│       └── ma_cross.py           # MA crossover strategies
│
├── models/                       # Data models
│   ├── condition.py              # Quant condition schema (17 types)
│   ├── watchlist.py              # Watchlist management
│   └── price_target.py           # Price target settings
│
├── discovery/                    # Stock discovery
│   ├── evaluator.py              # Condition evaluation engine
│   ├── indicators.py             # Technical indicators (RSI, MACD, BB)
│   └── decision.py               # Buy decision logic (scoring)
│
├── portfolio/                    # Portfolio management
│   ├── holdings.py               # Holdings CRUD
│   ├── monitor.py                # Price monitoring (polling)
│   ├── trigger.py                # Condition trigger detection
│   ├── conditions.py             # Trading condition IoC pattern
│   ├── quantity.py               # Buy/sell quantity calculation
│   ├── executor.py               # Order execution (Paper/Live)
│   ├── risk.py                   # Risk management rules
│   └── notifier.py               # Notification (Telegram/Slack)
│
├── scripts/                      # Executable scripts
│   ├── backtesting/              # Backtesting scripts
│   │   └── run_backtest.py       # CLI backtest runner
│   ├── screening/                # Stock screening scripts
│   │   ├── korean_daily_report.py    # Daily report with golden/death cross
│   │   ├── korean_crossover.py       # MA crossover detection
│   │   ├── korean_ma_below.py        # Stocks below MA
│   │   ├── korean_ma_touch.py        # Stocks touching MA
│   │   └── tech_breakout.py          # Technical breakout screener
│   └── live/                     # Live trading/bots
│       ├── portfolio_sell_checker.py     # Portfolio sell signal checker
│       ├── options_tracker.py            # Options volume tracker bot
│       └── global_dual_momentum_2025.py  # Dual momentum strategy
│
├── screener/                     # Stock screening library
│   ├── basic_filter.py           # Basic info filter (price, volume, market cap)
│   ├── technical_filter.py       # Technical indicator filter
│   ├── external_filter.py        # External data filter
│   ├── portfolio_manager.py      # Portfolio management
│   └── korean/                   # Korean stock screener
│       ├── kospi_fetcher.py      # KOSPI/KOSDAQ data fetcher
│       └── ma_screener.py        # Moving average screener
│
├── utils/                        # Utilities
│   ├── fetch.py                  # Stock data fetching (yfinance)
│   ├── options_fetch.py          # Options data fetching
│   ├── config_manager.py         # Configuration file manager
│   └── timezone_utils.py         # Timezone utilities
│
├── data/                         # Data storage & cache
├── logs/                         # Log files
├── reports/                      # Generated reports
└── docs/                         # Documentation
    ├── examples/                 # Examples and templates
    ├── ko/                       # Korean documentation
    └── works/                    # Work plan documents
```

## Quick Start

### 1. Run Strategy
```bash
# Activate virtual environment
source venv/bin/activate

# Run strategy orchestrator
python run.py
```

### 2. Run Options Tracker Bot
```bash
# One-time check
python scripts/live/options_tracker.py --once

# Continuous monitoring (every 60 seconds)
python scripts/live/options_tracker.py
```

See [docs/OPTIONS_TRACKER_README.md](docs/OPTIONS_TRACKER_README.md) for details

### 3. Check Portfolio Sell Signals
```bash
# Add holdings to config/portfolio.yaml first
python scripts/live/portfolio_sell_checker.py
```

### 4. Stock Discovery (Buy Signal Analysis)
```python
from discovery import analyze_buy_signal

decision = analyze_buy_signal("005930.KS")
print(decision.summary())
# Recommendation: HOLD, Score: 54/100, Risk: HIGH
```

### 5. Portfolio Management & Paper Trading
```python
from portfolio import Portfolio, OrderExecutor, Order

# Manage holdings
portfolio = Portfolio()
portfolio.add("005930.KS", quantity=10, avg_price=70000)

# Paper trading
executor = OrderExecutor(dry_run=True)
order = Order("005930.KS", "SELL", quantity=5)
result = executor.execute(order, market_price=80000)
print(f"Simulated P&L: {result.fill_price * result.fill_quantity:,.0f}")
```

### 6. Run Backtest
```bash
# Basic backtest (Korean stock) - uses SMA(10,20) by default
python scripts/backtesting/run_backtest.py --ticker 005930.KS --period 1y

# US stock with EMA strategy
python scripts/backtesting/run_backtest.py --ticker AAPL --strategy ema

# Custom MA periods
python scripts/backtesting/run_backtest.py --ticker AAPL --strategy sma --n1 5 --n2 30

# Parameter optimization
python scripts/backtesting/run_backtest.py --ticker 005930.KS --optimize
```

**Available strategies:**
| Strategy | Description | Default params |
|----------|-------------|----------------|
| `sma` | Simple MA crossover (default) | n1=10, n2=20 |
| `ema` | Exponential MA crossover | n1=12, n2=26 |
| `ma_touch` | MA touch & bounce | ma_period=20 |

### 7. Create New Strategy

1. Copy template
```bash
cp docs/examples/screening_template.py scripts/screening/my_strategy.py
```

2. Edit strategy
```python
# Edit scripts/screening/my_strategy.py
def run():
    # Write your strategy logic here
    pass
```

3. Run with `run.py`
```bash
python run.py scripts/screening/my_strategy.py
```

## Recent Updates

### Portfolio Monitoring System (2026-01)
- Holdings management with auto avg price calculation
- Price monitoring with polling & callbacks
- Condition trigger detection (price targets, stop loss)
- Trading condition IoC pattern (customizable sell conditions)
- Paper trading executor with virtual balance
- Risk management rules (position limits, daily loss limits)
- Notification system (Telegram, Slack, Console)

### Stock Discovery System (2026-01)
- Quant condition schema with 17 condition types
- Technical indicators (RSI, MACD, Bollinger, MA 5/20/60/120/240)
- Buy decision logic with scoring (STRONG_BUY/BUY/HOLD/WAIT)
- Watchlist & price target management

### Backtesting Framework (2026-01)
- Backtesting.py integration for strategy testing
- MA crossover strategies (SMA, EMA)
- Performance metrics: Sharpe, Sortino, MDD, Win Rate, CAGR
- Run: `python scripts/backtesting/run_backtest.py --ticker AAPL`

### Portfolio Sell Alert (2026-01)
- Portfolio holdings management via `config/portfolio.yaml`
- Sell signal detection (stop loss, take profit, trailing stop)
- Technical sell signals (MA20 breakdown, death cross)
- Run: `python scripts/live/portfolio_sell_checker.py`

### Korean Daily Report (2026-01)
- Golden/death cross detection for KOSPI stocks
- Auto-saved daily reports to `reports/` folder

### Project Cleanup (2026-01)
- Removed backtrader dependency (unused)
- Removed legacy code (`lib/`, `scripts/legacy/`, `visualizer/`)
- Simplified project structure

### Options Tracker Bot (2025-01)
- Detects unusual options activity for NVDA, AAPL, TSLA, AMZN
- Alerts when volume is 2-3x above 5-day average

## Documentation

- [Korean MA Screener](docs/KOREAN_MA_SCREENER.md)
- [Market Calendar](docs/MARKET_CALENDAR_README.md)
- [Options Tracker Bot](docs/OPTIONS_TRACKER_README.md)
- [Code Quality Report](docs/code_quality_report.md)

## Contributing

Add new strategies under `scripts/` in the appropriate subfolder:
- `backtesting/` - Backtesting scripts
- `screening/` - Stock screening
- `live/` - Live trading/bots

## License

MIT
