# quant-investment

스크리닝, 전략 설계, 백테스팅, 포트폴리오 모니터링, 관심종목 추적, 분석을 하나로 연결한 퀀트 투자 워크스페이스입니다.

언어: [English README](README.md)

## 이 프로젝트는 무엇인가요?

`quant-investment`는 아래를 통합합니다.
- **FastAPI** 백엔드: 스크리닝/전략 실행/포트폴리오/관심종목 API
- **Next.js 16 + React 19** 웹 UI: 일상적인 퀀트 작업 흐름 제공 (EN/KO/ZH 다국어)
- **Python** 연구/실행 모듈: 데이터, 지표, 백테스트

핵심 목표는 아이디어를 실행 가능한 전략으로 빠르게 연결하는 것입니다.

## UI에서 할 수 있는 일

| 영역 | 경로 | 가능한 작업 |
|---|---|---|
| 대시보드 | `/[locale]` | 시장/포트폴리오 요약, 매도 신호, 퀵 통계 |
| 스크리닝 | `/[locale]/screening` | 조건 조합, 스캔 실행, 통과 종목 확인 |
| 전략 빌더 | `/[locale]/strategy` | 노드 기반 전략 그래프, 저장/불러오기, 실행, 시장 배지 |
| 포트폴리오 | `/[locale]/portfolio` | 보유 종목, 매도 규칙, 손익 트리맵, 주문 데스크 |
| 관심종목 | `/[locale]/watchlist` | 종목 추적, 목표가 설정, 매수 규칙, 퀵뷰 팝업 |
| 분석 | `/[locale]/analysis` | 차트/지표 분석, 종목별 분석 팝업 |
| 리포트 | `/[locale]/reports` | 분석 리포트 조회, 목표일 추적 |
| 설정 | `/[locale]/settings` | 앱 환경설정 |

## 빠른 시작

### 1) 요구사항

- Python 3.13+
- Node.js 20+
- npm 10+

### 2) 설치

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm --prefix web install
```

### 3) 실행

API (기본 포트 `8002`):
```bash
source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload
```

Web (기본 포트 `3002`):
```bash
cd web && PORT=3002 npm run dev
```

> 포트 번호는 자유롭게 변경 가능합니다. API 포트를 바꾸면 `web/.env.local`의 `NEXT_PUBLIC_API_URL`도 맞춰 주세요.

### 4) 접속

- Web UI: `http://localhost:3002`
- API 문서 (Swagger): `http://localhost:8002/docs`

## Docker 공용 DB (실행 위치/포트 독립)

API/Web를 어디서 실행해도 동일한 로컬 DB를 쓰고 싶을 때 사용합니다.

### 1) env 설정

```bash
cp .env.example .env
```

`.env`에서 아래 값을 설정하세요.
- `DB_PORT` (기본 `5432`, 충돌 시 변경)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `DATABASE_URL=postgresql://<DB_USER>:<DB_PASSWORD>@localhost:<DB_PORT>/<DB_NAME>`

### 2) DB만 기동

```bash
docker compose up -d db
docker compose ps db
```

데이터는 named volume `quant-investment-pgdata`에 영속 저장됩니다.

### 3) 스키마 초기화

```bash
source venv/bin/activate
python -c "from api.database import init_db; init_db()"
```

### 4) 포트 충돌 정책

`5432`가 이미 사용 중이면 `.env`에서 `DB_PORT=55432`로 변경하고 `DATABASE_URL`도 맞춰 주세요. 이후 재기동:

```bash
docker compose up -d db
```

## 핵심 작업 시나리오

### 시나리오 A: 전략 생성 후 실행

1. 전략 빌더(`/strategy`) 접속
2. 유니버스/조건 노드 배치, 엣지 연결
3. 조건 파라미터 조정
4. 배포/실행 버튼 클릭
5. 매칭 결과(KOSPI/KOSDAQ 시장 배지)와 중간 결과 확인

### 시나리오 B: 전략 검증(백테스트)

1. 전략 저장 또는 불러오기
2. 백테스트 패널 열기
3. 기간/입력값 선택
4. 결과(수익곡선/거래내역/지표) 검토

### 시나리오 C: 스크리닝에서 분석으로

1. `/screening`에서 스캔 실행
2. 종목코드 클릭 → 분석 팝업(퀵뷰) 열림
3. 기술/재무/AI 컨텍스트 확인
4. 리포트 흐름으로 연결

### 시나리오 D: 포트폴리오 모니터링

1. 포트폴리오 페이지에서 종목 추가(이름으로 검색)
2. 종목별 매도 규칙 설정(손절/익절/트레일링스탑/보유기간)
3. 손익, 트리맵, 매도 신호 배너 모니터링
4. 종목코드 클릭으로 분석 팝업

### 시나리오 E: 관심종목 추적

1. 관심종목에 추가(이름 검색, 목표가 자동 입력)
2. 현재가 vs 목표가 추적
3. 종목별 매수 규칙 설정
4. 종목코드 클릭으로 분석 팝업

## 기술 스택

