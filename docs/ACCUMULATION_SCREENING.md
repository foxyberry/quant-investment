# Accumulation Zone Screening

This document explains how to use the accumulation zone screening feature to identify stocks in quiet accumulation phases.

---

## Table of Contents

1. [What is Accumulation?](#what-is-accumulation)
2. [Technical Signals](#technical-signals)
3. [Presets](#presets)
4. [Usage](#usage)
5. [Parameters](#parameters)
6. [Interpreting Results](#interpreting-results)
7. [Investment Strategy](#investment-strategy)
8. [Cautions](#cautions)
9. [Code Examples](#code-examples)

---

## What is Accumulation?

**Accumulation** refers to the phase where institutional investors or "smart money" quietly buy shares over time without significantly moving the price.

### Characteristics

| Indicator | During Accumulation |
|-----------|---------------------|
| Volatility | Low (tight price range) |
| Volume | Below average |
| Price Action | Sideways/Consolidation |
| Media Attention | Low |

### Why It Matters

- After accumulation ends, stocks often experience significant upward breakouts
- Early detection allows entry before the crowd
- Lower risk entry due to tight stop-loss levels (just below the consolidation range)

---

## Technical Signals

### Bollinger Band Squeeze

The Bollinger Band width narrows when volatility decreases, indicating consolidation.

```
Upper Band ----====----
Price          ====
Lower Band ----====----
              ^squeeze^
```

- **Condition**: Band width below threshold (default: 15%)
- **Interpretation**: Squeeze often precedes explosive moves
- **Parameter**: `bb_max_width` (default: 15.0%)

### Volume Decline

Below-average volume indicates lack of public interest, allowing quiet accumulation.

- **Condition**: Volume below moving average
- **Interpretation**: Low participation = potential for smart money accumulation
- **Parameter**: `volume_multiplier` (default: 1.0 = at or below average)

### Price Consolidation (Flat Price)

Price moves within a narrow range, indicating equilibrium between buyers and sellers.

- **Condition**: 20-day price range below threshold
- **Interpretation**: Tight range = accumulation without price impact
- **Parameter**: `price_max_range` (default: 10.0%)

### OBV Divergence (Most Important)

**On-Balance Volume (OBV)** tracks cumulative buying/selling pressure.

```
Price:  ----====----  (flat)
OBV:    ____/^^^^^^   (rising)
        = BULLISH DIVERGENCE
```

- **Condition**: Price flat but OBV rising
- **Interpretation**: Net buying despite flat price = accumulation
- **Strength**: Most reliable accumulation signal

### Stochastic Divergence

Detects momentum shifts hidden in price action.

- **Condition**: Price making lower lows, but Stochastic making higher lows
- **Interpretation**: Selling pressure weakening
- **Signal Type**: Bullish divergence

### VPCI Divergence (Volume-Price Confirmation Indicator)

Analyzes the relationship between price movement and volume.

- **Condition**: Positive divergence between price and VPCI
- **Interpretation**: Volume confirms accumulation
- **Signal Type**: Accumulation confirmation

---

## Presets

| Preset | Conditions | Reliability | Result Count | Recommended For |
|--------|-----------|-------------|--------------|-----------------|
| `accumulation_basic` | BB Squeeze + Low Volume + Flat Price | Low | Many (~200) | Wide exploration |
| `accumulation_obv` | Basic + OBV Divergence | Medium | Few | **Best choice** |
| `accumulation_full` | Basic + Any Divergence (OBV/Stoch/VPCI) | Medium | Few | Diverse signals |

### Preset Details

**accumulation_basic**
- Broad filter for initial screening
- High false positive rate
- Use for exploration, not final decisions

**accumulation_obv** (Recommended)
- Adds OBV divergence requirement
- Most reliable single indicator for accumulation
- Best balance of quality and quantity

**accumulation_full**
- Requires any one of three divergence types
- Catches signals that OBV alone might miss
- Good for comprehensive scanning

---

## Usage

### Basic Commands

```bash
# Single stock analysis
python scripts/screening/accumulation_screen.py --ticker 005930.KS

# OBV divergence preset (recommended)
python scripts/screening/accumulation_screen.py --preset accumulation_obv

# KOSDAQ screening
python scripts/screening/accumulation_screen.py --preset accumulation_obv --universe KOSDAQ

# All Korean stocks
python scripts/screening/accumulation_screen.py --preset accumulation_obv --universe ALL
```

### Stricter Conditions

```bash
# Tighter Bollinger Band (8% instead of 15%)
python scripts/screening/accumulation_screen.py --preset accumulation_basic --bb-width 8.0

# Lower volume threshold (70% of average)
python scripts/screening/accumulation_screen.py --preset accumulation_basic --volume-mult 0.7

# Combine multiple strict parameters
python scripts/screening/accumulation_screen.py --preset accumulation_obv \
    --bb-width 8.0 \
    --volume-mult 0.7 \
    --price-range 5.0 \
    --min-price 10000
```

### List Available Presets

```bash
python scripts/screening/accumulation_screen.py --list-presets
```

---

## Parameters

| Parameter | Default | Description | Strict Value |
|-----------|---------|-------------|--------------|
| `--min-price` | 5000 | Minimum stock price (KRW) | 10000 |
| `--bb-width` | 15.0 | Max Bollinger Band width (%) | 8.0 |
| `--volume-mult` | 1.0 | Volume multiplier (1.0 = average) | 0.7 |
| `--price-range` | 10.0 | Max 20-day price range (%) | 5.0 |
| `--universe` | KOSPI | Market (KOSPI/KOSDAQ/ALL) | - |
| `--preset` | accumulation_basic | Preset name | accumulation_obv |

### Parameter Tuning Guide

| Goal | Adjust |
|------|--------|
| Fewer, higher-quality results | Lower `--bb-width`, `--volume-mult`, `--price-range` |
| More results to explore | Increase thresholds |
| Exclude penny stocks | Increase `--min-price` |
| Different market | Change `--universe` |

---

## Interpreting Results

### Example Output

```
005930 (Samsung Electronics)
  Price: 72,000
  [PASS] min_price_5000
  [PASS] bb_width_15.0
  [PASS] volume_below_avg_1.0
  [PASS] price_flat_10.0
  [PASS] obv_divergence
```

### Understanding Results

| Status | Meaning |
|--------|---------|
| `[PASS]` | Condition satisfied |
| `[FAIL]` | Condition not met |

### Signal Strength Ranking

1. **All PASS + OBV Divergence**: Strongest accumulation signal
2. **All PASS (basic only)**: Possible accumulation, needs confirmation
3. **Some FAIL**: Not in accumulation phase

---

## Investment Strategy

### Entry Strategy

1. **Screen**: Use `accumulation_obv` preset to find candidates
2. **Verify**: Check chart for support/resistance levels
3. **Confirm**: Look for additional signals (news, fundamentals)
4. **Enter**:
   - Option A: Buy on breakout above consolidation range
   - Option B: Scale in near support within the range

### Stop-Loss Guidelines

| Condition | Action |
|-----------|--------|
| Price breaks below consolidation range | Exit position |
| High volume + price decline | Exit (distribution signal) |
| OBV turns down while price flat | Reduce position |

### Take-Profit Guidelines

| Condition | Action |
|-----------|--------|
| Price touches upper Bollinger Band | Consider partial exit |
| Volume spike + price surge | Breakout complete, trail stop |
| Target reached (range height added to breakout) | Take profit |

### Position Sizing

```
Risk per trade: 1-2% of portfolio
Stop-loss: Just below consolidation low
Position size = (Risk Amount) / (Entry Price - Stop Price)
```

---

## Cautions

### False Signals

- Not all accumulation zones lead to upward breakouts
- Downward breakouts are possible (distribution phase)
- Always use stop-losses

### Complementary Analysis Required

| Analysis Type | Purpose |
|---------------|---------|
| Fundamental | Verify company health |
| News/Sentiment | Check for upcoming catalysts |
| Sector/Industry | Confirm sector trend alignment |
| Market Condition | Bull/bear market context |

### Limitations

- Screening identifies candidates, not guarantees
- Final decision requires human judgment
- Past patterns may not repeat

---

## Code Examples

### Python API Usage

```python
from screener import StockScreener, get_preset

# Using preset
conditions = get_preset("accumulation_obv")
screener = StockScreener(conditions=conditions)
results = screener.run(universe="KOSPI")

# Print results
for r in results:
    print(f"{r.ticker} ({r.name}) - {r.current_price:,} KRW")

# Convert to DataFrame
df = screener.to_dataframe(results)
print(df[['ticker', 'name', 'current_price', 'matched']])
```

### Custom Conditions

```python
from screener import (
    StockScreener,
    MinPriceCondition,
    BollingerWidthCondition,
    VolumeBelowAvgCondition,
    OBVDivergenceCondition,
)

# Build custom screener
conditions = [
    MinPriceCondition(10000),           # Min 10,000 KRW
    BollingerWidthCondition(8.0),       # Tight squeeze (8%)
    VolumeBelowAvgCondition(0.7),       # Volume < 70% of average
    OBVDivergenceCondition(),           # OBV bullish divergence
]

screener = StockScreener(conditions=conditions)
results = screener.run(universe="KOSPI")
```

### Single Stock Analysis

```python
from screener import StockScreener, get_preset

conditions = get_preset("accumulation_obv")
screener = StockScreener(conditions=conditions)

# Analyze single stock
result = screener.run_single("005930.KS")

print(f"Stock: {result.name}")
print(f"Price: {result.current_price:,}")
print(f"Matched: {result.matched}")

for cr in result.condition_results:
    status = "PASS" if cr.matched else "FAIL"
    print(f"  [{status}] {cr.condition_name}")
    for k, v in cr.details.items():
        print(f"      {k}: {v}")
```

### Batch Processing with DataFrame

```python
from screener import StockScreener, get_preset
import pandas as pd

# Run screening
conditions = get_preset("accumulation_obv")
screener = StockScreener(conditions=conditions)
results = screener.run(universe="ALL")

# Convert to DataFrame for analysis
df = screener.to_dataframe(results)

# Filter and sort
df_sorted = df.sort_values('current_price', ascending=False)

# Export to CSV
df_sorted.to_csv('accumulation_candidates.csv', index=False)
```

---

## Related Documentation

- [Screener Conditions Architecture](SCREENER_CONDITIONS.md) - All 28 condition classes
- [Breakout Conditions](BREAKOUT_CONDITIONS.md) - Breakout detection after accumulation

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-12 | Initial documentation |
