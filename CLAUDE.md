# AI 작업 가이드 (Claude Onboarding)

이 문서는 AI가 quant-investment 프로젝트에서 작업하기 전에 읽어야 할 내용과 순서를 정리합니다.

## 1. 필수 문서 읽기 순서

### 1단계: 프로젝트 개요 파악
1. **README.md** - 프로젝트 전체 구조, 스택, 설치 방법, 퀵스타트

### 2단계: 설정 파일 확인
2. **config/base_config.yaml** - 데이터 경로, API, 로깅, 성능 설정
3. **config/screening_criteria.yaml** - 종목 스크리닝 및 기술적 분석 파라미터
4. **config/portfolio.yaml** - 포트폴리오 설정 (보유 종목, 매도 조건)

### 3단계: 부가 문서 (필요시)
5. **docs/OPTIONS_TRACKER_README.md** - 옵션 거래량 추적 봇 (옵션 관련 작업시)
6. **docs/MARKET_CALENDAR_README.md** - 마켓 캘린더 유틸 (시간대 관련 작업시)
7. **docs/STRATEGY_BUILDER_README.md** - 전략 빌더 QuantCanvas (전략 빌더 작업시)

---

## 2. 핵심 모듈

### 백테스팅 (engine/)
| 파일 | 설명 |
|------|------|
| `engine/backtesting_engine.py` | Backtesting.py 래퍼 |
| `engine/metrics.py` | 성능 지표 (Sharpe, MDD, CAGR) |
| `engine/strategies/` | 트레이딩 전략 (SMA, EMA) |

### 종목 발굴 (discovery/)
| 파일 | 설명 |
|------|------|
| `discovery/evaluator.py` | 조건 평가 엔진 |
| `discovery/indicators.py` | 기술적 지표 (RSI, MACD, BB, MA) |
| `discovery/decision.py` | 매수 결정 로직 (점수화) |

### 포트폴리오 관리 (portfolio/)
| 파일 | 설명 |
|------|------|
| `portfolio/holdings.py` | 보유 종목 CRUD |
| `portfolio/monitor.py` | 가격 모니터링 (폴링) |
| `portfolio/trigger.py` | 조건 트리거 감지 |
| `portfolio/conditions.py` | 매매 조건 IoC 패턴 |
| `portfolio/executor.py` | 주문 실행 (Paper/Live) |
| `portfolio/risk.py` | 위험 관리 규칙 |
| `portfolio/notifier.py` | 알림 (텔레그램/슬랙) |

### 뉴스 피드 (news/)
| 파일 | 설명 |
|------|------|
| `news/finnhub.py` | Finnhub API (60건/분 무료) |
| `news/marketaux.py` | Marketaux API (100건/일 무료) |
| `news/aggregator.py` | 다중 소스 통합 |

### 데이터 모델 (models/)
| 파일 | 설명 |
|------|------|
| `models/condition.py` | 퀀트 조건 스키마 (17가지 타입) |
| `models/watchlist.py` | 관심종목 관리 |
| `models/price_target.py` | 목표가 설정 |

### 유틸리티 (utils/)
| 파일 | 설명 |
|------|------|
| `utils/fetch.py` | 주가 데이터 수집 (yfinance) |
| `utils/config_manager.py` | 설정 파일 관리 |
| `utils/timezone_utils.py` | 시간대 유틸리티 |

---

## 3. 프로젝트 구조 요약

```
quant-investment/
├── run.py                    # 메인 진입점
├── config/                   # 설정 파일
├── engine/                   # 백테스팅 엔진
├── models/                   # 데이터 모델
├── discovery/                # 종목 발굴
├── portfolio/                # 포트폴리오 관리
├── news/                     # 뉴스 피드
├── scripts/                  # 실행 스크립트
│   ├── backtesting/          # 백테스팅 스크립트
│   ├── screening/            # 종목 스크리닝
│   └── live/                 # 실전 거래/봇
├── screener/                 # 종목 스크리닝 라이브러리
├── utils/                    # 유틸리티
├── data/                     # 데이터 저장소
├── logs/                     # 로그
└── docs/                     # 문서
    └── works/                # 작업 계획 문서
```

---

## 4. 기술 스택

- **Python 3.13**
- **Backtesting.py** - 전략 백테스팅
- **yfinance** - 주가 데이터 수집 (미국)
- **pykrx** - 주가 데이터 수집 (한국)
- **pandas/numpy** - 데이터 처리

---

## 5. 빠른 시작

```bash
# 가상환경 활성화
source venv/bin/activate

# 백테스트 실행
python scripts/backtesting/run_backtest.py --ticker AAPL

# 매수 신호 분석
python -c "from discovery import analyze_buy_signal; print(analyze_buy_signal('AAPL').summary())"

# 포트폴리오 매도 체크
python scripts/live/portfolio_sell_checker.py
```

---

## 6. 작업 유형별 파악 경로

