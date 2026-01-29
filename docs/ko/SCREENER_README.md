# 확장 가능한 스크리닝 시스템

> 이 문서는 [영문 버전](../SCREENER_README.md)의 번역입니다.

조건 클래스를 조합하여 유연하게 종목을 스크리닝하는 시스템입니다.

## 빠른 시작

```python
from screener import StockScreener, MinPriceCondition, MATouchCondition

# 스크리너 생성 및 조건 추가
screener = StockScreener()
screener.add_condition(MinPriceCondition(5000))          # 5000원 이상
screener.add_condition(MATouchCondition(period=160))     # 160일선 터치

# 스크리닝 실행
results = screener.run(universe="KOSPI")

# 결과 출력
for r in results:
    print(f"{r.ticker} ({r.name}): {r.current_price:,.0f}원")
```

## CLI 실행

```bash
# 프리셋 사용
python scripts/screening/run_screener.py --preset ma_touch_160

# 프리셋 목록 보기
python scripts/screening/run_screener.py --list-presets

# 단일 종목 검사
python scripts/screening/run_screener.py --ticker 035420.KS

# 유니버스 지정
python scripts/screening/run_screener.py --preset golden_cross --universe KOSDAQ
```

## 조건 클래스

### 가격 조건 (Price)

| 클래스 | 설명 | 파라미터 |
|--------|------|----------|
| `MinPriceCondition` | 최소 가격 | `min_price` |
| `MaxPriceCondition` | 최대 가격 | `max_price` |
| `PriceRangeCondition` | 가격 범위 | `min_price`, `max_price` |
| `PriceChangeCondition` | 가격 변동률 | `min_change`, `max_change`, `period` |

```python
from screener import MinPriceCondition, PriceRangeCondition

# 5000원 이상
MinPriceCondition(min_price=5000)

# 10000~50000원 범위
PriceRangeCondition(min_price=10000, max_price=50000)
```

### 거래량 조건 (Volume)

| 클래스 | 설명 | 파라미터 |
|--------|------|----------|
| `MinVolumeCondition` | 최소 거래량 | `min_volume` |
| `VolumeAboveAvgCondition` | 평균 대비 거래량 | `multiplier`, `period` |
| `VolumeSpikeCondition` | 거래량 급증 | `multiplier`, `period` |

```python
from screener import MinVolumeCondition, VolumeSpikeCondition

# 10만주 이상
MinVolumeCondition(min_volume=100000)

# 20일 평균 대비 2배 거래량
VolumeSpikeCondition(multiplier=2.0, period=20)
```

### 이동평균 조건 (MA)

| 클래스 | 설명 | 파라미터 |
|--------|------|----------|
| `MATouchCondition` | 이평선 터치 | `period`, `threshold` |
| `AboveMACondition` | 이평선 위 | `period`, `min_distance_pct` |
| `BelowMACondition` | 이평선 아래 | `period`, `max_distance_pct` |
| `MACrossUpCondition` | 골든크로스 | `short_period`, `long_period`, `lookback_days` |
| `MACrossDownCondition` | 데드크로스 | `short_period`, `long_period`, `lookback_days` |

```python
from screener import MATouchCondition, MACrossUpCondition, AboveMACondition

# 160일선 ±2% 이내
MATouchCondition(period=160, threshold=0.02)

# 20일/60일 골든크로스 (최근 5일 내)
MACrossUpCondition(short_period=20, long_period=60, lookback_days=5)

# 20일선 위 (이격률 0% 이상)
AboveMACondition(period=20)
```

### RSI 조건

| 클래스 | 설명 | 파라미터 |
|--------|------|----------|
| `RSIOversoldCondition` | 과매도 | `threshold`, `period` |
| `RSIOverboughtCondition` | 과매수 | `threshold`, `period` |
| `RSIRangeCondition` | RSI 범위 | `lower`, `upper`, `period` |

```python
from screener import RSIOversoldCondition, RSIRangeCondition

# RSI 30 이하 (과매도)
RSIOversoldCondition(threshold=30, period=14)

# RSI 40~60 범위
RSIRangeCondition(lower=40, upper=60)
```

### 복합 조건 (Composite)

| 클래스 | 설명 |
|--------|------|
| `AndCondition` | 모든 조건 충족 |
| `OrCondition` | 하나 이상 충족 |
| `NotCondition` | 조건 반전 |

