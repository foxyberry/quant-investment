# quant-investment

퀀트 투자 전략 개발 및 백테스팅 프로젝트

[English README](README.md)

## 기술 스택
- **Backtesting.py** - 전략 백테스팅 프레임워크
- **yfinance** - 미국 주가 데이터 수집
- **pykrx** - 한국 주식 데이터 (코스피/코스닥)
- **pandas/numpy** - 데이터 처리
- **matplotlib/seaborn** - 시각화

## 설치

```bash
pip install -r requirements.txt
```

### 버전 확인
```bash
pip show yfinance
# Name: yfinance
# Version: 0.2.63
```

## 프로젝트 구조

```
quant-investment/
├── run.py                        # 메인 진입점 (전략 오케스트레이터)
│
├── config/                       # 설정 파일
│   ├── base_config.yaml          # 기본 설정
│   ├── portfolio.yaml            # 포트폴리오 보유종목 & 매도 조건
│   ├── korean_screening.yaml     # 한국 주식 스크리닝 설정
│   └── screening_criteria.yaml   # 기술적 스크리닝 조건
│
├── engine/                       # 백테스팅 엔진
│   ├── backtesting_engine.py     # Backtesting.py 래퍼
│   ├── metrics.py                # 성능 지표 (Sharpe, MDD 등)
│   └── strategies/               # 트레이딩 전략
│       └── ma_cross.py           # 이동평균 크로스오버 전략
│
├── models/                       # 데이터 모델
│   ├── condition.py              # 퀀트 조건 스키마 (17가지 타입)
│   ├── watchlist.py              # 관심종목 관리
│   └── price_target.py           # 목표가 설정
│
├── discovery/                    # 종목 발굴
│   ├── evaluator.py              # 조건 평가 엔진
│   ├── indicators.py             # 기술적 지표 (RSI, MACD, BB)
│   └── decision.py               # 매수 결정 로직 (점수화)
│
├── portfolio/                    # 포트폴리오 관리
│   ├── holdings.py               # 보유 종목 CRUD
│   ├── monitor.py                # 가격 모니터링 (폴링)
│   ├── trigger.py                # 조건 트리거 감지
│   ├── conditions.py             # 매매 조건 IoC 패턴
│   ├── quantity.py               # 매수/매도 수량 계산
│   ├── executor.py               # 주문 실행 (Paper/Live)
│   ├── risk.py                   # 위험 관리 규칙
│   └── notifier.py               # 알림 (텔레그램/슬랙)
│
├── scripts/                      # 실행 스크립트
│   ├── backtesting/              # 백테스팅 스크립트
│   │   └── run_backtest.py       # CLI 백테스트 실행기
│   ├── screening/                # 종목 스크리닝 스크립트
│   │   ├── korean_daily_report.py    # 일일 리포트 (골든/데스크로스)
│   │   ├── korean_crossover.py       # 이평선 크로스오버 감지
│   │   ├── korean_ma_below.py        # 이평선 하향 돌파 종목
│   │   ├── korean_ma_touch.py        # 이평선 터치 종목
│   │   └── tech_breakout.py          # 기술적 돌파 스크리너
│   └── live/                     # 실전 거래/봇
│       ├── portfolio_sell_checker.py     # 포트폴리오 매도 신호 체커
│       ├── options_tracker.py            # 옵션 거래량 추적 봇
│       └── global_dual_momentum_2025.py  # 듀얼 모멘텀 전략
│
├── screener/                     # 종목 스크리닝 라이브러리
│   ├── basic_filter.py           # 기본 정보 필터 (가격, 거래량, 시총)
│   ├── technical_filter.py       # 기술적 지표 필터
│   ├── external_filter.py        # 외부 데이터 필터
│   ├── portfolio_manager.py      # 포트폴리오 관리
│   └── korean/                   # 한국 주식 스크리너
│       ├── kospi_fetcher.py      # 코스피/코스닥 데이터 조회
│       └── ma_screener.py        # 이동평균선 스크리너
│
├── utils/                        # 유틸리티
│   ├── fetch.py                  # 주가 데이터 수집 (yfinance)
│   ├── options_fetch.py          # 옵션 데이터 수집
│   ├── config_manager.py         # 설정 파일 관리
│   └── timezone_utils.py         # 시간대 유틸리티
│
├── data/                         # 데이터 저장소 & 캐시
├── logs/                         # 로그 파일
├── reports/                      # 생성된 리포트
└── docs/                         # 문서
    ├── examples/                 # 예제 및 템플릿
    ├── ko/                       # 한글 문서
    └── works/                    # 작업 계획 문서
```

## 빠른 시작

### 1. 전략 실행
```bash
# 가상환경 활성화
source venv/bin/activate

# 전략 오케스트레이터 실행
python run.py
```

### 2. 옵션 추적 봇 실행
```bash
# 일회성 체크
python scripts/live/options_tracker.py --once

# 지속적 모니터링 (60초마다)
python scripts/live/options_tracker.py
```

자세한 내용은 [docs/OPTIONS_TRACKER_README.md](docs/OPTIONS_TRACKER_README.md) 참고

### 3. 포트폴리오 매도 신호 확인
```bash
# config/portfolio.yaml에 보유 종목 추가 후 실행
python scripts/live/portfolio_sell_checker.py
```

