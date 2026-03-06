# Condition 테스트 전략

> 날짜: 2026-03-06
> 상태: 초안
> 작성: Claude Code + Codex (토론 기반 설계)

## 1. 문제 정의

프로젝트에 `screener/conditions/` 19개 모듈에 걸쳐 **131개 condition 클래스** (164개 이상 등록 키)가 있다.

현재 테스트 격차:

| 문제 | 상세 |
|------|------|
| **28개 클래스 테스트 없음** | ma.py(5), rsi.py(3), breakout.py(4), composite.py(3), fundamental.py(15), price.py(4), volume.py(4) |
| **정확성 검증 없음** | 대부분 테스트가 `"key" in result.details`만 확인 — `result.matched` 미검증 |
| **parametrize 미사용** | 모든 테스트가 단일 시나리오 하드코딩 |
| **통합 테스트 없음** | 실제 `StockScreener` 파이프라인을 condition과 함께 테스트한 적 없음 |
| **회귀 스냅샷 없음** | 의도치 않은 동작 변경을 감지할 golden file 없음 |

요약: "실행된다"는 증명하지만 **"정확하게 판정한다"는 증명 못함**.

## 2. 설계 원칙

1. **테스트에서 지표를 재구현하지 않는다** — 결과가 자명한 극단 합성 패턴 사용
2. **목적별 레이어 분리** — 계약 vs 의미 vs 통합
3. **자동화로 스케일** — registry 기반 parametrize, condition별 수동 테스트 파일 아님
4. **유지보수 비용 최소화** — golden snapshot은 안정 필드만 저장

## 3. 테스트 아키텍처 (5 레이어)

### L0: 인터페이스 계약 테스트 (131개 전수)

**목적:** 모든 condition이 `BaseCondition` 계약을 준수하는지 확인.

**검증 항목:**
- `evaluate()`가 예외 없이 `ConditionResult` 반환
- `result.matched`가 `bool`
- `result.details`가 `dict`이고 기대 키 포함
- 데이터 부족 시 `matched=False` + `error`
- 입력 DataFrame 미변형 (방어적 복사 확인)
- `required_days`가 양의 정수 반환

**구현:**
- 단일 파일: `tests/test_condition_contract.py`
- `pytest.mark.parametrize`로 `get_condition_metadata()`에서 구동
- registry의 `test_defaults` 필드로 인스턴스 생성 파라미터 제공
- 기본값만 있는 단순 클래스는 `inspect.signature` fallback

**ROI:** 높은 발견율 / 낮은 비용 / 낮은 유지비

---

### L1: 의미 정확성 테스트 (그룹별 템플릿)

**목적:** `matched`가 True여야 할 때 True, False여야 할 때 False인지 검증.

**접근법 — 극단 패턴 방식:**
- RSI = 28.3을 계산하지 않음 → 50일 단조 하락 생성 → RSI는 **확실히** 30 미만
- 경계값(29-31) 회피, 극단(10/90)에서 넉넉한 마진으로 판정

**합성 데이터 템플릿:**

| 프로파일 | 형태 | 용도 |
|----------|------|------|
| `strong_uptrend` | 120일 단조 +2%/일 | MA 크로스 업, 모멘텀, 골든 크로스 |
| `strong_downtrend` | 120일 단조 -2%/일 | RSI 과매도, 데스 크로스, 손절 |
| `flat_consolidation` | 120일 ±0.1% 랜덤워크 | 볼린저 스퀴즈, 저변동성 |
| `volume_spike` | 100일 정상 + 20일 5배 거래량 | 거래량 급등, 돌파 |
| `gap_up` | 100일 횡보 + 10% 갭상승 | 갭 돌파, 오버나이트 수익률 |
| `v_recovery` | 60일 하락 + 60일 상승 | 수익률 반전, 바닥 돌파 |
| `high_pe_stock` | PER=50 펀더멘탈 데이터 | 고평가 필터 |
| `value_stock` | PER=8, PBR=0.5 | 가치주 필터 |

