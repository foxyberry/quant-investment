# quant-investment

Quantitative investment strategy development and backtesting project

[한국어 README](README_KO.md)

---

## Web UI (New!)

The platform now includes a web-based dashboard for easy access to all features.

### Quick Start

```bash
# Start both API and Web servers
./scripts/dev.sh
```

### Development URLs

| Service | URL | Description |
|---------|-----|-------------|
| Web Dashboard | http://localhost:3000 | Main user interface |
| API | http://localhost:8000 | REST API backend |
| Swagger Docs | http://localhost:8000/docs | Interactive API documentation |
| ReDoc | http://localhost:8000/redoc | Alternative API documentation |

### Individual Services

```bash
# API only (FastAPI)
./scripts/run_api.sh

# Web only (Next.js) - requires API running
./scripts/run_web.sh
```

### Docker Deployment

```bash
# Build and run all services
docker-compose up -d

# Build specific service
docker-compose up -d api
docker-compose up -d web

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Documentation

- [API Reference](docs/API_REFERENCE.md) - Complete REST API documentation
- [Development Guide](docs/DEVELOPMENT_GUIDE.md) - Setup and contribution guide

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

## AI-Powered Stock Analysis

Semi-automated analysis pipeline using Claude AI:
1. Screen stocks touching 240-day MA
2. Enrich with technical indicators, fundamentals, and news
3. Analyze with Claude for valuation and entry timing
4. Generate report with position sizing recommendations

### Option 1: Claude API

```bash
# Full analysis (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY="your-api-key"
python scripts/analysis/run_daily_analysis.py

# Single market
python scripts/analysis/run_daily_analysis.py --market KOSPI
python scripts/analysis/run_daily_analysis.py --market SP500
```

### Option 2: Claude Code Integration

```bash
# Run screening and enrichment, save JSON for Claude Code
python scripts/analysis/run_daily_analysis.py --claude-code

# Then in Claude Code, use the /analyze-stocks skill
# or ask Claude Code to analyze the saved JSON file
```

### Other Options

```bash
# Data enrichment only (no analysis)
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
- **FastAPI** - REST API backend
- **Next.js 16** - Web frontend (App Router)
- **Claude API** - AI-powered stock analysis
- **Backtesting.py** - Strategy backtesting
- **yfinance** - US stock data
- **pykrx** - Korean stock data (KOSPI/KOSDAQ)
- **pandas/numpy** - Data processing
- **Tailwind CSS** - Frontend styling

---

## Project Structure

```
quant-investment/
├── api/                        # FastAPI backend
│   ├── main.py                 # Application entry point
│   ├── routers/                # API endpoints
│   ├── schemas/                # Request/response models
│   └── services/               # Business logic
├── web/                        # Next.js frontend
│   ├── src/app/                # Pages (App Router)
│   ├── src/components/         # React components
│   └── src/lib/                # Utilities
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
│   ├── live/                   # Live monitoring
│   │   ├── portfolio_sell_checker.py
│   │   └── options_tracker.py
│   ├── dev.sh                  # Start all services
│   ├── run_api.sh              # Start API only
│   └── run_web.sh              # Start web only
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
├── data/                       # Data cache
├── docker-compose.yml          # Docker configuration
└── Dockerfile.api              # API Docker image
```

---

## Documentation

### API & Development
- [API Reference](docs/API_REFERENCE.md) - Complete REST API documentation
- [Development Guide](docs/DEVELOPMENT_GUIDE.md) - Setup and contribution guide

### Screener
- [Screener Conditions Architecture](docs/SCREENER_CONDITIONS.md) - All 28 condition classes and usage
- [Accumulation Zone Screening](docs/ACCUMULATION_SCREENING.md) - Quiet accumulation detection guide
- [Breakout Conditions](docs/BREAKOUT_CONDITIONS.md) - Breakout detection conditions
- [Korean MA Screener](docs/KOREAN_MA_SCREENER.md) - Korean stock MA touch screener

### Analysis & Monitoring
- [Analysis Pipeline](docs/ANALYSIS_PIPELINE.md) - AI-powered analysis workflow
- [Options Tracker Bot](docs/OPTIONS_TRACKER_README.md) - Options activity monitoring
- [Market Calendar](docs/MARKET_CALENDAR_README.md) - Market hours utility

### Work Plans
- [Analysis Pipeline Plan](docs/works/20260211_semi_auto_analysis_pipeline.md)
- [UI Integration Plan](docs/works/20260212_ui_integration_project.md)

---

## License

MIT
