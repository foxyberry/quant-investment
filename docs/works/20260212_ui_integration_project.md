# UI 연동 프로젝트: FastAPI + Next.js 웹 대시보드

- **날짜**: 2026-02-12
- **브랜치**: `feature/ui-integration`
- **상태**: 계획중

## 목표

기존 quant-investment 백엔드를 REST API로 제공하고, Next.js 기반 웹 대시보드를 구축하여 브라우저에서 종목 스크리닝, 포트폴리오 관리, 분석 결과 조회가 가능하도록 한다.

## 배경

- 현재 CLI 기반으로만 사용 가능
- 매번 터미널에서 스크립트 실행 필요
- 시각적인 차트와 대시보드 부재
- 모바일/원격 접근 불가

---

# Phase 1: FastAPI 백엔드 구축

## Epic 1.1: 프로젝트 구조 설정

### Task 1.1.1: FastAPI 기본 구조 생성 ✅ (2026-02-12)
- [x] `api/` 폴더 생성
- [x] `api/__init__.py` 생성
- [x] `api/main.py` 생성 (FastAPI 앱 인스턴스)
- [x] `api/config.py` 생성 (환경변수, 설정)
- [x] `api/dependencies.py` 생성 (공통 의존성)

**변경 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `api/__init__.py` | 신규 생성 |
| `api/main.py` | FastAPI 앱 초기화, CORS 설정 |
| `api/config.py` | Settings 클래스 (pydantic-settings) |
| `api/dependencies.py` | 공통 의존성 주입 |

### Task 1.1.2: 라우터 구조 생성 ✅ (2026-02-12)
- [x] `api/routers/` 폴더 생성
- [x] `api/routers/__init__.py` 생성
- [x] `api/routers/health.py` 생성 (헬스체크)

**변경 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `api/routers/__init__.py` | 라우터 export |
| `api/routers/health.py` | GET /health 엔드포인트 |

### Task 1.1.3: 스키마 구조 생성 ✅ (2026-02-12)
- [x] `api/schemas/` 폴더 생성
- [x] `api/schemas/__init__.py` 생성
- [x] `api/schemas/common.py` 생성 (공통 응답 스키마)

**변경 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `api/schemas/__init__.py` | 스키마 export |
| `api/schemas/common.py` | ApiResponse, PaginatedResponse |

### Task 1.1.4: 의존성 추가 ✅ (2026-02-12)
- [x] `requirements.txt`에 FastAPI 관련 패키지 추가
- [x] `requirements-dev.txt` 생성 (테스트, 린팅, 타입체크)

**추가 패키지:**
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-multipart>=0.0.6
```

### Task 1.1.5: 개발 서버 실행 스크립트
- [ ] `scripts/run_api.sh` 생성
- [ ] `scripts/run_api.py` 생성 (Python 버전)

---

## Epic 1.2: 스크리닝 API

### Task 1.2.1: 스크리닝 스키마 정의
- [ ] `api/schemas/screening.py` 생성
- [ ] ScreeningRequest 스키마
- [ ] ScreeningResult 스키마
- [ ] ConditionResult 스키마
- [ ] PresetInfo 스키마

**스키마 예시:**
```python
class ScreeningRequest(BaseModel):
    preset: str = "accumulation_basic"
    universe: str = "KOSPI"
    params: Optional[Dict[str, Any]] = None

class ScreeningResultItem(BaseModel):
    ticker: str
    name: str
    current_price: float
    matched: bool
    conditions: List[ConditionResultItem]