```python
from screener import AndCondition, OrCondition, NotCondition

# AND: 모든 조건 충족
condition = AndCondition([
    MinPriceCondition(5000),
    MATouchCondition(160),
    RSIOversoldCondition(30)
])

# OR: 하나 이상 충족
condition = OrCondition([
    MATouchCondition(120),
    MATouchCondition(160),
    MATouchCondition(200)
])

# NOT: 조건 반전
condition = NotCondition(RSIOverboughtCondition(70))  # RSI 70 미만
```

## 프리셋

자주 사용하는 전략 조합입니다.

```python
from screener import get_preset, list_presets, StockScreener

# 프리셋 목록 확인
print(list_presets())
# ['ma_touch_160', 'ma_touch_120', 'ma_touch_200', 'oversold_bounce',
#  'golden_cross', 'dead_cross', 'volume_breakout', 'ma_touch_with_oversold',
#  'trend_following', 'value_dip', 'momentum_breakout']

# 프리셋 사용
screener = StockScreener(conditions=get_preset("ma_touch_160"))
results = screener.run(universe="KOSPI")

# 프리셋 + 추가 조건
screener = StockScreener(conditions=get_preset("golden_cross"))
screener.add_condition(MinVolumeCondition(50000))
```

### 프리셋 목록

| 이름 | 설명 |
|------|------|
| `ma_touch_160` | 160일선 터치 + 최소가격 |
| `ma_touch_120` | 120일선 터치 + 최소가격 |
| `ma_touch_200` | 200일선 터치 + 최소가격 |
| `oversold_bounce` | RSI 과매도 반등 |
| `golden_cross` | 20/60 골든크로스 |
| `dead_cross` | 20/60 데드크로스 |
| `volume_breakout` | 거래량 2배 돌파 |
| `ma_touch_with_oversold` | 이평선 터치 + RSI 과매도 |
| `trend_following` | 추세 추종 (이평선 위 + RSI 50+) |
| `value_dip` | 가치 저점 매수 |
| `momentum_breakout` | 모멘텀 돌파 |

## StockScreener API

### 생성자

```python
StockScreener(conditions=None, max_workers=10)
```

- `conditions`: 초기 조건 목록
- `max_workers`: 병렬 처리 워커 수

### 메서드

```python
# 조건 추가 (체이닝 지원)
screener.add_condition(condition) -> StockScreener

# 조건 초기화
screener.clear_conditions() -> StockScreener

# 스크리닝 실행
screener.run(universe="KOSPI", tickers=None, show_progress=True) -> List[ScreeningResult]

# 단일 종목 검사
screener.run_single(ticker) -> ScreeningResult

# DataFrame 변환
screener.to_dataframe(results) -> pd.DataFrame
```

### 유니버스

- `"KOSPI"`: KOSPI 대표 종목 (~35개)
- `"KOSDAQ"`: KOSDAQ 대표 종목 (~15개)
- `"ALL"`: KOSPI + KOSDAQ

직접 종목 지정:
```python
results = screener.run(tickers=["005930.KS", "035420.KS", "000660.KS"])
```

## ScreeningResult

```python
@dataclass
class ScreeningResult:
    ticker: str                           # 종목 코드
    name: str                             # 종목명
    matched: bool                         # 매칭 여부
    condition_results: List[ConditionResult]  # 조건별 결과
    current_price: Optional[float]        # 현재가
    volume: Optional[int]                 # 거래량
    timestamp: datetime                   # 검사 시간
```

```python
result = screener.run_single("035420.KS")

print(result.ticker)        # 035420.KS
print(result.name)          # NAVER
print(result.matched)       # True/False
print(result.current_price) # 284000.0

# 조건별 결과 확인
for cr in result.condition_results:
    print(f"{cr.condition_name}: {cr.matched}")
    print(f"  세부: {cr.details}")
```

## 커스텀 조건 만들기

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
        return 30  # 필요한 데이터 일수

    def evaluate(self, ticker: str, data: pd.DataFrame) -> ConditionResult:
        # 커스텀 로직
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

## 파일 구조

```
screener/
├── conditions/
│   ├── __init__.py      # 모듈 익스포트
│   ├── base.py          # BaseCondition, ConditionResult
│   ├── price.py         # 가격 조건
│   ├── volume.py        # 거래량 조건
│   ├── ma.py            # 이동평균 조건
│   ├── rsi.py           # RSI 조건
│   └── composite.py     # AND/OR/NOT
├── stock_screener.py    # StockScreener 클래스
├── presets.py           # 프리셋 전략
└── __init__.py          # 모듈 익스포트

scripts/screening/
└── run_screener.py      # CLI 스크립트
```

## 관련 링크

- [GitHub 이슈 #27](https://github.com/foxyberry/quant-investment/issues/27)
- [영문 문서](../SCREENER_README.md)
