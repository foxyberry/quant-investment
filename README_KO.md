# quant-investment

퀀트 투자 전략 개발 및 백테스팅 프로젝트

[English README](README.md)

---

## 매일 실행 (Daily Routine)

### 1. 포트폴리오 매도 신호 체크
보유 종목의 손절/익절/기술적 매도 신호 확인

```bash
python scripts/live/portfolio_sell_checker.py
```

### 2. 투자자별 매매 동향
외국인/기관 순매수/순매도 현황 확인

```bash
# 개별 종목 조회
python scripts/investor_trading.py 005930

# 외국인/기관 순매수 상위 전체 (추천)
python scripts/investor_trading.py --top 10

# 기관만 조회
python scripts/investor_trading.py --top-institution 10

# KOSDAQ 조회
python scripts/investor_trading.py --top 10 --market KOSDAQ
```

### 3. 일일 마켓 리포트
코스피/미국 종목 골든크로스/데스크로스 감지

```bash
# 한국 (코스피)
python scripts/screening/korean_daily_report.py

# 미국 (S&P 500)
python scripts/screening/us_daily_report.py
python scripts/screening/us_daily_report.py --sector Technology
```

---

## 종목 발굴 (Stock Screening)

### 매집 구간 탐지
조용한 매집 구간 종목 찾기 (저변동성 + 저거래량)

```bash
# 기본 프리셋
python scripts/screening/accumulation_screen.py --preset accumulation_basic

# OBV 다이버전스 포함 (추천)
python scripts/screening/accumulation_screen.py --preset accumulation_obv

# 더 엄격한 조건
python scripts/screening/accumulation_screen.py --preset accumulation_basic --bb-width 8.0 --volume-mult 0.7
```

### 이동평균선 스크리너
```bash
# 이평선 터치 종목
python scripts/screening/korean_ma_touch.py

# 이평선 하향 돌파 종목
python scripts/screening/korean_ma_below.py

# 이평선 크로스오버 감지
python scripts/screening/korean_crossover.py
```

### 기술적 돌파
```bash
python scripts/screening/tech_breakout.py
```

---

## 백테스팅 (전략 연구)

과거 데이터로 트레이딩 전략 테스트

```bash
# 기본 백테스트 (한국 주식)
python scripts/backtesting/run_backtest.py --ticker 005930.KS --period 1y

# 미국 주식 + EMA 전략
python scripts/backtesting/run_backtest.py --ticker AAPL --strategy ema

# 파라미터 최적화
python scripts/backtesting/run_backtest.py --ticker 005930.KS --optimize
```

**사용 가능한 전략:**
| 전략 | 설명 | 기본값 |
|------|------|--------|
| `sma` | 단순 이평선 크로스오버 | n1=10, n2=20 |
| `ema` | 지수 이평선 크로스오버 | n1=12, n2=26 |

---

## 실시간 모니터링 (Live)

### 옵션 추적 봇
NVDA, AAPL, TSLA, AMZN 옵션 거래량 이상 징후 감지

```bash
# 일회성 체크
python scripts/live/options_tracker.py --once

# 지속 모니터링 (60초마다)
python scripts/live/options_tracker.py
```

---

## 설정 파일

| 파일 | 설명 |
|------|------|
| `config/portfolio.yaml` | 보유 종목 & 매도 조건 |
| `config/screening_criteria.yaml` | 기술적 스크리닝 파라미터 |
| `config/base_config.yaml` | 데이터 경로, API, 로깅 설정 |

---

## 설치

```bash
# 클론 및 설정
git clone https://github.com/yourusername/quant-investment.git
cd quant-investment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 기술 스택
- **Python 3.13**
- **Backtesting.py** - 전략 백테스팅
- **yfinance** - 미국 주가 데이터
- **pykrx** - 한국 주식 데이터 (코스피/코스닥)
- **pandas/numpy** - 데이터 처리

---

## 프로젝트 구조

```
quant-investment/
├── scripts/
│   ├── investor_trading.py      # 투자자별 매매 동향
│   ├── screening/               # 종목 스크리닝
│   │   ├── accumulation_screen.py   # 매집 구간 탐지
│   │   ├── korean_daily_report.py   # 일일 리포트
│   │   ├── korean_crossover.py      # 이평선 크로스오버
│   │   ├── korean_ma_below.py       # 이평선 하향 돌파
│   │   └── korean_ma_touch.py       # 이평선 터치
│   ├── backtesting/             # 백테스팅
│   │   └── run_backtest.py
│   └── live/                    # 실시간 모니터링
│       ├── portfolio_sell_checker.py  # 매도 신호 체커
│       └── options_tracker.py         # 옵션 추적 봇
├── config/                      # 설정 파일
├── screener/                    # 스크리닝 라이브러리
├── engine/                      # 백테스팅 엔진
├── discovery/                   # 종목 발굴
├── portfolio/                   # 포트폴리오 관리
└── data/                        # 데이터 캐시
```

---

## 문서

- [한국 주식 MA 스크리너](docs/KOREAN_MA_SCREENER.md)
- [옵션 추적 봇](docs/OPTIONS_TRACKER_README.md)
- [마켓 캘린더](docs/MARKET_CALENDAR_README.md)

---

## 라이선스

MIT