```

### Task 1.2.2: 스크리닝 라우터 구현
- [ ] `api/routers/screening.py` 생성
- [ ] GET `/api/screening/presets` - 프리셋 목록
- [ ] GET `/api/screening/universes` - 유니버스 목록
- [ ] POST `/api/screening/run` - 스크리닝 실행
- [ ] GET `/api/screening/stock/{ticker}` - 단일 종목 검사

### Task 1.2.3: 스크리닝 서비스 레이어
- [ ] `api/services/` 폴더 생성
- [ ] `api/services/screening_service.py` 생성
- [ ] 기존 `screener` 모듈과 연동

---

## Epic 1.3: 포트폴리오 API

### Task 1.3.1: 포트폴리오 스키마 정의
- [ ] `api/schemas/portfolio.py` 생성
- [ ] HoldingCreate, HoldingUpdate 스키마
- [ ] HoldingResponse 스키마
- [ ] PortfolioSummary 스키마
- [ ] SellSignalResponse 스키마

### Task 1.3.2: 포트폴리오 라우터 구현
- [ ] `api/routers/portfolio.py` 생성
- [ ] GET `/api/portfolio` - 전체 포트폴리오
- [ ] POST `/api/portfolio/holdings` - 종목 추가
- [ ] PUT `/api/portfolio/holdings/{ticker}` - 종목 수정
- [ ] DELETE `/api/portfolio/holdings/{ticker}` - 종목 삭제
- [ ] GET `/api/portfolio/summary` - P&L 요약
- [ ] GET `/api/portfolio/sell-signals` - 매도 신호

### Task 1.3.3: 포트폴리오 서비스 레이어
- [ ] `api/services/portfolio_service.py` 생성
- [ ] 기존 `portfolio` 모듈과 연동
- [ ] YAML 파일 대신 SQLite 사용 고려

---

## Epic 1.4: 분석 API

### Task 1.4.1: 분석 스키마 정의
- [ ] `api/schemas/analysis.py` 생성
- [ ] EnrichRequest, EnrichResponse 스키마
- [ ] AnalysisResult 스키마
- [ ] TechnicalData, FundamentalData 스키마

### Task 1.4.2: 분석 라우터 구현
- [ ] `api/routers/analysis.py` 생성
- [ ] POST `/api/analysis/enrich` - 데이터 강화
- [ ] POST `/api/analysis/analyze` - AI 분석 (단일)
- [ ] GET `/api/analysis/reports` - 리포트 목록
- [ ] GET `/api/analysis/reports/{date}` - 리포트 조회

### Task 1.4.3: 분석 서비스 레이어
- [ ] `api/services/analysis_service.py` 생성
- [ ] 기존 `data_enrichment`, `llm` 모듈과 연동

---

## Epic 1.5: 시세 API

### Task 1.5.1: 시세 스키마 정의
- [ ] `api/schemas/market.py` 생성
- [ ] OHLCVData 스키마
- [ ] QuoteResponse 스키마

### Task 1.5.2: 시세 라우터 구현
- [ ] `api/routers/market.py` 생성
- [ ] GET `/api/market/quote/{ticker}` - 현재가
- [ ] GET `/api/market/ohlcv/{ticker}` - OHLCV 데이터
- [ ] GET `/api/market/technical/{ticker}` - 기술적 지표

### Task 1.5.3: 캐시 서비스 연동
- [ ] `api/services/market_service.py` 생성
- [ ] 기존 `OHLCVCache` 활용

---

# Phase 2: Next.js 프론트엔드 구축

## Epic 2.1: 프로젝트 초기 설정

### Task 2.1.1: Next.js 프로젝트 생성 ✅ (2026-02-12)
- [x] `web/` 폴더에 Next.js 16 (App Router) 프로젝트 생성
- [x] TypeScript 설정
- [x] ESLint 설정
- [x] Tailwind CSS 설정

**명령어:**
```bash
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir
```

### Task 2.1.2: 기본 레이아웃 구성
- [ ] `web/src/app/layout.tsx` - 루트 레이아웃
- [ ] `web/src/components/layout/Header.tsx` - 헤더
- [ ] `web/src/components/layout/Sidebar.tsx` - 사이드바
- [ ] `web/src/components/layout/Footer.tsx` - 푸터

### Task 2.1.3: API 클라이언트 설정 ✅ (2026-02-12)
- [x] `web/src/lib/api.ts` - Fetch 래퍼
- [x] `web/src/lib/types.ts` - API 타입 정의
- [x] 환경변수 설정 (`.env.local`)

### Task 2.1.4: 상태 관리 설정
- [ ] Zustand 또는 React Query 설치
- [ ] `web/src/stores/` 폴더 구조
- [ ] `web/src/hooks/` 커스텀 훅

---

## Epic 2.2: 대시보드 페이지

### Task 2.2.1: 대시보드 레이아웃
- [ ] `web/src/app/page.tsx` - 메인 대시보드
- [ ] 포트폴리오 요약 카드
- [ ] 오늘의 스크리닝 결과 카드
- [ ] 최근 분석 리포트 카드

### Task 2.2.2: 포트폴리오 요약 컴포넌트
- [ ] `web/src/components/dashboard/PortfolioSummary.tsx`
- [ ] 총 자산, 수익률, P&L 표시
- [ ] 종목별 비중 파이차트

### Task 2.2.3: 스크리닝 요약 컴포넌트
- [ ] `web/src/components/dashboard/ScreeningSummary.tsx`
- [ ] 오늘 발견된 종목 수
- [ ] 프리셋별 결과 요약

---

## Epic 2.3: 스크리닝 페이지

### Task 2.3.1: 스크리닝 페이지 레이아웃
- [ ] `web/src/app/screening/page.tsx`
- [ ] 프리셋 선택 UI
- [ ] 파라미터 조정 폼
- [ ] 실행 버튼

### Task 2.3.2: 스크리닝 결과 테이블
- [ ] `web/src/components/screening/ResultTable.tsx`
- [ ] AG-Grid 또는 TanStack Table 사용
- [ ] 정렬, 필터, 페이지네이션
- [ ] 종목 클릭 시 상세 정보

### Task 2.3.3: 스크리닝 필터 컴포넌트
- [ ] `web/src/components/screening/FilterPanel.tsx`
- [ ] 프리셋 드롭다운
- [ ] 파라미터 슬라이더 (BB 폭, 거래량 등)
- [ ] 유니버스 선택

---

## Epic 2.4: 포트폴리오 페이지

### Task 2.4.1: 포트폴리오 페이지 레이아웃
- [ ] `web/src/app/portfolio/page.tsx`
- [ ] 보유 종목 테이블
- [ ] 종목 추가/수정 모달

### Task 2.4.2: 보유 종목 테이블
- [ ] `web/src/components/portfolio/HoldingsTable.tsx`
- [ ] 종목명, 수량, 평균가, 현재가, 수익률
- [ ] 수정/삭제 버튼

### Task 2.4.3: 종목 추가 폼
- [ ] `web/src/components/portfolio/AddHoldingForm.tsx`
- [ ] 종목 검색 자동완성
- [ ] 수량, 매수가 입력
- [ ] 유효성 검증

### Task 2.4.4: 매도 신호 알림
- [ ] `web/src/components/portfolio/SellSignals.tsx`
- [ ] 매도 조건 충족 종목 하이라이트
- [ ] 알림 배지

---

## Epic 2.5: 차트 및 분석 페이지

### Task 2.5.1: 종목 상세 페이지
- [ ] `web/src/app/stock/[ticker]/page.tsx`
- [ ] 캔들 차트 (TradingView Lightweight Charts)
- [ ] 기술적 지표 오버레이
- [ ] 재무 데이터 표시

### Task 2.5.2: 캔들 차트 컴포넌트
- [ ] `web/src/components/chart/CandleChart.tsx`
- [ ] TradingView Lightweight Charts 연동
- [ ] 이동평균선, 볼린저밴드 오버레이
- [ ] 거래량 바 차트

### Task 2.5.3: 기술적 지표 패널
- [ ] `web/src/components/chart/IndicatorPanel.tsx`
- [ ] RSI, MACD, Stochastic 표시
- [ ] 신호 해석 텍스트

### Task 2.5.4: 분석 리포트 페이지
- [ ] `web/src/app/analysis/page.tsx`
- [ ] 일자별 리포트 목록
- [ ] Markdown 렌더링

---

# Phase 3: 통합 및 배포

## Epic 3.1: 개발 환경 통합

### Task 3.1.1: Docker Compose 설정
- [ ] `docker-compose.yml` 생성
- [ ] FastAPI 서비스 정의
- [ ] Next.js 서비스 정의
- [ ] 공유 네트워크 설정

### Task 3.1.2: 개발 실행 스크립트
- [ ] `scripts/dev.sh` - 전체 개발 서버 실행
- [ ] 동시에 API + Web 실행
- [ ] 핫 리로드 지원

---

## Epic 3.2: 테스트

### Task 3.2.1: API 테스트
- [ ] `api/tests/` 폴더 구조
- [ ] pytest + httpx 설정
- [ ] 각 엔드포인트 테스트

### Task 3.2.2: 프론트엔드 테스트
- [ ] Jest + React Testing Library 설정
- [ ] 주요 컴포넌트 테스트

---

## Epic 3.3: 문서화

### Task 3.3.1: API 문서
- [ ] FastAPI 자동 생성 Swagger 활용
- [ ] README에 API 사용법 추가

### Task 3.3.2: 개발 가이드
- [ ] `docs/DEVELOPMENT.md` 작성
- [ ] 로컬 개발 환경 설정 방법
- [ ] 아키텍처 설명

---

# 작업 우선순위 및 일정

## 추천 진행 순서

| 순서 | Epic | 예상 작업량 |
|------|------|------------|
| 1 | 1.1 프로젝트 구조 설정 | 0.5일 |
| 2 | 1.2 스크리닝 API | 1일 |
| 3 | 1.5 시세 API | 0.5일 |
| 4 | 2.1 Next.js 초기 설정 | 0.5일 |
| 5 | 2.3 스크리닝 페이지 | 1일 |
| 6 | 1.3 포트폴리오 API | 1일 |
| 7 | 2.4 포트폴리오 페이지 | 1일 |
| 8 | 2.5 차트 및 분석 | 1.5일 |
| 9 | 1.4 분석 API | 1일 |
| 10 | 2.2 대시보드 | 1일 |
| 11 | 3.x 통합 및 배포 | 1일 |

**총 예상**: 10일

---

# 기술적 고려사항

## 주의점

1. **CORS 설정**: FastAPI에서 Next.js 개발 서버(localhost:3000) 허용 필요
2. **환경변수 관리**: API 키 (ANTHROPIC_API_KEY 등) 안전하게 관리
3. **캐시 전략**: OHLCV 데이터는 기존 Parquet 캐시 활용
4. **비동기 처리**: 스크리닝, AI 분석은 시간이 오래 걸릴 수 있음 → 폴링 또는 WebSocket

## 의존성 충돌 방지

- Python 가상환경 분리 유지
- Node.js는 `web/` 폴더 내에서만 관리
- 공유 데이터는 `data/` 폴더 사용

---

# 결과

(완료 후 작성)
