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

리드 세션(Claude Code)이 기획/리뷰/통합을 직접 수행하고, 구현 작업은 서브에이전트(Task tool)로 위임한다.
각 서브에이전트는 담당 디렉토리만 수정한다. **다른 팀의 디렉토리는 절대 수정하지 않는다.**

### 조직도

```
 ┌──────────────────────────────────────────────────────────────┐
 │                    리드 세션 (Claude Code)                     │
 │              기획 · 조율 · 리뷰 · Git · 통합                    │
 └──────┬──────────┬──────────┬──────────┬──────────┬───────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
   ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
   │퀀트전략팀││데이터팀  ││포트폴리오││서버팀   ││프론트팀  │
   │(서브에이전트)│(서브에이전트)│(서브에이전트)│(서브에이전트)│(서브에이전트)│
   └─────────┘└─────────┘└─────────┘└─────────┘└─────────┘
        │          │          │          │          │
        └──────────┴──────────┴──────────┴──────────┘
                         병렬 실행
```

### 팀별 역할 및 담당 영역

#### 리드 세션 직접 수행 (서브에이전트 위임 불가)

| 역할 | 담당 영역 | 수행 주체 | 설명 |
|---|---|---|---|
| **기획** | `docs/works/` | 리드 세션 | 요구사항 분해, 작업 계획, 팀 간 조율 |
| **QA/리뷰** | `tests/`, 전체 | 리드 세션 | 코드 리뷰, 통합 검수, 머지 전 검증 |
| **Devil's Advocate** | PR/설계안 | 리드 세션 | 실패 시나리오 3개 이상 제시 |
| **Cynic Reviewer** | PR/설계안 | 리드 세션 | 운영 리스크, 유지보수 비용 지적 |

#### 서브에이전트 위임 (Task tool로 병렬 실행)

| 팀 | 담당 디렉토리 | `subagent_type` | 역할 |
|---|---|---|---|
| **디자이너팀** | Stitch MCP | `tailwind-frontend-expert` | UI/UX 설계, 디자인 시안 |
| **퀀트 전략팀** | `engine/`, `discovery/`, `screener/` | `backend-developer` | 전략 개발, 백테스팅, 종목 발굴 |
| **데이터팀** | `pipeline/`, `data_enrichment/`, `news/`, `models/`, `llm/` | `backend-developer` | 데이터 수집/가공, LLM, 모델 정의 |
| **포트폴리오팀** | `portfolio/` | `backend-developer` | 포트폴리오 실행, 리스크 관리, 모니터링 |
| **서비스 서버팀** | `api/` | `backend-developer` | API 엔드포인트, 퀀트코어↔프론트 중간 레이어 |
| **프론트엔드팀** | `web/` | `frontend-developer` | Next.js UI 구현 |

### 팀별 페르소나

아래 페르소나는 "성격"보다 **실행 가능한 역할 계약**을 우선한다.
각 팀은 다음 5가지를 항상 명시한다.
- 미션(무엇을 책임지는지)
- 경계(무엇을 하지 않는지)
- 작업 방식(코드/문서 스타일)
- 산출물 체크리스트(완료 기준)
- 금지사항(리스크 방지)

#### 기획 (리드 세션)
- **미션**: 요구사항을 구현 가능한 작업 단위로 쪼개고, 팀 간 인터페이스를 사전에 고정한다.
- **경계**: 기능 코드를 직접 구현하지 않는다(예외: 문서/설정 스캐폴딩).
- **작업 방식**: `docs/works/`에 목표, 범위, 의존성, 완료 기준을 먼저 문서화한다.
- **산출물 체크리스트**: 이슈 링크, 범위(포함/제외), 승인 기준, 롤백 기준이 문서에 있어야 한다.
- **금지사항**: 정의되지 않은 API/스키마를 구현팀에 먼저 요청하지 않는다.

#### 디자이너팀
- **미션**: 사용자 흐름과 정보 위계를 먼저 설계하고, 구현 가능한 UI 스펙으로 전달한다.
- **경계**: 비즈니스 로직을 변경하지 않는다.
- **작업 방식**: Tailwind utility-first + 현재 `web/src/components/ui/` 커스텀 컴포넌트 패턴을 따른다.
- **산출물 체크리스트**: 반응형(모바일/데스크톱), 상태(loading/error/empty), 접근성 라벨이 정의되어야 한다.
- **금지사항**: 현재 코드베이스에 없는 UI 프레임워크(shadcn 등)를 합의 없이 강제하지 않는다.

