# Analysis Pipeline

This document describes the daily stock analysis pipeline that screens, enriches, and analyzes stocks using Claude AI.

---

## Pipeline Overview

```
+-------------------------------------------------------------+
|  1. Screening                                               |
|     Filter stocks touching 240-day moving average           |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  2. Enrichment                                              |
|     Add technical, fundamental, and news data               |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  3. Analysis                                                |
|     Analyze with Claude API or Claude Code                  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  4. Report                                                  |
|     Generate BUY/WAIT/AVOID + position sizing               |
+-------------------------------------------------------------+
```

---

## KOSPI vs S&P 500 Differences

| Item | KOSPI (Korea) | S&P 500 (US) |
|------|---------------|--------------|
| **Stock List** | `KospiListFetcher` (pykrx) | `UsStockFetcher` (Wikipedia) |
| **Min Price** | 1,000 KRW | $5 |
| **Min Volume** | 100,000 shares | 500,000 shares |
| **Ticker Format** | `005930.KS` | `AAPL` |
| **Currency** | KRW | USD |

---

## Data Sources

**Shared across markets:**

- **OHLCV Data**: `OHLCVCache` using yfinance (with caching)
- **Technical Indicators**: `TechnicalEnricher` (RSI, MACD, Bollinger Bands, OBV, Stochastic)
- **Fundamental Data**: `FundamentalEnricher` using yfinance `.info`
- **News**: `NewsEnricher` using Finnhub/Marketaux API

---

## Known Issues

For Korean stocks, yfinance often returns null for fundamental data (P/E, market cap, etc.). US stocks generally work fine.

To improve Korean stock fundamental data, an alternative source such as KRX or Naver Finance is needed.

---

## Usage

### Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables (optional):
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"    # For Claude API analysis
   export FINNHUB_API_KEY="your-api-key"      # For news (optional)
   export MARKETAUX_API_KEY="your-api-key"    # For news (optional)
   ```

### Basic Commands

```bash
# Full analysis with Claude API (requires ANTHROPIC_API_KEY)
python scripts/analysis/run_daily_analysis.py

# Single market
python scripts/analysis/run_daily_analysis.py --market KOSPI
python scripts/analysis/run_daily_analysis.py --market SP500

# Data enrichment only (no Claude analysis)
python scripts/analysis/run_daily_analysis.py --enrich-only

# Claude Code integration (saves JSON for manual analysis)
python scripts/analysis/run_daily_analysis.py --claude-code

# Custom capital for position sizing
python scripts/analysis/run_daily_analysis.py --capital 50000000
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--market`, `-m` | `ALL` | Market to analyze: `ALL`, `KOSPI`, `SP500` |
| `--capital`, `-c` | `10000000` | Total capital for position sizing |
| `--enrich-only` | `false` | Only run screening and enrichment |
| `--claude-code` | `false` | Save JSON for Claude Code analysis |
| `--ma-period` | `240` | Moving average period for screening |
| `--threshold` | `0.02` | MA touch threshold (2%) |

### Claude Code Integration

When using the `--claude-code` flag:

1. Run the pipeline to generate enriched JSON:
   ```bash
   python scripts/analysis/run_daily_analysis.py --claude-code
   ```

2. The enriched data is saved to `data/analysis/enriched_{market}_{date}.json`

3. In Claude Code, you can:
   - Use the `/analyze-stocks` skill (if configured)
   - Ask Claude Code to analyze the saved JSON file directly

### Output

The pipeline produces:

- **Valuation Score** (1-10): How attractive the stock is at current price
- **Risk Score** (1-10): Risk assessment based on volatility and fundamentals
- **Entry Recommendation**: `BUY`, `WAIT`, or `AVOID`
- **Position Sizing**: Suggested position size with stop-loss levels
- **Analysis Reasoning**: Detailed explanation for each recommendation

Reports are saved to `data/reports/` directory.

---

## Architecture

```
scripts/analysis/run_daily_analysis.py
        |
        +-- screener/
        |       +-- stock_screener.py      # Core screening engine
        |       +-- kospi_fetcher.py       # KOSPI stock list
        |       +-- us_fetcher.py          # S&P 500 stock list
        |       +-- conditions/            # Screening conditions
        |
        +-- data_enrichment/
        |       +-- technical.py           # Technical indicators
        |       +-- fundamental.py         # Fundamental data
        |       +-- news.py                # News aggregation
        |
        +-- llm/
        |       +-- stock_analyzer.py      # Claude API integration
        |       +-- prompts/               # Analysis prompts
        |
        +-- pipeline/
        |       +-- report_generator.py    # Report generation
        |
        +-- portfolio/
                +-- position_sizing.py     # Position sizing logic
```

---

## See Also

- [Breakout Conditions](BREAKOUT_CONDITIONS.md)
- [Korean MA Screener](KOREAN_MA_SCREENER.md)
- [Screener README](SCREENER_README.md)