**condition별:** 최소 2개 시나리오 — `should_match` + `should_not_match`

**구현:**
- `tests/test_condition_semantics.py`
- 그룹별 parametrize + 시나리오 템플릿
- `tests/fixtures/synthetic_data.py` — 공유 데이터 팩토리

**ROI:** 최고 버그 발견율 / 중간 비용 / 중간 유지비

---

### L2: 차분 테스트 (표준 지표만)

**목적:** 독립 참조 구현과 교차 검증.

**범위:** 공식이 명확하고 참조 라이브러리가 있는 condition만:
- MA (SMA/EMA) — `pandas.DataFrame.rolling().mean()` / `.ewm().mean()`
- RSI — `pandas_ta.rsi()` 또는 수동 Wilder 평활
- MACD — `pandas_ta.macd()`
- ATR — `pandas_ta.atr()`
- 볼린저 밴드 — `pandas_ta.bbands()`
- 스토캐스틱 — `pandas_ta.stoch()`

**구현:**
- `tests/test_condition_differential.py`
- `result.details["rsi"]` vs `pandas_ta.rsi(data["close"])[-1]` 비교
- 허용 오차: `abs(ours - reference) < 0.01`

**ROI:** 심층 버그에 매우 높음 / 중~높은 비용 / 중간 유지비

---

### L3: 변형/속성 기반 테스트

**목적:** 기대값 계산 없이 로직 결함 탐지.

**속성:**
1. **스케일 불변성:** 모든 가격에 K를 곱해도 RSI, 퍼센트 기반 조건 불변
2. **단조성:** 강한 상승 추세에 상승일을 더 추가해도 모멘텀 조건이 True→False로 뒤집히지 않음
3. **접미사 안정성:** 앞에 burn-in 데이터를 추가해도 최신 평가 불변
4. **부정 일관성:** `rsi_oversold(threshold=30)`이 매칭되면 `rsi_overbought(threshold=30)`은 매칭 안 됨

**구현:**
- `tests/test_condition_properties.py`
- `hypothesis` 라이브러리로 자동 데이터 생성
- 핵심 5-10개 condition부터 시작, 점진 확대

**ROI:** 미묘한 버그에 높음 / 중~높은 비용 / 중간 유지비

---

### L4: 통합 스모크 테스트 (StockScreener 파이프라인)

**목적:** 실제 파이프라인에서 condition 조합이 올바르게 동작하는지 검증.

**시나리오:**
1. 단일 condition → 올바른 필터링
2. AND 조합 → 교집합
3. OR 조합 → 합집합
4. 펀더멘탈 + 기술적 혼합
5. 빈 유니버스 → 정상 처리

**구현:**
- `tests/test_screener_integration.py`
- 고정 합성 유니버스 (5-10개 종목, 특성 알려진)
- 고정 condition + 종목별 예상 pass/fail
- 최종 매칭 집합 == 예상 집합 검증

**ROI:** 파이프라인 버그에 높음 / 중간 비용 / 중간 유지비

---

### L5: Golden 스냅샷 (회귀 감지)

**목적:** 모든 condition에 대한 의도치 않은 동작 변경 감지.

**저장 내용:**
```json
{
  "version": 1,
  "generated_at": "2026-03-06T00:00:00Z",
  "fixture": "standard_120d_mixed",
  "items": [
    {
      "condition_key": "rsi_oversold",
      "params": {"rsi_period": 14, "threshold": 30},
      "matched": true,
      "details_subset": {"rsi": 12.34}
    }
  ]
}
```

**저장 위치:** `tests/fixtures/golden/conditions_snapshot.v1.json`

**업데이트 워크플로:**
1. CI 기본: 불일치 → 테스트 실패
2. 의도적 변경: `pytest --update-golden`으로 재생성
3. PR에 스냅샷 변경 사유 필수 (조건 로직 변경 / 버그 수정 / 파라미터 변경)

**수치 허용 오차:** 비교 전 소수점 4자리로 반올림.

**ROI:** 회귀에 매우 높음 / 낮은 비용 / 중간 유지비 (업데이트 프로세스)