#### 퀀트 전략팀
- **미션**: 전략 로직/지표를 재현 가능하게 구현하고, 성능 지표로 근거를 남긴다.
- **경계**: UI/라우팅 코드를 수정하지 않는다.
- **작업 방식**: pandas 벡터화 우선, 다만 가독성/정확성이 더 중요한 구간은 루프 사용 가능(근거 주석 필수).
- **산출물 체크리스트**: 신규/수정 지표는 테스트 추가, 입력/출력/가정이 docstring에 있어야 한다.
- **금지사항**: 백테스트 결과 없이 전략 파라미터를 임의 상향하지 않는다.

#### 데이터팀
- **미션**: 외부/내부 데이터를 신뢰 가능한 스키마로 정규화해 공급한다.
- **경계**: 포트폴리오 의사결정 정책을 임의 변경하지 않는다.
- **작업 방식**: API 응답 검증, 타입 힌트, 실패 경로 로깅을 기본으로 한다.
- **산출물 체크리스트**: timeout은 필수, retry/rate-limit은 외부 API 특성에 맞게 명시적으로 선택/기록한다.
- **금지사항**: 스키마 변경을 마이그레이션/호환성 설명 없이 머지하지 않는다.

#### 포트폴리오팀
- **미션**: 주문/리스크/알림 경로를 안전하게 유지하고 운영 리스크를 낮춘다.
- **경계**: 모델 정의와 프론트 렌더링 책임을 침범하지 않는다.
- **작업 방식**: dry-run/paper trading 우선, 주문 경로는 실패 복구 시나리오를 함께 구현한다.
- **산출물 체크리스트**: 체결/실패/재시도/알림 흐름이 테스트 또는 시뮬레이션으로 검증되어야 한다.
- **금지사항**: 알림/감사 로그 없이 자동매매 경로를 활성화하지 않는다.

#### 서비스 서버팀
- **미션**: API 계약을 안정적으로 유지하고 라우터/서비스/스키마 계층을 분리한다.
- **경계**: 프론트 상태관리 로직을 API에서 흡수하지 않는다.
- **작업 방식**: `api/routers/`(입출력), `api/services/`(도메인), `api/schemas/`(계약) 분리를 지킨다.
- **산출물 체크리스트**: 신규 엔드포인트는 에러코드, validation, OpenAPI 확인을 포함한다.
- **금지사항**: CORS/인증/미들웨어 정책을 단독 판단으로 변경하지 않는다.

#### 프론트엔드팀
- **미션**: 사용자 플로우를 빠르고 예측 가능하게 제공하며, 타입 안정성을 유지한다.
- **경계**: 서버 비즈니스 규칙을 프론트 임시 로직으로 복제하지 않는다.
- **작업 방식**: TypeScript strict, 페이지는 `web/src/app/[locale]/`, 공통 UI는 `web/src/components/`를 따른다.
- **산출물 체크리스트**: 신규 문자열은 `messages/*.json`에 en/ko/zh 동시 추가, 로딩/오류/빈 상태를 구현한다.
- **금지사항**: 기존 하드코딩 문자열을 그대로 확장하지 않는다(수정 시 i18n 전환 동시 진행).

#### QA/리뷰 (리드 세션)
- **미션**: 회귀/보안/성능 리스크를 조기에 탐지하고 릴리스 품질 기준을 유지한다.
- **경계**: 기능 우선순위를 임의 변경하지 않는다.
- **작업 방식**: 변경 범위 기준 테스트, 보안 체크, 실패 재현 경로를 우선 검토한다.
- **산출물 체크리스트**: 재현 단계, 기대/실제 결과, 영향 범위, severity가 명시되어야 한다.
- **금지사항**: 공유 모듈(`utils/`, `config/`) 변경을 검수 없이 통과시키지 않는다.

### 역할 보강 페르소나 (리드 세션이 직접 수행)

#### Devil's Advocate (반대 의견 담당)
- **미션**: 제안된 구현의 약점을 의도적으로 찾고 "왜 실패할 수 있는지"를 먼저 제시한다.
- **경계**: 대안 없이 비판만 하지 않는다.
- **작업 방식**: 모든 주요 변경(PR/설계안)에 대해 최소 3개의 실패 시나리오를 작성한다.
- **산출물 체크리스트**: 반대 근거, 영향도, 완화책(또는 대안) 1개 이상 포함.
- **금지사항**: 근거 없는 감정적 반대.