| 레이어 | 기술 |
|---|---|
| 백엔드 | Python 3.13, FastAPI, SQLAlchemy, SQLite |
| 프론트엔드 | Next.js 16, React 19, TypeScript, Tailwind CSS |
| 다국어 | next-intl (EN / KO / ZH) |
| 데이터 | yfinance (미국), pykrx (한국), Finnhub, Marketaux |
| 리서치 | pandas, numpy, Backtesting.py |

## 설정

### 주요 설정 파일

- `config/base_config.yaml`: 전역 런타임/데이터/로깅
- `config/screening_criteria.yaml`: 스크리닝 기본값
- `portfolio/`: 포트폴리오 로직 및 포지션 사이징 모듈

### 환경 변수

| 변수 | 용도 |
|---|---|
| `NEXT_PUBLIC_API_URL` | 프론트엔드 API 베이스 URL (예: `http://localhost:8002`) |
| `ANTHROPIC_API_KEY` | AI 분석 연동 |
| `FINNHUB_API_KEY` | 선택적 뉴스/데이터 소스 |
| `MARKETAUX_API_KEY` | 선택적 뉴스/데이터 소스 |

## API 엔드포인트

| 그룹 | 접두사 | 설명 |
|---|---|---|
| 포트폴리오 | `/api/portfolio` | 보유 종목 CRUD, 매도 규칙, 매도 신호, 거래내역 |
| 관심종목 | `/api/watchlist` | 관심종목 항목, 매수 규칙 |
| 전략 | `/api/strategy` | 실행, 저장/불러오기, SSE 스트리밍 |
| 스크리닝 | `/api/screening` | 조건 실행, 유니버스 |
| 검색 | `/api/search`, `/api/price` | 종목명 검색, 현재가 조회 |
| 분석 | `/api/analysis` | 종목 분석 및 AI 인사이트 |
| 리포트 | `/api/reports` | 분석 리포트 관리 |
| 시장 | `/api/market` | 마켓 캘린더, 환율 |
| 백테스트 | `/api/backtest` | 백테스트 실행 |

전체 API 문서: `http://localhost:8002/docs`

## 개발

### 백엔드

```bash
source venv/bin/activate
./venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload
```

> **팁**: `uvicorn` 직접 실행 대신 `python -m uvicorn`을 사용하세요. venv를 이동하거나 재생성하면 `uvicorn` shebang이 깨질 수 있습니다.

### 프론트엔드

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8002 PORT=3002 npm --prefix web run dev
```

또는 `web/.env.local`에 `NEXT_PUBLIC_API_URL`을 설정한 후:

```bash
cd web && PORT=3002 npm run dev
```

### CORS: `localhost` vs `127.0.0.1`

브라우저는 `localhost`와 `127.0.0.1`을 서로 다른 origin으로 취급합니다. 기본 CORS 설정은 아래 dev origin을 명시적으로 허용합니다:

- `http://localhost:3000`
- `http://localhost:3001`
- `http://localhost:3002`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:3001`
- `http://127.0.0.1:3002`

커스텀 origin을 추가하려면 `.env`에서 `CORS_ORIGINS`를 설정하세요:

```env
CORS_ORIGINS=["http://localhost:3002","http://192.168.1.100:3002"]
```

### 유용한 점검 명령

```bash
npm --prefix web run lint
npm --prefix web run check:condition-i18n
npm --prefix web run check:strategy-i18n
```

## 문제 해결

### 빠른 상태 확인

```bash
# API 헬스 체크
curl http://127.0.0.1:8002/health

# DB 준비 상태 (Postgres만 해당)
pg_isready -h localhost -p 5432
```

### 자주 발생하는 문제

- **Web에서 API 호출 실패**: `web/.env.local`의 `NEXT_PUBLIC_API_URL`이 API 포트와 일치하는지 확인
- **브라우저에서 `Failed to fetch` 발생**: 주소창의 origin(`localhost` vs `127.0.0.1`)이 CORS 허용 목록에 있는지 확인. 위의 [CORS 섹션](#cors-localhost-vs-127001) 참조
- **API 라우트에서 DB 에러 발생**: `.env`의 `DATABASE_URL`이 DB 호스트/포트와 일치하는지 확인. Docker DB: `postgresql://quant:quant@localhost:5432/quant`
- **i18n 키 에러** (`MISSING_MESSAGE`): `npm --prefix web run check:strategy-i18n` / `check:condition-i18n` 실행
- **전략 실행 결과가 비어 있음**: 유니버스/조건 임계값이 너무 엄격한지 확인
- **한국 종목명이 표시되지 않음**: pykrx 설치 여부 및 KRX 마스터 CSV 최신 상태 확인
- **매크로 패널에 unknown/unavailable 표시**: 환율 API, 선물 티커 심볼, `MACRO_INVESTOR_FLOW_PATH` 파일 확인
- **`uvicorn` 명령을 찾을 수 없음**: `uvicorn` 대신 `./venv/bin/python -m uvicorn ...` 사용

## 로드맵 / 제한사항

- 브로커 연동(Kiwoom/IBKR) 이슈 기반 진행 중
- 백그라운드 매도 규칙 모니터링 (Phase 2 — 현재는 조회 시 평가)
- 고급 퀀트 조건 단계적 확장 중
- 다중 시장 워크플로우 점진적 고도화 중

## 언어 전환

- English: [`README.md`](README.md)
- 한국어: `README_KO.md`
