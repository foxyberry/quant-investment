# Screener Conditions 아키텍처

이 문서는 `screener` 모듈에서 사용되는 조건 기반 종목 스크리닝 아키텍처를 설명합니다.

---

## 목차

1. [개요](#개요)
2. [사용 가능한 조건 클래스 (28개)](#사용-가능한-조건-클래스-28개)
3. [조건 조합 방법](#조건-조합-방법)
4. [새 조건 추가 방법](#새-조건-추가-방법)
5. [파라미터 설정 예시](#파라미터-설정-예시)
6. [사용 예시](#사용-예시)
7. [파일 구조](#파일-구조)

---

## 개요

스크리너 모듈은 **조건 기반 아키텍처**를 사용하여 각 스크리닝 기준을 `BaseCondition`을 상속하는 클래스로 구현합니다. 조건은 복합 연산자(AND, OR, NOT)를 사용하여 조합하여 복잡한 스크리닝 전략을 구성할 수 있습니다.

**핵심 구성 요소:**

- `BaseCondition` - 모든 조건의 추상 기본 클래스
- `ConditionResult` - 평가 결과를 담는 데이터클래스
- `StockScreener` - 조건을 주식 데이터에 대해 평가하는 메인 스크리너 클래스

---

## 사용 가능한 조건 클래스 (28개)

### 가격 조건 (price.py - 4개)

| 조건 | 설명 | 주요 파라미터 |
|------|------|---------------|
| `MinPriceCondition` | 최소 주가 조건 | `min_price` |
| `MaxPriceCondition` | 최대 주가 조건 | `max_price` |
| `PriceRangeCondition` | 가격 범위 조건 | `min_price`, `max_price` |
| `PriceChangeCondition` | 가격 변동률 조건 | `min_change_pct`, `max_change_pct`, `days` |

### 거래량 조건 (volume.py - 3개)

| 조건 | 설명 | 주요 파라미터 |
|------|------|---------------|
| `MinVolumeCondition` | 최소 거래량 조건 | `min_volume` |
| `VolumeAboveAvgCondition` | 평균 대비 거래량 조건 | `multiplier`, `period` |
| `VolumeSpikeCondition` | 거래량 급증 조건 | `multiplier`, `period` |

### 이동평균선 조건 (ma.py - 5개)

| 조건 | 설명 | 주요 파라미터 |
|------|------|---------------|
| `MATouchCondition` | 이평선 터치 (근접) | `period`, `threshold` |
| `AboveMACondition` | 이평선 위 | `period`, `min_distance_pct` |
| `BelowMACondition` | 이평선 아래 | `period`, `max_distance_pct` |
| `MACrossUpCondition` | 골든크로스 | `short_period`, `long_period`, `lookback_days` |
| `MACrossDownCondition` | 데드크로스 | `short_period`, `long_period`, `lookback_days` |

### RSI 조건 (rsi.py - 3개)

| 조건 | 설명 | 주요 파라미터 |
|------|------|---------------|
| `RSIOversoldCondition` | RSI 과매도 (기본 30 이하) | `threshold`, `period` |
| `RSIOverboughtCondition` | RSI 과매수 (기본 70 이상) | `threshold`, `period` |
| `RSIRangeCondition` | RSI 범위 내 | `lower`, `upper`, `period` |

### 축적 조건 (accumulation.py - 9개)

**Layer 1: 기본 조건**

| 조건 | 설명 | 주요 파라미터 |
|------|------|---------------|
| `BollingerWidthCondition` | BB 폭 수축 | `max_width_pct`, `period`, `std_dev` |
| `VolumeBelowAvgCondition` | 거래량 평균 이하 | `multiplier`, `period` |
| `PriceFlatCondition` | 가격 횡보 | `max_range_pct`, `period` |
| `OBVTrendCondition` | OBV 추세 방향 | `direction`, `lookback` |
| `StochasticLevelCondition` | 스토캐스틱 레벨 | `threshold`, `condition`, `k_period`, `d_period` |
| `VPCITrendCondition` | VPCI 추세 방향 | `direction`, `short_period`, `long_period`, `lookback` |

**Layer 2: 다이버전스 조건**

| 조건 | 설명 | 주요 파라미터 |
|------|------|---------------|
| `OBVDivergenceCondition` | OBV 다이버전스 (가격 횡보 + OBV 상승) | `price_max_range_pct`, `obv_min_change_pct`, `period` |
| `StochasticDivergenceCondition` | 스토캐스틱 다이버전스 (상승) | `k_period`, `d_period`, `lookback`, `divergence_threshold` |
| `VPCIDivergenceCondition` | VPCI 다이버전스 (가격 횡보 + VPCI 상승) | `price_max_range_pct`, `short_period`, `long_period`, `lookback` |

### 돌파 조건 (breakout.py - 4개)

| 조건 | 설명 | 주요 파라미터 |
|------|------|---------------|
| `BottomBreakoutCondition` | N일 바닥 대비 X% 돌파 | `lookback_days`, `breakout_pct` |
| `FreshBreakoutCondition` | 신규 돌파 (첫 돌파) | `lookback_days`, `breakout_pct` |
| `BreakoutWithVolumeCondition` | 거래량 확인 돌파 | `lookback_days`, `breakout_pct`, `volume_ratio`, `volume_avg_days`, `fresh_only` |
| `ResistanceBreakoutCondition` | 저항선 돌파 | `lookback_days`, `breakout_margin_pct` |

### 복합 조건 (composite.py - 3개)

| 조건 | 설명 | 주요 파라미터 |
|------|------|---------------|
| `AndCondition` | AND 조합 (모두 충족) | `conditions` (리스트) |
| `OrCondition` | OR 조합 (하나 이상 충족) | `conditions` (리스트) |
| `NotCondition` | NOT 반전 | `condition` |

---

## 조건 조합 방법

### AND 조합

모든 조건이 충족되어야 매칭:

```python
from screener.conditions import AndCondition, MinPriceCondition, MATouchCondition

combined = AndCondition([
    MinPriceCondition(5000),
    MATouchCondition(160),
])
```

### OR 조합

하나 이상의 조건이 충족되면 매칭:

```python
from screener.conditions import OrCondition, RSIOversoldCondition, MATouchCondition

combined = OrCondition([
    RSIOversoldCondition(30),
    MATouchCondition(200),
])
```

### NOT 조합

조건 결과를 반전:

```python
from screener.conditions import NotCondition, RSIOverboughtCondition

not_overbought = NotCondition(RSIOverboughtCondition(70))
```

### 중첩 조합

여러 레벨의 복잡한 조건:

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

## 새 조건 추가 방법

`BaseCondition`을 상속하고 3개의 필수 메서드를 구현합니다:

```python
from screener.conditions.base import BaseCondition, ConditionResult
import pandas as pd

class MyCondition(BaseCondition):
    def __init__(self, param: float = 10):
        self.param = param

    @property
    def name(self) -> str:
        """식별을 위한 고유 조건 이름"""
        return f"my_condition_{self.param}"

    @property
    def required_days(self) -> int:
        """필요한 과거 데이터 일수"""
        return 50

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        """
        조건 평가.

        Args:
            ticker: 종목 코드
            data: OHLCV DataFrame (컬럼: open, high, low, close, volume)

        Returns:
            매칭 상태와 세부 정보를 담은 ConditionResult
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

## 파라미터 설정 예시

### 가격 조건

```python
MinPriceCondition(min_price=5000)
MaxPriceCondition(max_price=100000)
PriceRangeCondition(min_price=5000, max_price=50000)
PriceChangeCondition(min_change_pct=-5.0, max_change_pct=5.0, days=5)
```

### 거래량 조건

```python
MinVolumeCondition(min_volume=100000)
VolumeAboveAvgCondition(multiplier=1.5, period=20)
VolumeSpikeCondition(multiplier=2.0, period=20)
```

### 이동평균선 조건

```python
MATouchCondition(period=160, threshold=0.02)  # +/-2% 범위 내
AboveMACondition(period=20, min_distance_pct=0.05)  # 5% 위
BelowMACondition(period=60, max_distance_pct=-0.05)  # 5% 아래
MACrossUpCondition(short_period=20, long_period=60, lookback_days=5)
MACrossDownCondition(short_period=20, long_period=60, lookback_days=5)
```

### RSI 조건

```python
RSIOversoldCondition(threshold=30, period=14)
RSIOverboughtCondition(threshold=70, period=14)
RSIRangeCondition(lower=40, upper=60, period=14)
```

### 축적 조건

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

### 돌파 조건

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

## 사용 예시

### 기본 스크리너 사용법

```python
from screener import StockScreener
from screener.conditions import MinPriceCondition, MATouchCondition

screener = StockScreener()
screener.add_condition(MinPriceCondition(5000))
screener.add_condition(MATouchCondition(160))

# KOSPI 유니버스에서 실행
results = screener.run(universe="KOSPI")

# 특정 종목에서 실행
results = screener.run(tickers=['005930.KS', '000660.KS'])

# 결과를 DataFrame으로 변환
df = screener.to_dataframe(results)
```

### 프리셋 사용

```python
from screener.presets import get_preset, list_presets
from screener import StockScreener

# 사용 가능한 프리셋 목록 확인
print(list_presets())
# ['ma_touch_160', 'ma_touch_120', 'ma_touch_200', 'oversold_bounce',
#  'golden_cross', 'dead_cross', 'volume_breakout', 'ma_touch_with_oversold',
#  'trend_following', 'value_dip', 'momentum_breakout',
#  'accumulation_basic', 'accumulation_obv', 'accumulation_full']

# 프리셋 사용
conditions = get_preset("accumulation_basic")
screener = StockScreener(conditions=conditions)
results = screener.run(universe="KOSPI")

# 커스텀 파라미터로 프리셋 사용
conditions = get_preset("accumulation_obv", min_price=10000, bb_max_width=12.0)
screener = StockScreener(conditions=conditions)
```

### 단일 종목 평가

```python
from screener import StockScreener
from screener.conditions import MinPriceCondition, RSIOversoldCondition

screener = StockScreener()
screener.add_condition(MinPriceCondition(5000))
screener.add_condition(RSIOversoldCondition(30))

result = screener.run_single("005930.KS")
print(f"매칭: {result.matched}")
print(f"현재가: {result.current_price}")
for cr in result.condition_results:
    print(f"  {cr.condition_name}: {cr.matched} - {cr.details}")
```

---

## 파일 구조

```
screener/
├── conditions/
│   ├── __init__.py        # 모든 조건 export
│   ├── base.py            # BaseCondition, ConditionResult, ConditionError
│   ├── price.py           # 가격 조건 (4개)
│   ├── volume.py          # 거래량 조건 (3개)
│   ├── ma.py              # 이동평균선 조건 (5개)
│   ├── rsi.py             # RSI 조건 (3개)
│   ├── accumulation.py    # 축적 조건 (9개)
│   ├── breakout.py        # 돌파 조건 (4개)
│   └── composite.py       # AND/OR/NOT 복합 조건 (3개)
├── stock_screener.py      # 메인 StockScreener 클래스
├── presets.py             # 미리 만들어진 조건 조합
└── kospi_fetcher.py       # KOSPI/KOSDAQ 종목 리스트 가져오기
```

---

## 관련 문서

- [Breakout Conditions](BREAKOUT_CONDITIONS.md) - 돌파 조건 상세 문서
- [Screener README](SCREENER_README.md) - 스크리너 일반 사용 가이드
- [Korean MA Screener](KOREAN_MA_SCREENER.md) - 한국 주식 이평선 터치 스크리너
