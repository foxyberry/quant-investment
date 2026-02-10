# Breakout Conditions

Breakout condition classes for stock screening based on price breakouts from technical levels.

> Korean version: [docs/ko/BREAKOUT_CONDITIONS.md](./ko/BREAKOUT_CONDITIONS.md)

## Overview

### What is Breakout Trading?

Breakout trading is a strategy that enters a position when the price moves beyond a defined support or resistance level with increased volume. The core idea is that once price breaks through a significant level, momentum often continues in that direction.

**Key concepts:**

- **Bottom Breakout**: Price rises above a recent low by a certain percentage, signaling potential reversal from a downtrend
- **Resistance Breakout**: Price moves above a recent high, indicating potential continuation of an uptrend
- **Fresh Breakout**: First-time breakout that has not occurred before in the lookback period
- **Volume Confirmation**: Breakout accompanied by higher-than-average volume, adding conviction to the move

### Why Use Breakout Conditions?

| Scenario | Condition to Use |
|----------|------------------|
| Find stocks bouncing from recent lows | `BottomBreakoutCondition` |
| Catch the first day of a breakout | `FreshBreakoutCondition` |
| Filter breakouts with volume confirmation | `BreakoutWithVolumeCondition` |
| Find new 52-week high candidates | `ResistanceBreakoutCondition` |

## Condition Classes

### BottomBreakoutCondition

Detects when price has risen X% above the N-day low.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_days` | int | 20 | Period to find the bottom price |
| `breakout_pct` | float | 5.0 | Required rise from bottom (%) |

**Usage:**

```python
from screener.conditions.breakout import BottomBreakoutCondition

# Price 5% above 20-day low
condition = BottomBreakoutCondition(lookback_days=20, breakout_pct=5.0)

# Price 10% above 60-day low (larger swing)
condition = BottomBreakoutCondition(lookback_days=60, breakout_pct=10.0)
```

**Result Details:**

```python
{
    "current_price": 52500.0,
    "bottom_price": 48000.0,
    "bottom_date": "2024-01-15",
    "breakout_price": 50400.0,      # bottom * 1.05
    "price_from_bottom_pct": 9.38,  # actual rise from bottom
    "lookback_days": 20,
    "breakout_pct": 5.0
}
```

---

### FreshBreakoutCondition

Detects the first occurrence of a breakout. Filters out stocks that have already broken out previously in the lookback period.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_days` | int | 20 | Period to find the bottom price |
| `breakout_pct` | float | 5.0 | Required rise from bottom (%) |

**Usage:**

```python
from screener.conditions.breakout import FreshBreakoutCondition

# First-time 5% breakout from 20-day low
condition = FreshBreakoutCondition(lookback_days=20, breakout_pct=5.0)
```

**Breakout Status Values:**

| Status | Meaning |
|--------|---------|
| `FRESH_BREAKOUT` | First time breaking out today |
| `ALREADY_ABOVE` | Currently above breakout level, but broke out before |
| `BELOW` | Price is below breakout level |

**Result Details:**

```python
{
    "current_price": 52500.0,
    "bottom_price": 48000.0,
    "bottom_date": "2024-01-15",
    "breakout_price": 50400.0,
    "price_from_bottom_pct": 9.38,
    "breakout_status": "FRESH_BREAKOUT",
    "is_breakout_today": True,
    "has_broken_before": False
}
```

---

### BreakoutWithVolumeCondition

Combines breakout detection with volume confirmation. Requires both price breakout and volume spike.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_days` | int | 20 | Period to find the bottom price |
| `breakout_pct` | float | 5.0 | Required rise from bottom (%) |
| `volume_ratio` | float | 1.5 | Required volume vs average (1.5 = 150%) |
| `volume_avg_days` | int | 10 | Period for average volume calculation |
| `fresh_only` | bool | True | Only match fresh breakouts |

**Usage:**

```python
from screener.conditions.breakout import BreakoutWithVolumeCondition