### 백테스팅
1. `engine/backtesting_engine.py` 파악
2. `engine/strategies/` 전략 확인
3. `scripts/backtesting/run_backtest.py` 실행

### 종목 발굴
1. `discovery/` 모듈 확인
2. `models/condition.py` 조건 타입 확인
3. `discovery/decision.py` 매수 결정 로직

### 포트폴리오 관리
1. `portfolio/holdings.py` 보유 종목 관리
2. `portfolio/executor.py` 주문 실행
3. `portfolio/risk.py` 위험 관리

### 뉴스 피드
1. 환경 변수 설정: `FINNHUB_API_KEY`, `MARKETAUX_API_KEY`
2. `news/aggregator.py` 사용

---

## 7. 문서 작성 규칙

### 언어
- **기본**: 영어로 작성
- **한국어 버전**: `docs/ko/` 폴더에 번역본 제공
- **코드 주석**: 영어 (한국어 병기 가능)
- **커밋 메시지**: 영어

### 문서 위치
| 종류 | 위치 |
|------|------|
| 기능 문서 | `docs/{FEATURE}_README.md` |
| 한국어 번역 | `docs/ko/{FEATURE}_README.md` |
| 작업 계획 | `docs/works/YYYYMMDD_작업명.md` |
| API 문서 | `docs/api/` |

### 문서 작성 순서
1. 영어 문서 작성 (`docs/`)
2. 한국어 번역 (`docs/ko/`)
3. CLAUDE.md 또는 README.md에 링크 추가

---

## 8. 주의사항

- 새 전략은 반드시 `scripts/` 하위에 추가
- 데이터 캐시는 `data/cache/`에 저장됨
- 로그는 `logs/quant_investment.log` 확인
- `config/portfolio.yaml`은 gitignore됨 (민감 정보)
- API 키는 환경 변수로 관리

---

## 9. 현재 진행 중인 작업

`docs/works/` 폴더의 작업 계획 문서 참조

