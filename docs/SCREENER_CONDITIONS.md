# Screener Conditions Architecture

This document describes the condition-based stock screening architecture used in the `screener` module.

---

## Table of Contents

1. [Overview](#overview)
2. [Available Condition Classes (28)](#available-condition-classes-28)
3. [Combining Conditions](#combining-conditions)
4. [Adding New Conditions](#adding-new-conditions)
5. [Parameter Configuration Examples](#parameter-configuration-examples)
6. [Usage Examples](#usage-examples)
7. [File Structure](#file-structure)

---

## Overview

The screener module uses a **condition-based architecture** where each screening criterion is implemented as a class inheriting from `BaseCondition`. Conditions can be combined using composite operators (AND, OR, NOT) to build complex screening strategies.

**Key Components:**

- `BaseCondition` - Abstract base class for all conditions
- `ConditionResult` - Dataclass containing evaluation results
- `StockScreener` - Main screener class that evaluates conditions against stock data

---

## Available Condition Classes (28)

### Price Conditions (price.py - 4)

| Condition | Description | Key Parameters |
|-----------|-------------|----------------|
| `MinPriceCondition` | Minimum stock price | `min_price` |
| `MaxPriceCondition` | Maximum stock price | `max_price` |
| `PriceRangeCondition` | Price within range | `min_price`, `max_price` |
| `PriceChangeCondition` | Price change percentage | `min_change_pct`, `max_change_pct`, `days` |

### Volume Conditions (volume.py - 3)

| Condition | Description | Key Parameters |
|-----------|-------------|----------------|
| `MinVolumeCondition` | Minimum volume | `min_volume` |
| `VolumeAboveAvgCondition` | Volume above average | `multiplier`, `period` |
| `VolumeSpikeCondition` | Volume spike detection | `multiplier`, `period` |

### Moving Average Conditions (ma.py - 5)

| Condition | Description | Key Parameters |
|-----------|-------------|----------------|
| `MATouchCondition` | Price near MA (touch) | `period`, `threshold` |
| `AboveMACondition` | Price above MA | `period`, `min_distance_pct` |
| `BelowMACondition` | Price below MA | `period`, `max_distance_pct` |
| `MACrossUpCondition` | Golden Cross | `short_period`, `long_period`, `lookback_days` |
| `MACrossDownCondition` | Death Cross | `short_period`, `long_period`, `lookback_days` |

### RSI Conditions (rsi.py - 3)

| Condition | Description | Key Parameters |
|-----------|-------------|----------------|
| `RSIOversoldCondition` | RSI oversold (default <= 30) | `threshold`, `period` |
| `RSIOverboughtCondition` | RSI overbought (default >= 70) | `threshold`, `period` |
| `RSIRangeCondition` | RSI within range | `lower`, `upper`, `period` |

### Accumulation Conditions (accumulation.py - 9)

**Layer 1: Primitive Conditions**

| Condition | Description | Key Parameters |
|-----------|-------------|----------------|
| `BollingerWidthCondition` | BB width contraction | `max_width_pct`, `period`, `std_dev` |
| `VolumeBelowAvgCondition` | Volume below average | `multiplier`, `period` |
| `PriceFlatCondition` | Price consolidation (sideways) | `max_range_pct`, `period` |
| `OBVTrendCondition` | OBV trend direction | `direction`, `lookback` |
| `StochasticLevelCondition` | Stochastic level | `threshold`, `condition`, `k_period`, `d_period` |
| `VPCITrendCondition` | VPCI trend direction | `direction`, `short_period`, `long_period`, `lookback` |

**Layer 2: Divergence Conditions**

| Condition | Description | Key Parameters |
|-----------|-------------|----------------|
| `OBVDivergenceCondition` | OBV divergence (price flat + OBV up) | `price_max_range_pct`, `obv_min_change_pct`, `period` |
| `StochasticDivergenceCondition` | Stochastic divergence (bullish) | `k_period`, `d_period`, `lookback`, `divergence_threshold` |
| `VPCIDivergenceCondition` | VPCI divergence (price flat + VPCI up) | `price_max_range_pct`, `short_period`, `long_period`, `lookback` |

### Breakout Conditions (breakout.py - 4)

| Condition | Description | Key Parameters |
|-----------|-------------|----------------|
| `BottomBreakoutCondition` | N-day bottom breakout by X% | `lookback_days`, `breakout_pct` |
| `FreshBreakoutCondition` | First-time (fresh) breakout | `lookback_days`, `breakout_pct` |
| `BreakoutWithVolumeCondition` | Breakout with volume confirmation | `lookback_days`, `breakout_pct`, `volume_ratio`, `volume_avg_days`, `fresh_only` |
| `ResistanceBreakoutCondition` | Resistance level breakout | `lookback_days`, `breakout_margin_pct` |

### Composite Conditions (composite.py - 3)

| Condition | Description | Key Parameters |
|-----------|-------------|----------------|
| `AndCondition` | AND combination (all must match) | `conditions` (list) |
| `OrCondition` | OR combination (any must match) | `conditions` (list) |
| `NotCondition` | NOT (invert result) | `condition` |

---

## Combining Conditions

### AND Combination

All conditions must be satisfied:

```python
from screener.conditions import AndCondition, MinPriceCondition, MATouchCondition

combined = AndCondition([
    MinPriceCondition(5000),
    MATouchCondition(160),
])
```

### OR Combination

At least one condition must be satisfied:

```python
from screener.conditions import OrCondition, RSIOversoldCondition, MATouchCondition

combined = OrCondition([
    RSIOversoldCondition(30),
    MATouchCondition(200),
])
```

### NOT Combination

Inverts the condition result:

```python
from screener.conditions import NotCondition, RSIOverboughtCondition

not_overbought = NotCondition(RSIOverboughtCondition(70))
```

### Nested Combinations

Complex conditions with multiple levels:

```python
from screener.conditions import (
    AndCondition, OrCondition, NotCondition,
    MinPriceCondition, RSIOversoldCondition, MATouchCondition, RSIOverboughtCondition
)

complex_condition = AndCondition([
    MinPriceCondition(5000),
    OrCondition([
        RSIOversoldCondition(30),
        MATouchCondition(200),
    ]),
    NotCondition(RSIOverboughtCondition(70)),
])
```

---

## Adding New Conditions

Inherit from `BaseCondition` and implement 3 required methods:

```python
from screener.conditions.base import BaseCondition, ConditionResult
import pandas as pd

class MyCondition(BaseCondition):
    def __init__(self, param: float = 10):
        self.param = param

    @property
    def name(self) -> str:
        """Unique condition name for identification"""
        return f"my_condition_{self.param}"

    @property
    def required_days(self) -> int:
        """Number of historical data days needed"""
        return 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        """
        Evaluate the condition.

        Args:
            ticker: Stock symbol
            data: OHLCV DataFrame with columns: open, high, low, close, volume

        Returns:
            ConditionResult with matched status and details
        """
        if len(data) < self.required_days:
            return ConditionResult(
                matched=False,
                condition_name=self.name,
                details={"error": "Insufficient data"}
            )

        matched = data['close'].iloc[-1] > self.param

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={"value": float(data['close'].iloc[-1])}
        )
```

---

## Parameter Configuration Examples

### Price Conditions

```python
MinPriceCondition(min_price=5000)
MaxPriceCondition(max_price=100000)
PriceRangeCondition(min_price=5000, max_price=50000)
PriceChangeCondition(min_change_pct=-5.0, max_change_pct=5.0, days=5)
```

### Volume Conditions

```python
MinVolumeCondition(min_volume=100000)
VolumeAboveAvgCondition(multiplier=1.5, period=20)
VolumeSpikeCondition(multiplier=2.0, period=20)
```

### Moving Average Conditions

```python
MATouchCondition(period=160, threshold=0.02)  # within +/-2%
AboveMACondition(period=20, min_distance_pct=0.05)  # 5% above
BelowMACondition(period=60, max_distance_pct=-0.05)  # 5% below
MACrossUpCondition(short_period=20, long_period=60, lookback_days=5)
MACrossDownCondition(short_period=20, long_period=60, lookback_days=5)
```

### RSI Conditions

```python
RSIOversoldCondition(threshold=30, period=14)
RSIOverboughtCondition(threshold=70, period=14)
RSIRangeCondition(lower=40, upper=60, period=14)
```

### Accumulation Conditions

```python
BollingerWidthCondition(max_width_pct=10.0, period=20, std_dev=2.0)
VolumeBelowAvgCondition(multiplier=0.8, period=20)
PriceFlatCondition(max_range_pct=5.0, period=20)
OBVTrendCondition(direction="up", lookback=20)
StochasticLevelCondition(threshold=20, condition="below", k_period=14, d_period=3)
VPCITrendCondition(direction="up", short_period=5, long_period=20, lookback=10)
OBVDivergenceCondition(price_max_range_pct=5.0, obv_min_change_pct=5.0, period=20)
StochasticDivergenceCondition(k_period=14, d_period=3, lookback=20, divergence_threshold=5.0)
VPCIDivergenceCondition(price_max_range_pct=5.0, short_period=5, long_period=20, lookback=20)
```

### Breakout Conditions

```python
BottomBreakoutCondition(lookback_days=20, breakout_pct=5.0)
FreshBreakoutCondition(lookback_days=20, breakout_pct=5.0)
BreakoutWithVolumeCondition(
    lookback_days=20,
    breakout_pct=5.0,
    volume_ratio=1.5,
    volume_avg_days=10,
    fresh_only=True
)
ResistanceBreakoutCondition(lookback_days=20, breakout_margin_pct=1.0)
```

---

## Usage Examples

### Basic Screener Usage

```python
from screener import StockScreener
from screener.conditions import MinPriceCondition, MATouchCondition

screener = StockScreener()
screener.add_condition(MinPriceCondition(5000))
screener.add_condition(MATouchCondition(160))

# Run on KOSPI universe
results = screener.run(universe="KOSPI")

# Run on specific tickers
results = screener.run(tickers=['005930.KS', '000660.KS'])

# Convert results to DataFrame
df = screener.to_dataframe(results)
```

### Using Presets

```python
from screener.presets import get_preset, list_presets
from screener import StockScreener

# List available presets
print(list_presets())
# ['ma_touch_160', 'ma_touch_120', 'ma_touch_200', 'oversold_bounce',
#  'golden_cross', 'dead_cross', 'volume_breakout', 'ma_touch_with_oversold',
#  'trend_following', 'value_dip', 'momentum_breakout',
#  'accumulation_basic', 'accumulation_obv', 'accumulation_full']

# Use a preset
conditions = get_preset("accumulation_basic")
screener = StockScreener(conditions=conditions)
results = screener.run(universe="KOSPI")

# Preset with custom parameters
conditions = get_preset("accumulation_obv", min_price=10000, bb_max_width=12.0)
screener = StockScreener(conditions=conditions)
```

### Single Stock Evaluation

```python
from screener import StockScreener
from screener.conditions import MinPriceCondition, RSIOversoldCondition

screener = StockScreener()
screener.add_condition(MinPriceCondition(5000))
screener.add_condition(RSIOversoldCondition(30))

result = screener.run_single("005930.KS")
print(f"Matched: {result.matched}")
print(f"Price: {result.current_price}")
for cr in result.condition_results:
    print(f"  {cr.condition_name}: {cr.matched} - {cr.details}")
```

---

## File Structure

```
screener/
├── conditions/
│   ├── __init__.py        # Exports all conditions
│   ├── base.py            # BaseCondition, ConditionResult, ConditionError
│   ├── price.py           # Price conditions (4)
│   ├── volume.py          # Volume conditions (3)
│   ├── ma.py              # Moving average conditions (5)
│   ├── rsi.py             # RSI conditions (3)
│   ├── accumulation.py    # Accumulation zone conditions (9)
│   ├── breakout.py        # Breakout conditions (4)
│   └── composite.py       # AND/OR/NOT composite (3)
├── stock_screener.py      # Main StockScreener class
├── presets.py             # Pre-built condition combinations
└── kospi_fetcher.py       # KOSPI/KOSDAQ stock list fetcher
```

---

## See Also

- [Breakout Conditions](BREAKOUT_CONDITIONS.md) - Detailed breakout condition documentation
- [Screener README](SCREENER_README.md) - General screener usage guide
- [Korean MA Screener](KOREAN_MA_SCREENER.md) - Korean stock MA touch screener