# Fresh breakout with 1.5x volume
condition = BreakoutWithVolumeCondition(
    lookback_days=20,
    breakout_pct=5.0,
    volume_ratio=1.5,
    volume_avg_days=10,
    fresh_only=True
)

# Any breakout (not just fresh) with 2x volume
condition = BreakoutWithVolumeCondition(
    lookback_days=20,
    breakout_pct=5.0,
    volume_ratio=2.0,
    fresh_only=False
)
```

**Result Details:**

```python
{
    "current_price": 52500.0,
    "bottom_price": 48000.0,
    "bottom_date": "2024-01-15",
    "breakout_price": 50400.0,
    "price_from_bottom_pct": 9.38,
    "is_breakout_today": True,
    "is_fresh": True,
    "current_volume": 1500000,
    "avg_volume": 800000,
    "volume_ratio": 1.875,           # actual ratio
    "required_volume_ratio": 1.5,    # threshold
    "is_volume_spike": True
}
```

---

### ResistanceBreakoutCondition

Detects when price breaks above N-day resistance (highest high).

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_days` | int | 20 | Period to find resistance level |
| `breakout_margin_pct` | float | 0.0 | Required margin above resistance (%) |

**Usage:**

```python
from screener.conditions.breakout import ResistanceBreakoutCondition

# Break above 20-day high
condition = ResistanceBreakoutCondition(lookback_days=20)

# Break 1% above 60-day high (confirmed breakout)
condition = ResistanceBreakoutCondition(lookback_days=60, breakout_margin_pct=1.0)

# 52-week high breakout
condition = ResistanceBreakoutCondition(lookback_days=252)
```

**Result Details:**

```python
{
    "current_price": 55000.0,
    "resistance_price": 54000.0,
    "resistance_date": "2024-01-10",
    "breakout_price": 54000.0,       # resistance * 1.00 (no margin)
    "distance_from_resistance_pct": 1.85,
    "lookback_days": 20
}
```

## Sample Screening Script

Below is a complete example combining multiple breakout conditions for screening.

```python
#!/usr/bin/env python
"""
Breakout Screening Example
Finds stocks with fresh volume-confirmed breakouts
"""

from screener import StockScreener
from screener.conditions.breakout import (
    BottomBreakoutCondition,
    FreshBreakoutCondition,
    BreakoutWithVolumeCondition,
    ResistanceBreakoutCondition,
)
from screener.conditions.price import MinPriceCondition
from screener.conditions.volume import MinVolumeCondition
from screener.conditions.composite import AndCondition, OrCondition


def run_bottom_breakout_screen():
    """Screen for bottom breakout stocks."""
    screener = StockScreener()

    # Basic filters
    screener.add_condition(MinPriceCondition(min_price=5000))
    screener.add_condition(MinVolumeCondition(min_volume=100000))

    # Fresh breakout with volume confirmation
    screener.add_condition(BreakoutWithVolumeCondition(
        lookback_days=20,
        breakout_pct=5.0,
        volume_ratio=1.5,
        fresh_only=True
    ))

    results = screener.run(universe="KOSPI")

    print(f"\n{'='*60}")
    print("Bottom Breakout Stocks (Fresh + Volume)")
    print(f"{'='*60}")

    for r in results:
        details = r.condition_results[-1].details
        print(f"\n{r.ticker} ({r.name})")
        print(f"  Price: {r.current_price:,.0f} KRW")
        print(f"  Bottom: {details['bottom_price']:,.0f} ({details['bottom_date']})")
        print(f"  Rise from bottom: {details['price_from_bottom_pct']:.1f}%")
        print(f"  Volume ratio: {details['volume_ratio']:.2f}x")

    return results


def run_resistance_breakout_screen():
    """Screen for resistance breakout stocks."""
    screener = StockScreener()

    # Basic filters
    screener.add_condition(MinPriceCondition(min_price=5000))

    # 20-day resistance breakout
    screener.add_condition(ResistanceBreakoutCondition(
        lookback_days=20,
        breakout_margin_pct=0.5  # 0.5% above resistance
    ))

    results = screener.run(universe="KOSPI")

    print(f"\n{'='*60}")
    print("Resistance Breakout Stocks")
    print(f"{'='*60}")

    for r in results:
        details = r.condition_results[-1].details
        print(f"\n{r.ticker} ({r.name})")
        print(f"  Price: {r.current_price:,.0f} KRW")
        print(f"  Resistance: {details['resistance_price']:,.0f} ({details['resistance_date']})")
        print(f"  Above resistance: {details['distance_from_resistance_pct']:.1f}%")

    return results


def run_multi_timeframe_breakout():
    """Screen for breakouts across multiple timeframes."""
    screener = StockScreener()

    screener.add_condition(MinPriceCondition(min_price=5000))

    # Match if breaking out of ANY timeframe
    multi_breakout = OrCondition([
        FreshBreakoutCondition(lookback_days=20, breakout_pct=5.0),
        FreshBreakoutCondition(lookback_days=60, breakout_pct=10.0),
        ResistanceBreakoutCondition(lookback_days=60),
    ])
    screener.add_condition(multi_breakout)

    results = screener.run(universe="KOSPI")

    print(f"\n{'='*60}")
    print("Multi-Timeframe Breakout Stocks")
    print(f"{'='*60}")

    for r in results:
        print(f"\n{r.ticker} ({r.name}): {r.current_price:,.0f} KRW")
        for cr in r.condition_results:
            if cr.matched:
                print(f"  - {cr.condition_name}")

    return results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("BREAKOUT SCREENING")
    print("="*60)

    run_bottom_breakout_screen()
    run_resistance_breakout_screen()
    run_multi_timeframe_breakout()
```