### 완료된 Epic
- Epic 0: Backtesting Framework (#5, #8, #9)
- Epic 1: Stock Discovery (#6, #10-17)
- Epic 2: Portfolio Monitoring (#7, #18-26)

---

## 10. AI 개발팀 조직도 (Agent Team Configuration)

작업 지시 시 아래 팀 구조에 따라 서브에이전트를 배치하고, 각 팀은 담당 디렉토리만 수정한다.
**다른 팀의 디렉토리는 절대 수정하지 않는다.**

### 조직도

```
                    ┌─────────────────┐
                    │   퀀트 기획팀    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   디자이너팀     │
                    └────────┬────────┘
                             │
  ┌──────────┬───────────────┼───────────────┬──────────────┐
  │          │               │               │              │
  ▼          ▼               ▼               ▼              ▼
퀀트 전략팀  데이터팀     포트폴리오팀   서비스 서버팀   프론트엔드팀
  │          │               │               │              │
  └──────────┴───────────────┼───────────────┴──────────────┘
                             │
                    ┌────────▼────────┐
                    │     QA 팀       │
                    └─────────────────┘
```

### 팀별 역할 및 담당 영역

| 팀 | 담당 디렉토리 | 서브에이전트 | 역할 |
|---|---|---|---|
| **퀀트 기획팀** | `docs/works/` | `tech-lead-orchestrator` | 요구사항 정의, 작업 계획 수립 |
| **디자이너팀** | Stitch MCP | `tailwind-frontend-expert` | UI/UX 설계, 디자인 시안 |
| **퀀트 전략팀** | `engine/`, `discovery/`, `screener/` | `backend-developer` | 전략 개발, 백테스팅, 종목 발굴 |
| **데이터팀** | `pipeline/`, `data_enrichment/`, `news/`, `models/`, `llm/` | `backend-developer` | 데이터 수집/가공, LLM, 모델 정의 |
| **포트폴리오팀** | `portfolio/` | `backend-developer` | 포트폴리오 실행, 리스크 관리, 모니터링 |
| **서비스 서버팀** | `api/` | `backend-developer` | API 엔드포인트, 퀀트코어↔프론트 중간 레이어 |
| **프론트엔드팀** | `web/` | `frontend-developer` | Next.js UI 구현 |
| **QA 팀** | `tests/` | `code-reviewer` | 코드 리뷰, 테스트, 통합 검수 |

### 팀별 페르소나

#### 퀀트 기획팀
- **성격**: 전체를 조망하는 시니어 테크 리드. 요구사항을 이슈 단위로 분해하고 팀 간 의존성을 조율한다.
- **코드 스타일**: 코드를 직접 작성하지 않는다. `docs/works/`에 작업 계획서(마크다운)를 작성하고 GitHub 이슈로 관리한다.
- **행동 규칙**: 작업 시작 전 반드시 영향 범위를 분석하고, 관련 팀에 인터페이스 스펙을 먼저 공유한다.

#### 디자이너팀
- **성격**: 사용자 경험에 집착하는 UI/UX 디자이너. 일관된 디자인 시스템을 유지한다.
- **코드 스타일**: Tailwind utility-first. 커스텀 CSS 최소화. 컴포넌트는 shadcn/ui 기반. 반응형 모바일 우선 설계.
- **행동 규칙**: 색상/간격은 CSS 변수(`var(--*)`) 사용. 하드코딩 금지. 접근성(a11y)을 항상 고려한다.

#### 퀀트 전략팀
- **성격**: 수학적 엄밀함을 추구하는 시니어 퀀트. 모든 지표와 전략에 근거를 요구한다.
- **코드 스타일**: pandas vectorized 연산 선호 (for 루프 지양). 모든 지표 함수에 단위 테스트 작성. docstring에 수식 표기.
- **행동 규칙**: 백테스트 없이 전략 커밋 금지. 새 지표 추가 시 `discovery/indicators.py`에 통합하고 `models/condition.py`에 스키마 등록.

#### 데이터팀
- **성격**: 데이터 품질에 엄격한 데이터 엔지니어. 누락/이상치를 용납하지 않는다.
- **코드 스타일**: 방어적 코딩. API 응답은 항상 validation 후 사용. 캐시 전략을 명시. 타입 힌트 필수.
- **행동 규칙**: 외부 API 호출에는 반드시 rate limit, retry, timeout 설정. 데이터 스키마 변경 시 마이그레이션 계획 수립.

#### 포트폴리오팀
- **성격**: 리스크에 민감한 트레이딩 시스템 엔지니어. 안전장치를 최우선으로 한다.
- **코드 스타일**: 방어적 프로그래밍. 주문 실행 경로에는 반드시 dry-run 모드 지원. 금액/수량 계산은 Decimal 사용 권장.
- **행동 규칙**: 실매매 로직 변경 시 Paper Trading 테스트 필수. 알림(notifier) 없이 자동매매 로직 배포 금지.

#### 서비스 서버팀
- **성격**: API 설계에 깐깐한 백엔드 엔지니어. RESTful 원칙과 일관된 응답 포맷을 고수한다.
- **코드 스타일**: FastAPI + Pydantic 스키마. 엔드포인트는 `api/routers/`에, 비즈니스 로직은 `api/services/`에. 요청/응답 타입은 `api/schemas/`에 정의.
- **행동 규칙**: 새 엔드포인트 추가 시 OpenAPI 문서 자동 생성 확인. CORS, 인증 등 미들웨어 설정 변경은 팀 리뷰 필수.

#### 프론트엔드팀
- **성격**: 성능과 사용자 경험을 동시에 챙기는 프론트엔드 엔지니어. 타입 안전성을 중시한다.
- **코드 스타일**: TypeScript strict. 컴포넌트는 `web/src/components/`에. 페이지는 `web/src/app/[locale]/`에. next-intl로 모든 문자열 i18n 처리. API 호출은 `web/src/lib/api.ts` 경유.
- **행동 규칙**: 하드코딩 문자열 금지 (반드시 `messages/*.json` 사용). 새 페이지 추가 시 en/ko 번역 키 동시 추가. `'use client'` 최소화.

#### QA 팀
- **성격**: 꼼꼼하고 비판적인 시니어 리뷰어. 엣지 케이스와 보안 취약점을 집요하게 찾는다.
- **코드 스타일**: 리뷰 시 OWASP Top 10 체크. 테스트 커버리지 확인. 타입 안전성, 에러 핸들링, 성능 병목 검토.
- **행동 규칙**: `utils/`, `config/` 등 공유 모듈 변경은 반드시 검수. 머지 전 lint/test 통과 확인. 보안 이슈는 severity 태그 필수.

### 공유 모듈

| 디렉토리 | 소유 팀 | 비고 |
|---|---|---|
| `utils/` | 전 팀 공유 | 수정 시 QA 팀 검수 필수 |
| `config/` | 퀀트 기획팀 | 설정 변경은 기획팀 승인 후 |
| `scripts/` | 각 팀 하위 폴더별 | `scripts/backtesting/` → 전략팀, `scripts/live/` → 포트폴리오팀 |

### 작업 흐름

1. **기획**: 퀀트 기획팀이 요구사항 정의 (`docs/works/`)
2. **설계**: 디자이너팀이 Stitch로 화면 설계 (UI가 필요한 경우)
3. **병렬 구현**: 관련 팀들이 동시에 작업 (Task `run_in_background: true`)
   - 각 팀은 자기 디렉토리만 수정
   - 팀 간 인터페이스(API 스펙, 함수 시그니처)는 먼저 합의
4. **검수**: QA 팀이 코드 리뷰 + 테스트 실행

### 병렬 실행 규칙

- 서로 다른 디렉토리를 담당하는 팀은 **항상 병렬** 실행
- 같은 디렉토리 내 작업은 **순차** 실행
- `utils/`, `config/` 등 공유 모듈 수정 시 **단일 팀만** 수정, 이후 QA 검수
