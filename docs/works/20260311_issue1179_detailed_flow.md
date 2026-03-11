# #1179 — 수급 디테일 강화 (재정의: 신뢰 기반 파생지표)

## 목표
기존 외국인/기관/개인 현물 순매수 데이터를 기반으로 **해석력을 높이는 파생지표**를 추가한다.
새로운 외부 데이터 소스 없이, 기존 Naver trend API 데이터에서 파생 가능한 지표만 구현한다.

## Codex 방향 검증 결과
- ❌ `futures_foreign_estimate` → 중복(KODEX200 이미 표시) + 추정치 신뢰도 문제 → 사용자 노출 보류
- ❌ 프로그램 매매 → 안정적 데이터 소스 없음
- ❌ 업종별 수급 → API 미발견
- ✅ **기존 데이터 기반 파생지표** → 추가 API 호출 없이 해석력 강화

## 구현할 파생지표 (3개)

### 1. 외국인 vs 기관 동행/충돌 상태
- 둘 다 순매수 → `aligned_buy` (동행 매수)
- 둘 다 순매도 → `aligned_sell` (동행 매도)
- 외국인 매수 + 기관 매도 → `foreign_lead` (외국인 주도)
- 외국인 매도 + 기관 매수 → `institution_lead` (기관 주도)
- 한쪽 null → `unknown`

### 2. 수급 강도 시그널
- 외국인 순매수 규모를 구간화:
  - |순매수| > 5000억 → `strong`
  - |순매수| > 1000억 → `moderate`
  - else → `weak`

### 3. KOSDAQ 동시 수집
- 기존 KOSPI만 수집 → KOSDAQ도 병행 수집
- 수급 카드에 KOSPI/KOSDAQ 탭 또는 비교 표시

## 변경 파일

| File | Team | Action |
|------|------|--------|
| `api/services/investor_flow_collector.py` | 서버 | KOSDAQ 수집 추가, 두 시장 동시 저장 |
| `api/services/macro_market_service.py` | 서버 | flow 해석 필드 추가 (alignment, strength) |
| `api/schemas/market.py` | 서버 | 스키마 필드 추가 |
| `web/src/lib/types.ts` | 프론트 | TS 타입 동기화 |
| `web/src/app/[locale]/macro/page.tsx` | 프론트 | 수급 카드 확장 (해석 뱃지, KOSDAQ) |
| `web/messages/{en,ko,zh}.json` | 프론트 | i18n |

## 상세 구현

### Backend Step 1: `investor_flow_collector.py` — KOSDAQ 추가

1. `run_investor_flow_collector()`에서 KOSPI + KOSDAQ 둘 다 수집
2. 출력 JSON 스키마:
   ```json
   {
     "market": "KOSPI",
     "foreign_net": 782100000000,
     "institution_net": -508600000000,
     "individual_net": -256300000000,
     "kosdaq": {
       "foreign_net": ...,
       "institution_net": ...,
       "individual_net": ...
     },
     "window_min": null,
     "updated_at": "..."
   }
   ```

### Backend Step 2: `macro_market_service.py` — 파생지표 계산

3. `_get_flow_snapshot()` 확장:
   - `alignment`: 외국인 vs 기관 동행/충돌 상태 계산
   - `foreign_strength`: 외국인 수급 강도 (strong/moderate/weak)
   - `kosdaq_foreign_net`, `kosdaq_institution_net`, `kosdaq_individual_net` 전달

### Backend Step 3: `api/schemas/market.py`

4. `MacroInvestorFlowSnapshot` 확장:
   ```python
   alignment: Optional[str] = Field(None)  # aligned_buy/aligned_sell/foreign_lead/institution_lead
   foreign_strength: Optional[str] = Field(None)  # strong/moderate/weak
   kosdaq_foreign_net: Optional[float] = Field(None)
   kosdaq_institution_net: Optional[float] = Field(None)
   kosdaq_individual_net: Optional[float] = Field(None)
   ```

### Frontend Step 4: 타입 + UI

5. `types.ts` — 위 필드들 TS 타입 추가

6. `macro/page.tsx` — 수급 카드 확장:
   - 외국인/기관 동행 상태 뱃지 (상단에 칩으로 표시)
   - 외국인 강도 표시 (강/중/약)
   - KOSDAQ 수급 토글 또는 비교 행

7. i18n 키 추가 (en/ko/zh):
   - alignment 상태 4종
   - strength 3종
   - KOSDAQ 관련 라벨

## Acceptance Criteria
- [ ] 기존 KOSPI 현물 수급 표시 유지 (회귀 없음)
- [ ] 외국인 vs 기관 동행/충돌 뱃지 표시
- [ ] 외국인 강도 시그널 표시
- [ ] KOSDAQ 수급 데이터 수집 및 표시
- [ ] i18n (en/ko/zh)
- [ ] 데이터 미가용시 graceful fallback
