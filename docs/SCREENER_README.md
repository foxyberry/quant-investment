# Extensible Stock Screening System

A flexible stock screening system that allows composing multiple condition classes.

> Korean version: [docs/ko/SCREENER_README.md](./ko/SCREENER_README.md)

## Quick Start

```python
from screener import StockScreener, MinPriceCondition, MATouchCondition

# Create screener and add conditions
screener = StockScreener()
screener.add_condition(MinPriceCondition(5000))          # Min price 5000 KRW
screener.add_condition(MATouchCondition(period=160))     # Touch 160-day MA

# Run screening
results = screener.run(universe="KOSPI")

# Print results
for r in results:
    print(f"{r.ticker} ({r.name}): {r.current_price:,.0f} KRW")
```

## CLI Usage

```bash
# Use preset
python scripts/screening/run_screener.py --preset ma_touch_160

# List available presets
python scripts/screening/run_screener.py --list-presets

# Check single stock
python scripts/screening/run_screener.py --ticker 035420.KS

# Specify universe
python scripts/screening/run_screener.py --preset golden_cross --universe KOSDAQ
```

## Condition Classes

### Price Conditions

| Class | Description | Parameters |
|-------|-------------|------------|
| `MinPriceCondition` | Minimum price | `min_price` |
| `MaxPriceCondition` | Maximum price | `max_price` |
| `PriceRangeCondition` | Price range | `min_price`, `max_price` |
| `PriceChangeCondition` | Price change % | `min_change`, `max_change`, `period` |

```python
from screener import MinPriceCondition, PriceRangeCondition

# Price >= 5000
MinPriceCondition(min_price=5000)

# Price between 10000-50000
PriceRangeCondition(min_price=10000, max_price=50000)
```

### Volume Conditions

| Class | Description | Parameters |
|-------|-------------|------------|
| `MinVolumeCondition` | Minimum volume | `min_volume` |
| `VolumeAboveAvgCondition` | Volume vs average | `multiplier`, `period` |
| `VolumeSpikeCondition` | Volume spike | `multiplier`, `period` |

```python
from screener import MinVolumeCondition, VolumeSpikeCondition

# Volume >= 100,000
MinVolumeCondition(min_volume=100000)

# Volume 2x of 20-day average
VolumeSpikeCondition(multiplier=2.0, period=20)
```

### Moving Average Conditions

| Class | Description | Parameters |
|-------|-------------|------------|
| `MATouchCondition` | Price near MA | `period`, `threshold` |
| `AboveMACondition` | Price above MA | `period`, `min_distance_pct` |
| `BelowMACondition` | Price below MA | `period`, `max_distance_pct` |
| `MACrossUpCondition` | Golden cross | `short_period`, `long_period`, `lookback_days` |
| `MACrossDownCondition` | Death cross | `short_period`, `long_period`, `lookback_days` |

```python
from screener import MATouchCondition, MACrossUpCondition, AboveMACondition

# Within 2% of 160-day MA
MATouchCondition(period=160, threshold=0.02)

# 20/60 golden cross (within last 5 days)
MACrossUpCondition(short_period=20, long_period=60, lookback_days=5)

# Above 20-day MA
AboveMACondition(period=20)
```

### RSI Conditions

| Class | Description | Parameters |
|-------|-------------|------------|
| `RSIOversoldCondition` | Oversold | `threshold`, `period` |
| `RSIOverboughtCondition` | Overbought | `threshold`, `period` |
| `RSIRangeCondition` | RSI range | `lower`, `upper`, `period` |

```python
from screener import RSIOversoldCondition, RSIRangeCondition

# RSI <= 30 (oversold)
RSIOversoldCondition(threshold=30, period=14)

# RSI between 40-60
RSIRangeCondition(lower=40, upper=60)
```

### Composite Conditions

| Class | Description |
|-------|-------------|
| `AndCondition` | All conditions must match |
| `OrCondition` | At least one must match |
| `NotCondition` | Invert condition |

```python
from screener import AndCondition, OrCondition, NotCondition

# AND: all must match
condition = AndCondition([
    MinPriceCondition(5000),
    MATouchCondition(160),
    RSIOversoldCondition(30)
])

# OR: at least one must match
condition = OrCondition([
    MATouchCondition(120),
    MATouchCondition(160),
    MATouchCondition(200)
])

# NOT: invert
condition = NotCondition(RSIOverboughtCondition(70))  # RSI < 70
```

## Presets

