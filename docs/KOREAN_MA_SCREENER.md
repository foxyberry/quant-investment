# Korean Stock Moving Average Screener

A screener that finds KOSPI stocks trading below or touching moving averages (60-day to 365-day)

[한국어 문서](ko/KOREAN_MA_SCREENER.md)

---

## Screener Types

| Screener | File | Purpose |
|----------|------|---------|
| **Short/Mid-term MA** | `korean_ma_below.py` | 60-day, 120-day MA analysis |
| **Long-term MA Touch** | `korean_ma_touch.py` | 200-day, 240-day, 365-day MA touch/below analysis |

---

## 1. Short/Mid-term Moving Average Screener

### Usage
```bash
# Activate virtual environment
source venv/bin/activate

# Basic run (60-day, 120-day MA)
python scripts/screening/korean_ma_below.py

# Options
python scripts/screening/korean_ma_below.py --short-ma 20 --long-ma 60
python scripts/screening/korean_ma_below.py --limit 30
python scripts/screening/korean_ma_below.py --min-volume 500000
python scripts/screening/korean_ma_below.py --help
```

### Example Output
```
[Summary]
  Analyzed: 86 stocks
  Below 60-day MA: 30
  Below 120-day MA: 25
  Below both: 22

Stocks below 60-day MA (sorted by decline)
  1. Cosmo Materials (005070) | Price ₩43,450 | 60-day MA ₩50,433 | -13.8%
  2. Coway         (021240) | Price ₩78,400 | 60-day MA ₩87,883 | -10.8%
```

---

## 2. Long-term Moving Average Touch Screener

### Usage
```bash
# Basic run (200-day, 240-day, 365-day MA)
python scripts/screening/korean_ma_touch.py

# Change MA periods
python scripts/screening/korean_ma_touch.py --periods 120 200 365

# Change touch threshold (default ±2%)
python scripts/screening/korean_ma_touch.py --threshold 3.0

# All options
python scripts/screening/korean_ma_touch.py --help
```

### Status Classification
| Status | Label | Condition | Meaning |
|--------|-------|-----------|---------|
| **Touch** | [T] | Within ±2% of MA | Testing support/resistance near MA |
| **Below** | [B] | Below MA by >2% | Broken below MA |
| **Above** | [A] | Above MA by >2% | Stable above MA |

### Example Output
```
[Summary] Analyzed: 82 stocks
--------------------------------------------------
MA Period   |    Below |    Touch |    Above
--------------------------------------------------
200-day     |       11 |        8 |       63
240-day     |       11 |       10 |       61
365-day     |       11 |        4 |       67

Stocks touching/below multiple long-term MAs:
  1. SK Innovation | 200-day:-2.8% | 240-day:-5.5% | 365-day:-5.7%
```

---

## Interpretation Guide

### Moving Average Meanings

| MA Period | Meaning | Investment Perspective |
|-----------|---------|----------------------|
| **60-day** | ~3 month average | Short-term trend, swing trading reference |
| **120-day** | ~6 month average | Mid-term trend, quarterly earnings reflected |
| **200-day** | ~10 month average | Key long-term indicator, institutional trading reference |
| **240-day** | ~1 year (trading days) | Annual average cost basis, long-term investor breakeven |
| **365-day** | 1 year (calendar days) | Longest-term trend, major bull/bear determination |

### Status Interpretation

#### Touch [T] Stocks
```
Meaning: Current price within ±2% of MA
```
- **Support test**: Price dropped from above to near MA → Watch for bounce
- **Resistance test**: Price rose from below to near MA → Watch for breakout
- **Trading timing**: Consider entry after support/resistance confirmation

#### Below [B] Stocks
```
Meaning: Current price more than 2% below MA
```
- **Below short-term MA (60-day)**: Short-term correction, look for bounce opportunities
- **Below mid-term MA (120-day)**: Mid-term downtrend, proceed with caution
- **Below long-term MA (200-day+)**:
  - Possible entry into long-term downtrend
  - Contrarian investors may see buying opportunity
  - Risk of further decline → Consider dollar-cost averaging

#### Below Multiple MAs
```
Example: Below 200-day, 240-day, and 365-day MAs
```
- **Severe decline**: All timeframes in downtrend
- **Extreme undervaluation or deteriorating fundamentals**
- **Investment caution**:
  - Analyze reasons for decline (earnings? industry? temporary?)
  - Check financial statements and news before deciding
  - Manage risk with dollar-cost averaging

### Practical Examples

#### 1. Long-term Support Bounce Trade
```
Condition: "Touch" status at 200-day or 240-day MA
Strategy:
  - Buy when support is confirmed at MA
  - Stop loss: -5% below MA
  - Target: Previous high or +10%
```

#### 2. Contrarian Bottom Buying
```
Condition: "Below" 365-day MA + Quality stock
Strategy:
  - Select stocks with solid fundamentals
  - Dollar-cost average (3-5 tranches)
  - Long-term hold (6 months to 1 year)
```

#### 3. Trend Following Sell
```
Condition: Holding turns "Below" 120-day MA
Strategy:
  - Partial sell to prepare for further decline
  - Consider re-entry when 60-day MA recovers
```

### Cautions

1. **Moving averages are lagging indicators**
   - Based on historical data → Limited future prediction
   - Analyze with other indicators (volume, RSI, MACD)

2. **Consider sector/market conditions**
   - Individual stocks decline with overall market
   - Account for sector characteristics (growth vs value)

3. **Set stop-loss levels**
   - Further decline possible after MA break
   - Always set stop-loss price before entry

---

## Stock List Management

### Add/Remove Stocks
Edit `data/korean/kospi_master.csv` directly:

```csv
code,name,sector
005930,Samsung Electronics,Electronics
000660,SK Hynix,Electronics
373220,LG Energy Solution,Electronics
...
```

### File Locations
| File | Purpose |
|------|---------|
| `data/korean/kospi_master.csv` | Stock master list (manual) |
| `data/korean/kospi_list.csv` | Cache file (auto-generated) |

---

## File Structure

```
quant-investment/
├── screener/
│   ├── kospi_fetcher.py         # Stock list fetcher
│   └── conditions/              # MA conditions (BelowMACondition, MATouchCondition, etc.)
│
├── scripts/screening/
│   ├── korean_ma_below.py       # Short/mid-term MA runner
│   ├── korean_ma_touch.py       # Long-term MA touch runner
│   ├── korean_crossover.py      # Golden/Dead cross runner
│   └── korean_daily_report.py   # Daily comprehensive report
│
├── config/
│   └── korean_screening.yaml    # Configuration
│
└── data/korean/
    ├── kospi_master.csv         # Stock master
    └── kospi_list.csv           # Cache
```

---

## Tech Stack

- **yfinance** - Stock data fetching (`.KS` suffix for KOSPI)
- **pandas** - Data processing
- **pykrx** - Korean stock data (optional)
