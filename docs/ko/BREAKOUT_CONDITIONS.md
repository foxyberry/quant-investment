# Breakout Conditions (돌파 조건)

주가 돌파 기반 종목 스크리닝을 위한 조건 클래스입니다.

> English version: [docs/BREAKOUT_CONDITIONS.md](../BREAKOUT_CONDITIONS.md)

## 개요

### 돌파 매매란?

돌파 매매는 가격이 정의된 지지선 또는 저항선을 넘어설 때 포지션에 진입하는 전략입니다. 핵심 아이디어는 가격이 중요한 레벨을 돌파하면 해당 방향으로 모멘텀이 지속되는 경향이 있다는 것입니다.

**핵심 개념:**

- **바닥 돌파**: 최근 저점 대비 특정 퍼센트 상승, 하락 추세 반전 신호
- **저항선 돌파**: 최근 고점 위로 이동, 상승 추세 지속 가능성
- **신규 돌파**: 룩백 기간 내 이전에 발생하지 않은 첫 돌파
- **거래량 확인**: 평균 이상 거래량을 동반한 돌파, 신뢰도 향상

### 조건 선택 가이드

| 시나리오 | 사용할 조건 |
|----------|------------|
| 최근 저점에서 반등하는 종목 찾기 | `BottomBreakoutCondition` |
| 돌파 첫 날 포착 | `FreshBreakoutCondition` |
| 거래량 확인된 돌파만 필터링 | `BreakoutWithVolumeCondition` |
| 신고가 후보 종목 찾기 | `ResistanceBreakoutCondition` |

## 조건 클래스

### BottomBreakoutCondition (바닥 돌파 조건)

N일 최저가 대비 X% 상승을 감지합니다.

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

# 60일 저점 대비 10% 상승 (더 큰 스윙)
condition = BottomBreakoutCondition(lookback_days=60, breakout_pct=10.0)
```

**결과 상세 정보:**

```python
{
    "current_price": 52500.0,        # 현재가
    "bottom_price": 48000.0,         # 바닥 가격
    "bottom_date": "2024-01-15",     # 바닥 일자
    "breakout_price": 50400.0,       # 돌파 기준가 (바닥 * 1.05)
    "price_from_bottom_pct": 9.38,   # 바닥 대비 실제 상승률
    "lookback_days": 20,
    "breakout_pct": 5.0
}
```

---

### FreshBreakoutCondition (신규 돌파 조건)

첫 번째 돌파만 감지합니다. 룩백 기간 내 이전에 돌파한 적이 있는 종목은 제외됩니다.

**파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `lookback_days` | int | 20 | 바닥 탐색 기간 (일) |
| `breakout_pct` | float | 5.0 | 바닥 대비 상승률 (%) |

**사용 예시:**

```python
from screener.conditions.breakout import FreshBreakoutCondition

# 20일 저점 대비 5% 첫 돌파
condition = FreshBreakoutCondition(lookback_days=20, breakout_pct=5.0)
```

**돌파 상태 값:**

| 상태 | 의미 |
|------|------|
| `FRESH_BREAKOUT` | 오늘 첫 돌파 |
| `ALREADY_ABOVE` | 돌파선 위에 있지만 이전에 돌파한 적 있음 |
| `BELOW` | 돌파선 아래에 있음 |

**결과 상세 정보:**

```python
{
    "current_price": 52500.0,
    "bottom_price": 48000.0,
    "bottom_date": "2024-01-15",
    "breakout_price": 50400.0,
    "price_from_bottom_pct": 9.38,
    "breakout_status": "FRESH_BREAKOUT",  # 돌파 상태
    "is_breakout_today": True,            # 오늘 돌파 여부
    "has_broken_before": False            # 이전 돌파 여부
}
```

---

### BreakoutWithVolumeCondition (거래량 확인 돌파)

가격 돌파와 거래량 급증을 함께 확인합니다. 가격 돌파와 거래량 스파이크 모두 충족해야 합니다.

**파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `lookback_days` | int | 20 | 바닥 탐색 기간 (일) |
| `breakout_pct` | float | 5.0 | 바닥 대비 상승률 (%) |
| `volume_ratio` | float | 1.5 | 평균 대비 거래량 배수 (1.5 = 150%) |
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
    volume_avg_days=10,
    fresh_only=True
)

# 모든 돌파 (신규뿐 아니라) + 2배 거래량
condition = BreakoutWithVolumeCondition(
    lookback_days=20,
    breakout_pct=5.0,
    volume_ratio=2.0,
    fresh_only=False
)
```

**결과 상세 정보:**

```python
{
    "current_price": 52500.0,
    "bottom_price": 48000.0,
    "bottom_date": "2024-01-15",
    "breakout_price": 50400.0,
    "price_from_bottom_pct": 9.38,
    "is_breakout_today": True,
    "is_fresh": True,
    "current_volume": 1500000,         # 현재 거래량
    "avg_volume": 800000,              # 평균 거래량
    "volume_ratio": 1.875,             # 실제 비율
    "required_volume_ratio": 1.5,      # 기준 비율
    "is_volume_spike": True            # 거래량 스파이크 여부
}
```

---

### ResistanceBreakoutCondition (저항선 돌파 조건)

N일 저항선(최고가)을 돌파했는지 감지합니다.

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