## Combining with Other Conditions

Breakout conditions work well when combined with other technical indicators.

```python
from screener import StockScreener
from screener.conditions.breakout import BreakoutWithVolumeCondition
from screener.conditions.rsi import RSIRangeCondition
from screener.conditions.ma import AboveMACondition

screener = StockScreener()

# Breakout + RSI not overbought + Above 20-day MA
screener.add_condition(BreakoutWithVolumeCondition(
    lookback_days=20,
    breakout_pct=5.0,
    volume_ratio=1.5
))
screener.add_condition(RSIRangeCondition(lower=40, upper=70))  # Not overbought
screener.add_condition(AboveMACondition(period=20))           # Trending up

results = screener.run(universe="KOSPI")
```

## Best Practices

1. **Use volume confirmation**: Raw breakouts often fail. `BreakoutWithVolumeCondition` filters for higher-quality signals.

2. **Fresh breakouts are timelier**: Use `FreshBreakoutCondition` or `fresh_only=True` to catch the first day of a move.

3. **Combine multiple timeframes**: Check for breakouts on 20, 60, and 120-day periods to find the strongest moves.

4. **Add trend filters**: Combine with `AboveMACondition` to ensure the broader trend supports the breakout.

5. **Watch for false breakouts**: Consider requiring `breakout_margin_pct > 0` for resistance breakouts to filter noise.

## Related

- [Screener Documentation](./SCREENER_README.md)
- [Korean Moving Average Screener](./KOREAN_MA_SCREENER.md)

---

# Korean Translation

## Breakout Conditions (돌파 조건)

주가 돌파 기반 종목 스크리닝을 위한 조건 클래스입니다.

### 개요

#### 돌파 매매란?

돌파 매매는 가격이 정의된 지지선 또는 저항선을 넘어설 때 포지션에 진입하는 전략입니다. 핵심 아이디어는 가격이 중요한 레벨을 돌파하면 해당 방향으로 모멘텀이 지속되는 경향이 있다는 것입니다.

**핵심 개념:**

