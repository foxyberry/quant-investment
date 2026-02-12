# 매집 구간 스크리닝

조용한 매집 구간에 있는 종목을 탐지하는 스크리닝 기능 사용법입니다.

---

## 목차

1. [매집 구간이란?](#매집-구간이란)
2. [기술적 신호](#기술적-신호)
3. [프리셋](#프리셋)
4. [사용법](#사용법)
5. [파라미터](#파라미터)
6. [결과 해석](#결과-해석)
7. [투자 전략](#투자-전략)
8. [주의사항](#주의사항)
9. [코드 예제](#코드-예제)

---

## 매집 구간이란?

**매집(Accumulation)**은 세력이나 기관투자자가 가격을 크게 움직이지 않으면서 조용히 주식을 모으는 구간입니다.

### 특징

| 지표 | 매집 구간 특성 |
|------|---------------|
| 변동성 | 낮음 (좁은 가격 범위) |
| 거래량 | 평균 이하 |
| 가격 움직임 | 횡보/박스권 |
| 관심도 | 낮음 |

### 왜 중요한가

- 매집 종료 후 상승 돌파 가능성이 높음
- 대중보다 먼저 진입 가능
- 박스권 하단에서 손절 설정으로 리스크 제한 가능

---

## 기술적 신호

### 볼린저밴드 수축 (Bollinger Band Squeeze)

변동성이 낮아지면 볼린저밴드 폭이 좁아집니다.

```
상단밴드 ----====----
가격          ====
하단밴드 ----====----
              ^수축^
```

- **조건**: 밴드 폭이 임계값 이하 (기본: 15%)
- **해석**: 수축 후 폭발적 움직임 예상
- **파라미터**: `bb_max_width` (기본값: 15.0%)

### 거래량 감소 (Volume Decline)

평균 이하의 거래량은 대중의 관심이 낮음을 의미합니다.

- **조건**: 거래량이 이동평균 이하
- **해석**: 낮은 참여도 = 조용한 매집 가능
- **파라미터**: `volume_multiplier` (기본값: 1.0 = 평균 이하)

### 가격 횡보 (Price Consolidation)

가격이 좁은 범위 내에서 움직이며 매수/매도 균형 상태입니다.

- **조건**: 20일 가격 변동폭이 임계값 이하
- **해석**: 좁은 범위 = 가격 충격 없이 매집
- **파라미터**: `price_max_range` (기본값: 10.0%)

### OBV 다이버전스 (가장 중요)

**OBV(On-Balance Volume)**는 누적 매수/매도 압력을 추적합니다.

```
가격:  ----====----  (횡보)
OBV:   ____/^^^^^^   (상승)
       = 상승 다이버전스
```

- **조건**: 가격은 횡보인데 OBV가 상승
- **해석**: 가격 변동 없이 순매수 우위 = 매집
- **신뢰도**: 가장 신뢰할 수 있는 매집 신호

### 스토캐스틱 다이버전스 (Stochastic Divergence)

가격 움직임에 숨겨진 모멘텀 변화를 감지합니다.

- **조건**: 가격은 저점을 낮추는데 스토캐스틱은 저점을 높임
- **해석**: 매도 압력 약화
- **신호 유형**: 상승 다이버전스

### VPCI 다이버전스 (Volume-Price Confirmation Indicator)

가격 움직임과 거래량의 관계를 분석합니다.

- **조건**: 가격과 VPCI 간 양의 다이버전스
- **해석**: 거래량이 매집을 확인
- **신호 유형**: 매집 확인 신호

---

## 프리셋

| 프리셋 | 조건 | 신뢰도 | 결과 수 | 추천 상황 |
|--------|------|--------|---------|-----------|
| `accumulation_basic` | BB수축 + 거래량감소 + 가격횡보 | 낮음 | 많음 (~200개) | 넓은 범위 탐색 |
| `accumulation_obv` | basic + OBV 다이버전스 | 중간 | 적음 | **가장 추천** |
| `accumulation_full` | basic + 아무 다이버전스 (OBV/Stoch/VPCI) | 중간 | 적음 | 다양한 신호 포착 |

### 프리셋 상세

**accumulation_basic**
- 초기 스크리닝용 광범위 필터
- 높은 거짓 양성률
- 탐색용으로 사용, 최종 결정에는 부적합

**accumulation_obv** (추천)
- OBV 다이버전스 조건 추가
- 매집 탐지에 가장 신뢰할 수 있는 단일 지표
- 품질과 수량의 최적 균형

**accumulation_full**
- 세 가지 다이버전스 유형 중 하나 필요
- OBV만으로 놓칠 수 있는 신호 포착
- 종합적인 스캔에 적합

---

## 사용법

### 기본 명령어

```bash
# 단일 종목 분석
python scripts/screening/accumulation_screen.py --ticker 005930.KS

# OBV 다이버전스 프리셋 (추천)
python scripts/screening/accumulation_screen.py --preset accumulation_obv

# KOSDAQ 스크리닝
python scripts/screening/accumulation_screen.py --preset accumulation_obv --universe KOSDAQ

# 전체 한국 주식
python scripts/screening/accumulation_screen.py --preset accumulation_obv --universe ALL
```

### 더 엄격한 조건

```bash
# 더 좁은 볼린저밴드 (15% 대신 8%)
python scripts/screening/accumulation_screen.py --preset accumulation_basic --bb-width 8.0

# 더 낮은 거래량 기준 (평균의 70%)
python scripts/screening/accumulation_screen.py --preset accumulation_basic --volume-mult 0.7

# 여러 엄격한 파라미터 조합
python scripts/screening/accumulation_screen.py --preset accumulation_obv \
    --bb-width 8.0 \
    --volume-mult 0.7 \
    --price-range 5.0 \
    --min-price 10000
```

### 사용 가능한 프리셋 목록

```bash
python scripts/screening/accumulation_screen.py --list-presets
```

---

## 파라미터

| 파라미터 | 기본값 | 설명 | 엄격한 값 |
|----------|--------|------|-----------|
| `--min-price` | 5000 | 최소 주가 (원) | 10000 |
| `--bb-width` | 15.0 | 볼린저밴드 폭 최대 (%) | 8.0 |
| `--volume-mult` | 1.0 | 거래량 배수 (1.0 = 평균) | 0.7 |
| `--price-range` | 10.0 | 20일 가격 변동폭 최대 (%) | 5.0 |
| `--universe` | KOSPI | 시장 (KOSPI/KOSDAQ/ALL) | - |
| `--preset` | accumulation_basic | 프리셋 이름 | accumulation_obv |

### 파라미터 조정 가이드

| 목표 | 조정 방법 |
|------|-----------|
| 더 적고 높은 품질의 결과 | `--bb-width`, `--volume-mult`, `--price-range` 낮추기 |
| 더 많은 탐색 결과 | 임계값 높이기 |
| 저가주 제외 | `--min-price` 높이기 |
| 다른 시장 | `--universe` 변경 |

---

## 결과 해석

### 출력 예시

```
005930 (삼성전자)
  Price: 72,000
  [PASS] min_price_5000
  [PASS] bb_width_15.0
  [PASS] volume_below_avg_1.0
  [PASS] price_flat_10.0
  [PASS] obv_divergence
```

### 결과 이해하기

| 상태 | 의미 |
|------|------|
| `[PASS]` | 조건 충족 |
| `[FAIL]` | 조건 미충족 |

### 신호 강도 순위

1. **모든 PASS + OBV 다이버전스**: 가장 강력한 매집 신호
2. **모든 PASS (basic만)**: 매집 가능성, 추가 확인 필요
3. **일부 FAIL**: 매집 구간 아님

---

## 투자 전략

### 진입 전략

1. **스크리닝**: `accumulation_obv` 프리셋으로 후보 선정
2. **확인**: 차트에서 지지/저항선 확인
3. **검증**: 추가 신호 확인 (뉴스, 펀더멘털)
4. **진입**:
   - 옵션 A: 박스권 상단 돌파 시 매수
   - 옵션 B: 박스권 내 지지선 부근에서 분할 매수

### 손절 기준

| 조건 | 행동 |
|------|------|
| 박스권 하단 이탈 | 포지션 청산 |
| 거래량 급증 + 하락 | 청산 (분배 신호) |
| 가격 횡보 중 OBV 하락 | 포지션 축소 |

### 익절 기준

| 조건 | 행동 |
|------|------|
| 볼린저밴드 상단 터치 | 일부 익절 고려 |
| 거래량 급증 + 상승 | 돌파 완성, 트레일링 스탑 |
| 목표가 도달 (박스권 높이만큼) | 익절 |

### 포지션 사이징

```
거래당 리스크: 포트폴리오의 1-2%
손절가: 박스권 하단 바로 아래
포지션 크기 = (리스크 금액) / (진입가 - 손절가)
```

---

## 주의사항

### 거짓 신호

- 모든 매집 구간이 상승 돌파로 이어지지 않음
- 하락 돌파도 가능 (분배 구간일 수 있음)
- 항상 손절을 설정할 것

### 보완 분석 필요

| 분석 유형 | 목적 |
|-----------|------|
| 펀더멘털 | 회사 건전성 확인 |
| 뉴스/심리 | 향후 촉매 확인 |
| 섹터/업종 | 업종 추세와 일치 여부 |
| 시장 상황 | 강세/약세장 맥락 |

### 한계

- 스크리닝은 후보 발굴용이지 보장이 아님
- 최종 결정은 직접 판단 필요
- 과거 패턴이 반복되지 않을 수 있음

---

## 코드 예제

### Python API 사용

```python
from screener import StockScreener, get_preset

# 프리셋 사용
conditions = get_preset("accumulation_obv")
screener = StockScreener(conditions=conditions)
results = screener.run(universe="KOSPI")

# 결과 출력
for r in results:
    print(f"{r.ticker} ({r.name}) - {r.current_price:,}원")

# DataFrame 변환
df = screener.to_dataframe(results)
print(df[['ticker', 'name', 'current_price', 'matched']])
```

### 커스텀 조건

```python
from screener import (
    StockScreener,
    MinPriceCondition,
    BollingerWidthCondition,
    VolumeBelowAvgCondition,
    OBVDivergenceCondition,
)

# 커스텀 스크리너 구성
conditions = [
    MinPriceCondition(10000),           # 최소 10,000원
    BollingerWidthCondition(8.0),       # 좁은 수축 (8%)
    VolumeBelowAvgCondition(0.7),       # 거래량 < 평균의 70%
    OBVDivergenceCondition(),           # OBV 상승 다이버전스
]

screener = StockScreener(conditions=conditions)
results = screener.run(universe="KOSPI")
```

### 단일 종목 분석

```python
from screener import StockScreener, get_preset

conditions = get_preset("accumulation_obv")
screener = StockScreener(conditions=conditions)

# 단일 종목 분석
result = screener.run_single("005930.KS")

print(f"종목: {result.name}")
print(f"가격: {result.current_price:,}")
print(f"매칭: {result.matched}")

for cr in result.condition_results:
    status = "PASS" if cr.matched else "FAIL"
    print(f"  [{status}] {cr.condition_name}")
    for k, v in cr.details.items():
        print(f"      {k}: {v}")
```

### DataFrame으로 일괄 처리

```python
from screener import StockScreener, get_preset
import pandas as pd

# 스크리닝 실행
conditions = get_preset("accumulation_obv")
screener = StockScreener(conditions=conditions)
results = screener.run(universe="ALL")

# 분석을 위해 DataFrame 변환
df = screener.to_dataframe(results)

# 필터링 및 정렬
df_sorted = df.sort_values('current_price', ascending=False)

# CSV로 내보내기
df_sorted.to_csv('accumulation_candidates.csv', index=False)
```

---

## 관련 문서

- [스크리너 조건 아키텍처](SCREENER_CONDITIONS.md) - 28개 조건 클래스 전체
- [돌파 조건](BREAKOUT_CONDITIONS.md) - 매집 후 돌파 탐지

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-02-12 | 최초 문서 작성 |