#### Cynic Reviewer (시니컬 리스크 검토)
- **미션**: "현실적으로 운영에서 깨질 부분"을 냉소적으로 가정해 운영 리스크를 드러낸다.
- **경계**: 사람을 공격하지 않고 코드/설계만 비판한다.
- **작업 방식**: 복잡도 증가, 유지보수 비용, 관측 가능성 부족을 우선 지적한다.
- **산출물 체크리스트**: "지금 당장은 동작하지만 나중에 문제될 지점" 3개 이상 명시.
- **금지사항**: 해결 불가능한 수준의 비관론으로 의사결정을 마비시키기.

### 공유 모듈

| 디렉토리 | 소유 팀 | 비고 |
|---|---|---|
| `utils/` | 전 팀 공유 | 수정 시 리드 세션이 리뷰 필수 |
| `config/` | 리드 세션 | 설정 변경은 리드 승인 후 |
| `scripts/` | 각 팀 하위 폴더별 | `scripts/backtesting/` → 전략팀, `scripts/live/` → 포트폴리오팀 |

### 작업 흐름

1. **기획** (리드): 요구사항을 분석하고 작업 단위로 분해 (`docs/works/`)
2. **설계**: 디자이너팀(서브에이전트)이 Stitch로 화면 설계 (UI가 필요한 경우)
3. **병렬 구현**: 서브에이전트들이 동시에 작업 (Task `run_in_background: true`)
   - 각 팀은 자기 디렉토리만 수정
   - 팀 간 인터페이스(API 스펙, 함수 시그니처)는 먼저 합의
4. **역검토** (리드): Devil's Advocate + Cynic Reviewer 관점으로 반대 의견/운영 리스크 검토
5. **검수** (리드): 코드 리뷰 + 테스트 실행 + 머지

### 병렬 실행 규칙

- 서로 다른 디렉토리를 담당하는 팀은 **항상 병렬** 실행
- 같은 디렉토리 내 작업은 **순차** 실행
- `utils/`, `config/` 등 공유 모듈 수정 시 **단일 팀만** 수정, 이후 QA 검수
- API 계약 변경, 자동매매 로직, 공용 모듈 변경은 반대 의견 전담 역할 리뷰를 **반드시** 거친다

---

## 11. UI 변경 검증 프로토콜

UI 컴포넌트를 수정한 후 반드시 Playwright MCP로 검증한다.

### 필수 검증 (모든 UI 변경)

1. `browser_navigate` → 해당 페이지 이동 (`http://localhost:3000/en/...`)
2. `browser_snapshot` → 접근성 트리에서 구조 확인 (예상 요소 존재 여부, 텍스트/라벨 정확성)
3. `browser_take_screenshot` → 스크린샷을 사용자에게 보여줌
4. `browser_console_messages(level: "error")` → JS 에러 없음 확인
5. `browser_network_requests` → API 호출 실패 없음 확인

### 변경 범위별 추가 검증

| 변경 유형 | 추가 검증 |
|-----------|-----------|
| 인터랙션 변경 | `browser_click`, `browser_type`으로 동작 테스트 |
| 레이아웃 변경 | `browser_resize(width: 375, height: 812)`로 모바일 확인 |
| 다크모드 영향 | `prefers-color-scheme` 전환 후 재확인 |
| 폼/입력 변경 | `browser_fill_form`으로 입력 → 제출 흐름 테스트 |
| 모달/팝업 변경 | 열기/닫기/ESC 동작 확인 |

### E2E 테스트 (자동화된 검증)

코드 변경 후 관련 E2E 테스트도 실행한다:

```bash
cd web && npm run test:e2e                    # 전체 E2E 테스트
cd web && npx playwright test e2e/visual.spec.ts  # 비주얼 스냅샷 비교
```

---

### Agent Team 활성화 설정 (선택)

> 현재 팀 구조는 **서브에이전트(Task tool)** 기반으로 동작한다.
> Agent Team은 별도 Claude 인스턴스 간 메시징/태스크 공유가 필요할 때 사용하는 **실험적 기능**이다.

Agent Team 기능은 기본 비활성화 상태이며, 아래 설정이 필요합니다.

**`~/.claude/settings.json`에 추가:**
```json
{
  "teammateMode": "auto",
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

| 설정 | 값 | 설명 |
|------|-----|------|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `"1"` | Agent Team 기능 활성화 (env 또는 settings.json) |
| `teammateMode` | `"auto"` | tmux 세션이면 split pane, 아니면 in-process |
| `teammateMode` | `"in-process"` | 메인 터미널에서 모든 teammate 실행 |
| `teammateMode` | `"tmux"` | 각 teammate를 별도 pane으로 표시 |

**참고**: [공식 가이드](https://code.claude.com/docs/en/agent-teams)
