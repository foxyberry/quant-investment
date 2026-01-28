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

## 7. 주의사항

- 새 전략은 반드시 `scripts/` 하위에 추가
- 데이터 캐시는 `data/cache/`에 저장됨
- 로그는 `logs/quant_investment.log` 확인
- `config/portfolio.yaml`은 gitignore됨 (민감 정보)
- API 키는 환경 변수로 관리

---

## 8. 현재 진행 중인 작업

`docs/works/` 폴더의 작업 계획 문서 참조

### 완료된 Epic
- Epic 0: Backtesting Framework (#5, #8, #9)
- Epic 1: Stock Discovery (#6, #10-17)
- Epic 2: Portfolio Monitoring (#7, #18-26)