# 52주 신고가 돌파
condition = ResistanceBreakoutCondition(lookback_days=252)
```

**결과 상세 정보:**

```python
{
    "current_price": 55000.0,
    "resistance_price": 54000.0,                # 저항선 가격
    "resistance_date": "2024-01-10",            # 저항선 일자
    "breakout_price": 54000.0,                  # 돌파 기준가
    "distance_from_resistance_pct": 1.85,       # 저항선 대비 거리
    "lookback_days": 20
}
```

## 스크리닝 예제 스크립트

여러 돌파 조건을 결합한 스크리닝 예제입니다.

```python
#!/usr/bin/env python
"""
돌파 스크리닝 예제
신규 거래량 확인 돌파 종목 찾기
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
    """바닥 돌파 종목 스크리닝."""
    screener = StockScreener()

    # 기본 필터
    screener.add_condition(MinPriceCondition(min_price=5000))
    screener.add_condition(MinVolumeCondition(min_volume=100000))

    # 신규 돌파 + 거래량 확인
    screener.add_condition(BreakoutWithVolumeCondition(
        lookback_days=20,
        breakout_pct=5.0,
        volume_ratio=1.5,
        fresh_only=True
    ))

    results = screener.run(universe="KOSPI")

    print(f"\n{'='*60}")
    print("바닥 돌파 종목 (신규 + 거래량)")
    print(f"{'='*60}")

    for r in results:
        details = r.condition_results[-1].details
        print(f"\n{r.ticker} ({r.name})")
        print(f"  현재가: {r.current_price:,.0f}원")
        print(f"  바닥가: {details['bottom_price']:,.0f} ({details['bottom_date']})")
        print(f"  바닥 대비 상승률: {details['price_from_bottom_pct']:.1f}%")
        print(f"  거래량 배수: {details['volume_ratio']:.2f}배")

    return results


def run_resistance_breakout_screen():
    """저항선 돌파 종목 스크리닝."""
    screener = StockScreener()

    # 기본 필터
    screener.add_condition(MinPriceCondition(min_price=5000))

    # 20일 저항선 돌파
    screener.add_condition(ResistanceBreakoutCondition(
        lookback_days=20,
        breakout_margin_pct=0.5  # 저항선 0.5% 위
    ))

    results = screener.run(universe="KOSPI")

    print(f"\n{'='*60}")
    print("저항선 돌파 종목")
    print(f"{'='*60}")

    for r in results:
        details = r.condition_results[-1].details
        print(f"\n{r.ticker} ({r.name})")
        print(f"  현재가: {r.current_price:,.0f}원")
        print(f"  저항선: {details['resistance_price']:,.0f} ({details['resistance_date']})")
        print(f"  저항선 대비: {details['distance_from_resistance_pct']:.1f}%")

    return results


def run_multi_timeframe_breakout():
    """다중 시간대 돌파 스크리닝."""
    screener = StockScreener()

    screener.add_condition(MinPriceCondition(min_price=5000))

    # 여러 시간대 중 하나라도 돌파하면 매칭
    multi_breakout = OrCondition([
        FreshBreakoutCondition(lookback_days=20, breakout_pct=5.0),
        FreshBreakoutCondition(lookback_days=60, breakout_pct=10.0),
        ResistanceBreakoutCondition(lookback_days=60),
    ])
    screener.add_condition(multi_breakout)

    results = screener.run(universe="KOSPI")

    print(f"\n{'='*60}")
    print("다중 시간대 돌파 종목")
    print(f"{'='*60}")

    for r in results:
        print(f"\n{r.ticker} ({r.name}): {r.current_price:,.0f}원")
        for cr in r.condition_results:
            if cr.matched:
                print(f"  - {cr.condition_name}")

    return results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("돌파 스크리닝")
    print("="*60)

    run_bottom_breakout_screen()
    run_resistance_breakout_screen()
    run_multi_timeframe_breakout()
```

## 다른 조건과 결합하기

돌파 조건은 다른 기술적 지표와 결합할 때 더 효과적입니다.

```python
from screener import StockScreener
from screener.conditions.breakout import BreakoutWithVolumeCondition
from screener.conditions.rsi import RSIRangeCondition
from screener.conditions.ma import AboveMACondition

screener = StockScreener()

# 돌파 + RSI 과매수 아님 + 20일 이평선 위
screener.add_condition(BreakoutWithVolumeCondition(
    lookback_days=20,
    breakout_pct=5.0,
    volume_ratio=1.5
))
screener.add_condition(RSIRangeCondition(lower=40, upper=70))  # 과매수 아님
screener.add_condition(AboveMACondition(period=20))           # 상승 추세

results = screener.run(universe="KOSPI")
```

## 모범 사례

1. **거래량 확인 사용**: 단순 돌파는 실패하는 경우가 많습니다. `BreakoutWithVolumeCondition`으로 고품질 신호를 필터링하세요.

2. **신규 돌파가 시의적절함**: `FreshBreakoutCondition` 또는 `fresh_only=True`를 사용하여 움직임의 첫 날을 포착하세요.

3. **다중 시간대 결합**: 20일, 60일, 120일 기간의 돌파를 확인하여 가장 강한 움직임을 찾으세요.

4. **추세 필터 추가**: `AboveMACondition`과 결합하여 더 넓은 추세가 돌파를 지지하는지 확인하세요.

5. **거짓 돌파 주의**: 저항선 돌파 시 `breakout_margin_pct > 0`을 요구하여 노이즈를 필터링하세요.

## 관련 문서

- [스크리너 문서](./SCREENER_README.md)
- [한국 주식 이평선 스크리너](./KOREAN_MA_SCREENER.md)