- **바닥 돌파**: 최근 저점 대비 특정 퍼센트 상승, 하락 추세 반전 신호
- **저항선 돌파**: 최근 고점 위로 이동, 상승 추세 지속 가능성
- **신규 돌파**: 룩백 기간 내 이전에 발생하지 않은 첫 돌파
- **거래량 확인**: 평균 이상 거래량을 동반한 돌파, 신뢰도 향상

### 조건 클래스

#### BottomBreakoutCondition (바닥 돌파 조건)

N일 최저가 대비 X% 상승 감지.

**파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `lookback_days` | int | 20 | 바닥 탐색 기간 (일) |
| `breakout_pct` | float | 5.0 | 바닥 대비 상승률 (%) |

**사용 예시:**

```python
from screener.conditions.breakout import BottomBreakoutCondition

# 20일 저점 대비 5% 상승
condition = BottomBreakoutCondition(lookback_days=20, breakout_pct=5.0)
```

---

#### FreshBreakoutCondition (신규 돌파 조건)

첫 번째 돌파만 감지. 룩백 기간 내 이전 돌파가 있었던 종목은 제외.

**파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `lookback_days` | int | 20 | 바닥 탐색 기간 (일) |
| `breakout_pct` | float | 5.0 | 바닥 대비 상승률 (%) |

**돌파 상태:**

| 상태 | 의미 |
|------|------|
| `FRESH_BREAKOUT` | 오늘 첫 돌파 |
| `ALREADY_ABOVE` | 돌파선 위지만 이전에 돌파한 적 있음 |
| `BELOW` | 돌파선 아래 |

---

#### BreakoutWithVolumeCondition (거래량 확인 돌파)

가격 돌파와 거래량 급증을 함께 확인.

**파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `lookback_days` | int | 20 | 바닥 탐색 기간 (일) |
| `breakout_pct` | float | 5.0 | 바닥 대비 상승률 (%) |
| `volume_ratio` | float | 1.5 | 평균 대비 거래량 배수 |
| `volume_avg_days` | int | 10 | 평균 거래량 계산 기간 |
| `fresh_only` | bool | True | 신규 돌파만 매칭 |

**사용 예시:**

```python
from screener.conditions.breakout import BreakoutWithVolumeCondition

# 신규 돌파 + 1.5배 거래량
condition = BreakoutWithVolumeCondition(
    lookback_days=20,
    breakout_pct=5.0,
    volume_ratio=1.5,
    fresh_only=True
)
```

---

#### ResistanceBreakoutCondition (저항선 돌파 조건)

N일 저항선(최고가) 돌파 감지.

**파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `lookback_days` | int | 20 | 저항선 탐색 기간 (일) |
| `breakout_margin_pct` | float | 0.0 | 저항선 위 마진 (%) |

**사용 예시:**

```python
from screener.conditions.breakout import ResistanceBreakoutCondition

# 20일 고점 돌파
condition = ResistanceBreakoutCondition(lookback_days=20)

# 60일 고점 1% 위 돌파 (확인된 돌파)
condition = ResistanceBreakoutCondition(lookback_days=60, breakout_margin_pct=1.0)
```

### 모범 사례

1. **거래량 확인 사용**: 단순 돌파는 실패하는 경우가 많습니다. `BreakoutWithVolumeCondition`으로 고품질 신호를 필터링하세요.

2. **신규 돌파가 시의적절함**: `FreshBreakoutCondition` 또는 `fresh_only=True`를 사용하여 움직임의 첫 날을 포착하세요.

3. **다중 시간대 결합**: 20일, 60일, 120일 기간의 돌파를 확인하여 가장 강한 움직임을 찾으세요.

4. **추세 필터 추가**: `AboveMACondition`과 결합하여 더 넓은 추세가 돌파를 지지하는지 확인하세요.

5. **거짓 돌파 주의**: 저항선 돌파 시 `breakout_margin_pct > 0`을 요구하여 노이즈를 필터링하세요.