---

## 4. 컬럼 의존성 관리

각 condition은 다른 DataFrame 컬럼에 의존한다. 이를 명시적으로 선언해야 한다.

**Registry 확장:**
```python
@register_condition(
    key="turnover_ratio_min",
    ...,
    test_defaults={"min_turnover_ratio": 0.01},
    test_profile="price_volume_shares",
    required_columns=["close", "volume", "shares_outstanding"],
)
```

**테스트 프로파일 → fixture 팩토리:**

| 프로파일 | 컬럼 |
|----------|------|
| `price_only` | open, high, low, close |
| `price_volume` | open, high, low, close, volume |
| `price_volume_shares` | + shares_outstanding |
| `fundamental` | + pe_ratio, pb_ratio, market_cap, ... |
| `fundamental_statements` | + revenue, net_income, total_assets, ... |

`tests/fixtures/synthetic_data.py`가 `build_fixture(profile, shape, days)` 제공.

---

## 5. 구현 로드맵

### Phase 1: 기반 구축 (즉시)

| 작업 | 파일 | 설명 |
|------|------|------|
| registry에 `test_defaults` 추가 | `screener/conditions/registry.py` + 전 모듈 | 테스트 인스턴스화용 기본 파라미터 |
| 합성 데이터 팩토리 | `tests/fixtures/synthetic_data.py` | 프로파일+형태별 공유 데이터 빌더 |
| L0 계약 테스트 | `tests/test_condition_contract.py` | 131개 전수 parametrize 테스트 |
| 누락 28개 채우기 | 동일 파일 또는 `test_condition_semantics.py` | 최소 L0 + L1 |

**완료 기준:** `pytest tests/test_condition_contract.py` — 131/131 통과

### Phase 2: 정확성 확보 (Phase 1 이후 1-2주)

| 작업 | 파일 | 설명 |
|------|------|------|
| L1 의미 테스트 | `tests/test_condition_semantics.py` | 극단 패턴으로 condition별 True/False 쌍 |
| 기존 테스트 업그레이드 | `tests/test_*_batch*.py` | detail-only → matched 검증 추가 |
| L4 통합 스모크 | `tests/test_screener_integration.py` | 5개 파이프라인 시나리오 |
| L5 golden 스냅샷 v1 | `tests/fixtures/golden/`, `tests/test_condition_golden.py` | 기준 스냅샷 |

**완료 기준:** 모든 condition에 최소 1 True + 1 False 의미 테스트

### Phase 3: 심화 검증 (지속)

| 작업 | 파일 | 설명 |
|------|------|------|
| L2 차분 테스트 | `tests/test_condition_differential.py` | MA/RSI/MACD/ATR/BB/Stoch vs pandas_ta |
| L3 속성 기반 | `tests/test_condition_properties.py` | hypothesis 기반 불변성 테스트 |
| CI 분리 | `.github/workflows/` | PR: L0+L1+L4 스모크 / 야간: L2+L3+전체 L4+golden |

**완료 기준:** 표준 지표가 참조 구현과 허용 오차 내 일치

---

## 6. 파일 구조

```
tests/
├── fixtures/
│   ├── synthetic_data.py          # 공유 데이터 팩토리
│   └── golden/
│       └── conditions_snapshot.v1.json
├── test_condition_contract.py     # L0: 131개 전수
├── test_condition_semantics.py    # L1: True/False 쌍
├── test_condition_differential.py # L2: pandas_ta 대비
├── test_condition_properties.py   # L3: hypothesis
├── test_screener_integration.py   # L4: 파이프라인 스모크
├── test_condition_golden.py       # L5: 스냅샷 회귀
└── test_*_batch*.py               # 기존 (현장 업그레이드)
```

---

## 7. 비목표

- condition별 100% 분기 커버리지 (수확 체감)
- CI에서 실제 시장 데이터 테스트 (불안정, 느림)
- 기존 batch 테스트 파일 교체 (현장 업그레이드)
- condition 결과의 UI 렌더링 테스트 (별도 관심사)