Common strategy combinations ready to use.

```python
from screener import get_preset, list_presets, StockScreener

# List available presets
print(list_presets())
# ['ma_touch_160', 'ma_touch_120', 'ma_touch_200', 'oversold_bounce',
#  'golden_cross', 'dead_cross', 'volume_breakout', 'ma_touch_with_oversold',
#  'trend_following', 'value_dip', 'momentum_breakout']

# Use preset
screener = StockScreener(conditions=get_preset("ma_touch_160"))
results = screener.run(universe="KOSPI")

# Preset + additional conditions
screener = StockScreener(conditions=get_preset("golden_cross"))
screener.add_condition(MinVolumeCondition(50000))
```

### Available Presets

| Name | Description |
|------|-------------|
| `ma_touch_160` | 160-day MA touch + min price |
| `ma_touch_120` | 120-day MA touch + min price |
| `ma_touch_200` | 200-day MA touch + min price |
| `oversold_bounce` | RSI oversold bounce |
| `golden_cross` | 20/60 golden cross |
| `dead_cross` | 20/60 death cross |
| `volume_breakout` | 2x volume breakout |
| `ma_touch_with_oversold` | MA touch + RSI oversold |
| `trend_following` | Trend following (above MA + RSI 50+) |
| `value_dip` | Value dip buying |
| `momentum_breakout` | Momentum breakout |

## StockScreener API

### Constructor

```python
StockScreener(conditions=None, max_workers=10)
```

- `conditions`: Initial list of conditions
- `max_workers`: Number of parallel workers

### Methods

```python
# Add condition (supports chaining)
screener.add_condition(condition) -> StockScreener

# Clear all conditions
screener.clear_conditions() -> StockScreener

# Run screening
screener.run(universe="KOSPI", tickers=None, show_progress=True) -> List[ScreeningResult]

# Check single stock
screener.run_single(ticker) -> ScreeningResult

# Convert to DataFrame
screener.to_dataframe(results) -> pd.DataFrame
```

### Universe

- `"KOSPI"`: KOSPI representative stocks (~35)
- `"KOSDAQ"`: KOSDAQ representative stocks (~15)
- `"ALL"`: KOSPI + KOSDAQ

Custom ticker list:
```python
results = screener.run(tickers=["005930.KS", "035420.KS", "000660.KS"])
```

## ScreeningResult

```python
@dataclass
class ScreeningResult:
    ticker: str                           # Stock ticker
    name: str                             # Stock name
    matched: bool                         # Match status
    condition_results: List[ConditionResult]  # Per-condition results
    current_price: Optional[float]        # Current price
    volume: Optional[int]                 # Volume
    timestamp: datetime                   # Check timestamp
```

```python
result = screener.run_single("035420.KS")

print(result.ticker)        # 035420.KS
print(result.name)          # NAVER
print(result.matched)       # True/False
print(result.current_price) # 284000.0

# Check per-condition results
for cr in result.condition_results:
    print(f"{cr.condition_name}: {cr.matched}")
    print(f"  Details: {cr.details}")
```

## Creating Custom Conditions

```python
from screener.conditions.base import BaseCondition, ConditionResult
import pandas as pd

class MyCustomCondition(BaseCondition):
    def __init__(self, param1: float):
        self.param1 = param1

    @property
    def name(self) -> str:
        return f"my_custom_{self.param1}"

    @property
    def required_days(self) -> int:
        return 30  # Days of data needed

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        # Custom logic
        close = data['close']
        my_value = close.iloc[-1] / close.iloc[-10]
        matched = my_value > self.param1

        return ConditionResult(
            matched=matched,
            condition_name=self.name,
            details={
                "my_value": float(my_value),
                "param1": self.param1
            }
        )
```

## File Structure

```
screener/
├── conditions/
│   ├── __init__.py      # Module exports
│   ├── base.py          # BaseCondition, ConditionResult
│   ├── price.py         # Price conditions
│   ├── volume.py        # Volume conditions
│   ├── ma.py            # Moving average conditions
│   ├── rsi.py           # RSI conditions
│   └── composite.py     # AND/OR/NOT
├── stock_screener.py    # StockScreener class
├── presets.py           # Preset strategies
└── __init__.py          # Module exports

scripts/screening/
└── run_screener.py      # CLI script
```

## Related

- [GitHub Issue #27](https://github.com/foxyberry/quant-investment/issues/27)
- [Korean Documentation](./ko/SCREENER_README.md)
