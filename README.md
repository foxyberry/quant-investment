# quant-investment

Quantitative investment strategy development and backtesting project

[한국어 README](README_KO.md)

---

## Daily Routine (Run Every Day)

### 1. Portfolio Sell Signal Check
Check if any holdings should be sold based on stop-loss, take-profit, or technical signals.

```bash
python scripts/live/portfolio_sell_checker.py
```

### 2. Investor Trading Analysis
Check foreign/institutional buying & selling trends.

```bash
# Single stock
python scripts/investor_trading.py 005930

# Top foreign/institutional rankings (recommended)
python scripts/investor_trading.py --top 10

# Institution only
python scripts/investor_trading.py --top-institution 10
```

### 3. Daily Market Report
Golden/death cross detection for KOSPI and US stocks.

```bash
# Korean (KOSPI)
python scripts/screening/korean_daily_report.py

# US (S&P 500)
python scripts/screening/us_daily_report.py
python scripts/screening/us_daily_report.py --sector Technology
```

---

## AI-Powered Stock Analysis (New!)

Semi-automated analysis pipeline using Claude AI:
1. Screen stocks touching 240-day MA
2. Enrich with technical indicators, fundamentals, and news
3. Analyze with Claude for valuation and entry timing
4. Generate report with position sizing recommendations

```bash
# Full analysis (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY="your-api-key"
python scripts/analysis/run_daily_analysis.py

# Single market
python scripts/analysis/run_daily_analysis.py --market KOSPI
python scripts/analysis/run_daily_analysis.py --market SP500

# Data enrichment only (no Claude)
python scripts/analysis/run_daily_analysis.py --enrich-only

# Custom capital for position sizing
python scripts/analysis/run_daily_analysis.py --capital 50000000
```

**Output includes:**
- Valuation score (1-10)
- Risk assessment
- Entry recommendation (BUY/WAIT/AVOID)
- Position sizing with stop-loss

---

## Stock Screening (Finding Opportunities)

### Accumulation Zone Detection
Find stocks in quiet accumulation phase (low volatility + low volume).

```bash
# Basic preset
python scripts/screening/accumulation_screen.py --preset accumulation_basic

# With OBV divergence (recommended)
python scripts/screening/accumulation_screen.py --preset accumulation_obv
```

### Moving Average Screener
```bash
# Stocks touching MA
python scripts/screening/korean_ma_touch.py

# Stocks below MA
python scripts/screening/korean_ma_below.py

# MA crossover detection
python scripts/screening/korean_crossover.py
```

### Breakout Detection
```bash
# Use the new condition-based screener
from screener import StockScreener, BottomBreakoutCondition, BreakoutWithVolumeCondition
```

---

## Backtesting (Strategy Research)

Test trading strategies with historical data.

```bash
# Basic backtest (Korean stock)
python scripts/backtesting/run_backtest.py --ticker 005930.KS --period 1y

# US stock with EMA strategy
python scripts/backtesting/run_backtest.py --ticker AAPL --strategy ema

# Parameter optimization
python scripts/backtesting/run_backtest.py --ticker 005930.KS --optimize
```

**Available Strategies:**
| Strategy | Description | Default |
|----------|-------------|---------|
| `sma` | Simple MA crossover | n1=10, n2=20 |
| `ema` | Exponential MA crossover | n1=12, n2=26 |

---

## Live Monitoring (Continuous)

### Options Tracker Bot
Detects unusual options activity for NVDA, AAPL, TSLA, AMZN.

```bash
# One-time check
python scripts/live/options_tracker.py --once

# Continuous monitoring (every 60 seconds)
python scripts/live/options_tracker.py
```

---

## Configuration

| File | Description |
|------|-------------|
| `config/portfolio.yaml` | Your holdings & sell conditions |
| `config/base_config.yaml` | Data paths, API, logging settings |

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for AI analysis |
| `FINNHUB_API_KEY` | Finnhub API for news (optional) |
| `MARKETAUX_API_KEY` | Marketaux API for news (optional) |

---

## Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/quant-investment.git
cd quant-investment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Stack
- **Python 3.13**
- **Claude API** - AI-powered stock analysis
- **Backtesting.py** - Strategy backtesting
- **yfinance** - US stock data
- **pykrx** - Korean stock data (KOSPI/KOSDAQ)
- **pandas/numpy** - Data processing

---

## Project Structure

```
quant-investment/
├── scripts/
│   ├── analysis/               # AI-powered analysis
│   │   └── run_daily_analysis.py
│   ├── screening/              # Stock screening
│   │   ├── accumulation_screen.py
│   │   ├── korean_daily_report.py
│   │   ├── us_daily_report.py
│   │   └── korean_ma_*.py
│   ├── backtesting/            # Strategy backtesting
│   │   └── run_backtest.py
│   └── live/                   # Live monitoring
│       ├── portfolio_sell_checker.py
│       └── options_tracker.py
├── llm/                        # Claude AI integration
│   ├── claude_client.py
│   ├── stock_analyzer.py
│   └── prompts/
├── data_enrichment/            # Data enrichment modules
│   ├── technical.py
│   ├── fundamental.py
│   └── news.py
├── pipeline/                   # Analysis pipeline
│   └── report_generator.py
├── screener/                   # Screening library
│   ├── conditions/             # Screening conditions
│   └── stock_screener.py
├── portfolio/                  # Portfolio management
│   └── position_sizing.py
├── config/                     # Configuration files
└── data/                       # Data cache
```

---

## Documentation

- [Breakout Conditions](docs/BREAKOUT_CONDITIONS.md)
- [Korean MA Screener](docs/KOREAN_MA_SCREENER.md)
- [Options Tracker Bot](docs/OPTIONS_TRACKER_README.md)
- [Market Calendar](docs/MARKET_CALENDAR_README.md)
- [Analysis Pipeline Plan](docs/works/20260211_semi_auto_analysis_pipeline.md)

---

## License

MIT