### 4. 종목 발굴 (매수 신호 분석)
```python
from discovery import analyze_buy_signal

decision = analyze_buy_signal("005930.KS")
print(decision.summary())
# Recommendation: HOLD, Score: 54/100, Risk: HIGH
```

### 5. 포트폴리오 관리 & 모의 거래
```python
from portfolio import Portfolio, OrderExecutor, Order

# 보유 종목 관리
portfolio = Portfolio()
portfolio.add("005930.KS", quantity=10, avg_price=70000)

# 모의 거래 (Paper Trading)
executor = OrderExecutor(dry_run=True)
order = Order("005930.KS", "SELL", quantity=5)
result = executor.execute(order, market_price=80000)
print(f"시뮬레이션 손익: {result.fill_price * result.fill_quantity:,.0f}")
```

### 6. 백테스트 실행
```bash
# 기본 백테스트 (한국 주식) - 기본값 SMA(10,20) 사용
python scripts/backtesting/run_backtest.py --ticker 005930.KS --period 1y

# 미국 주식 + EMA 전략
python scripts/backtesting/run_backtest.py --ticker AAPL --strategy ema

# 이평선 기간 직접 지정
python scripts/backtesting/run_backtest.py --ticker AAPL --strategy sma --n1 5 --n2 30

# 파라미터 최적화
python scripts/backtesting/run_backtest.py --ticker 005930.KS --optimize
```

**사용 가능한 전략:**
| 전략 | 설명 | 기본 파라미터 |
|------|------|---------------|
| `sma` | 단순 이평선 크로스오버 (기본값) | n1=10, n2=20 |
| `ema` | 지수 이평선 크로스오버 | n1=12, n2=26 |
| `ma_touch` | 이평선 터치 후 반등 | ma_period=20 |

### 7. 한국 주식 스크리너 실행
```bash
# 일일 리포트 (골든/데스크로스 감지)
python scripts/screening/korean_daily_report.py

# 이동평균선 스크리너
python scripts/screening/korean_ma_below.py
python scripts/screening/korean_ma_touch.py
```

자세한 내용은 [docs/KOREAN_MA_SCREENER.md](docs/KOREAN_MA_SCREENER.md) 참고

### 8. 새 전략 만들기

1. 템플릿 복사
```bash
cp docs/examples/screening_template.py scripts/screening/my_strategy.py
```

2. 전략 수정
```python
# scripts/screening/my_strategy.py 편집
def run():
    # 여기에 전략 로직 작성
    pass
```

3. `run.py`에서 실행
```bash
python run.py scripts/screening/my_strategy.py
```

## 최근 업데이트

### 포트폴리오 모니터링 시스템 (2026-01)
- 보유 종목 관리 (평균 매수가 자동 계산)
- 가격 모니터링 (폴링 방식 + 콜백)
- 조건 트리거 감지 (목표가, 손절가)
- 매매 조건 IoC 패턴 (커스텀 매도 조건)
- Paper Trading (가상 잔고 시뮬레이션)
- 위험 관리 규칙 (포지션 한도, 일일 손실 한도)
- 알림 시스템 (텔레그램, 슬랙, 콘솔)

### 종목 발굴 시스템 (2026-01)
- 퀀트 조건 스키마 (17가지 조건 타입)
- 기술적 지표 (RSI, MACD, 볼린저, MA 5/20/60/120/240)
- 매수 결정 로직 (STRONG_BUY/BUY/HOLD/WAIT 점수화)
- 관심종목 & 목표가 관리

### 백테스팅 프레임워크 (2026-01)
- Backtesting.py 기반 전략 테스트
- 이동평균 크로스오버 전략 (SMA, EMA)
- 성능 지표: Sharpe, Sortino, MDD, Win Rate, CAGR
- 실행: `python scripts/backtesting/run_backtest.py --ticker AAPL`

### 포트폴리오 매도 알림 (2026-01)
- `config/portfolio.yaml`로 보유 종목 관리
- 매도 신호 감지 (손절, 익절, 트레일링 스탑)
- 기술적 매도 신호 (20일선 이탈, 데스크로스)
- 실행: `python scripts/live/portfolio_sell_checker.py`

### 한국 주식 일일 리포트 (2026-01)
- 코스피 종목 골든/데스크로스 감지
- `reports/` 폴더에 일일 리포트 자동 저장

### 프로젝트 정리 (2026-01)
- backtrader 의존성 제거 (미사용)
- 레거시 코드 정리 (`lib/`, `scripts/legacy/`, `visualizer/`)
- 프로젝트 구조 단순화

### 옵션 추적 봇 (2025-01)
- NVDA, AAPL, TSLA, AMZN 옵션 거래량 이상 징후 감지
- 5일 평균 대비 2~3배 급증 시 알림

### 한국 주식 MA 스크리너 (2025-01)
- 코스피 종목 이동평균선 분석
- 60일, 120일, 200일, 240일, 365일선 지원

## 문서

- [한국 주식 MA 스크리너](docs/KOREAN_MA_SCREENER.md)
- [Market Calendar](docs/MARKET_CALENDAR_README.md)
- [옵션 추적 봇](docs/OPTIONS_TRACKER_README.md)
- [코드 품질 리포트](docs/code_quality_report.md)

## 기여하기

새 전략은 `scripts/` 아래 적절한 하위 폴더에 추가해주세요:
- `backtesting/` - 백테스팅 스크립트
- `screening/` - 종목 스크리닝
- `live/` - 실전 거래/봇

## 라이선스

MIT
