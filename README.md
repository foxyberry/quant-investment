# quant-investment

Quantitative investment strategy development and backtesting project

[한국어 README](README_KO.md)

## Stack
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
├── scripts/                      # Executable scripts
│   ├── screening/                # Stock screening scripts
│   └── live/                     # Live trading/bots
│       ├── options_tracker.py    # Options volume tracker bot
│       ├── portfolio_sell_checker.py  # Portfolio sell signal checker
│       └── global_dual_momentum_2025.py  # Dual momentum strategy
│
├── screener/                     # Stock screening library
│   ├── basic_filter.py           # Basic info filter
│   ├── technical_filter.py       # Technical indicator filter
│   ├── portfolio_manager.py      # Portfolio management
│   └── korean/                   # Korean stock screener
│
├── utils/                        # Utilities
│   ├── fetch.py                  # Stock data fetching
│   ├── options_fetch.py          # Options data fetching
│   └── ...
│
├── config/                       # Configuration files
├── data/                         # Data storage
├── logs/                         # Log files
└── docs/                         # Documentation
    └── examples/                 # Examples and templates
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

### 3. Create New Strategy

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

### Options Tracker Bot (2025-01)
- Detects unusual options activity for NVDA, AAPL, TSLA, AMZN
- Alerts when volume is 2-3x above 5-day average
- Automatic data caching and history analysis

### Global Dual Momentum (2025-01)
- Multi-asset allocation strategy (stocks/bonds/cash)
- Momentum-based asset switching

### Directory Structure Cleanup (2025-01)
- `strategies/` → `engine/` (renamed to reflect role)
- `my_strategies/` → `scripts/` (executable scripts)
- `strategy_templates/` → `docs/examples/` (consolidated templates)
- Enhanced documentation

## Documentation

- [Market Calendar](docs/MARKET_CALENDAR_README.md)
- [Options Tracker Bot](docs/OPTIONS_TRACKER_README.md)
- [Code Quality Report](docs/code_quality_report.md)

## Contributing

Add new strategies under `scripts/` in the appropriate subfolder:
- `screening/` - Stock screening
- `live/` - Live trading/bots

## License

MIT
