# quant-investment

스크리닝, 전략 설계, 백테스팅, 포트폴리오 모니터링, 분석을 하나로 연결한 퀀트 투자 워크스페이스입니다.

언어: [English README](README.md)

## 이 프로젝트는 무엇인가요?

`quant-investment`는 아래를 통합합니다.
- FastAPI 백엔드: 스크리닝/전략 실행/포트폴리오 API
- Next.js 웹 UI: 일상적인 퀀트 작업 흐름 제공
- Python 연구/실행 모듈: 데이터, 지표, 백테스트

핵심 목표는 아이디어를 실행 가능한 전략으로 빠르게 연결하는 것입니다.

## UI에서 할 수 있는 일

| 영역 | 경로 | 가능한 작업 |
|---|---|---|
| 대시보드 | `/[locale]` | 시장/포트폴리오 요약, 최근 상태 확인 |
| 스크리닝 | `/[locale]/screening` | 조건 조합, 스캔 실행, 통과 종목 확인 |
| 전략 빌더 | `/[locale]/strategy` | 노드 기반 전략 그래프 구성, 저장/불러오기, 실행 |
| 백테스트 | 전략 페이지 패널 | 기간/파라미터 기반 전략 성능 검증 |
| 포트폴리오 | `/[locale]/portfolio` | 보유 종목, 포지션, 주문 데스크 확인 |
| 분석/리포트 | `/[locale]/analysis`, `/[locale]/reports` | 차트/지표/분석 리포트 확인 |

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

### 3) 실행 (권장 개발 포트)

API (`8002`):
```bash
source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload
```

Web (`3002`):
```bash
cd web && PORT=3002 npm run dev
```

### 4) 접속

- Web UI: `http://localhost:3002`
- API 문서: `http://localhost:8002/docs`

## 핵심 작업 시나리오

### 시나리오 A: 전략 생성 후 실행

1. 전략 빌더(`/[locale]/strategy`) 접속
2. 유니버스/조건 노드 배치
3. 조건 파라미터 조정
4. 배포/실행 버튼 클릭
5. 매칭 결과와 중간 결과 확인

### 시나리오 B: 전략 검증(백테스트)

1. 전략 저장 또는 불러오기
2. 백테스트 패널 열기
3. 기간/입력값 선택
4. 결과(수익곡선/거래내역/지표) 검토

### 시나리오 C: 스크리닝에서 분석으로

1. `/[locale]/screening`에서 스캔 실행
2. 종목 분석 페이지 이동
3. 기술/재무/AI 컨텍스트 확인
4. 리포트 흐름으로 연결

## 설정

### 주요 설정 파일

- `config/base_config.yaml`: 전역 런타임/데이터/로깅
- `config/screening_criteria.yaml`: 스크리닝 기본값
- `portfolio/`: 포트폴리오 로직 및 포지션 사이징 모듈

### 환경 변수

| 변수 | 용도 |
|---|---|
| `ANTHROPIC_API_KEY` | AI 분석 연동 |
| `FINNHUB_API_KEY` | 선택적 뉴스/데이터 소스 |
| `MARKETAUX_API_KEY` | 선택적 뉴스/데이터 소스 |

## API/Web 개발

### 백엔드

```bash
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload
```

### 프론트엔드

```bash
cd web
PORT=3002 npm run dev
```

### 유용한 점검 명령

```bash
npm --prefix web run lint
npm --prefix web run check:condition-i18n
npm --prefix web run check:strategy-i18n
```

## 문제 해결

- Web에서 API 호출 실패:
  - API 실행 포트 확인
  - 프론트 API 베이스 URL/env 확인
- i18n 키 에러(`MISSING_MESSAGE`):
  - `npm --prefix web run check:strategy-i18n`
  - `npm --prefix web run check:condition-i18n`
- 전략 실행 결과가 비어 있음:
  - 유니버스/조건 임계값이 너무 엄격한지 확인

## 로드맵 / 제한사항

- 브로커 연동(Kiwoom/IBKR)은 이슈 기반으로 진행 중
- 고급 퀀트 조건은 단계적으로 확장 중
- 다중 시장 워크플로우는 점진적으로 고도화 중

## 언어 전환 (EN/KO)

- 영문 기준 문서: `README.md`
- 한국어 문서: `README_KO.md`
