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

## AI 기반 주식 분석 (신규!)

Claude AI를 활용한 반자동 분석 파이프라인:
1. 240일선 터치 종목 스크리닝
2. 기술적 지표, 재무제표, 뉴스 데이터 수집
3. Claude AI로 저평가 분석 및 진입 타이밍 판단
4. 포지션 사이징 포함 리포트 생성

### 옵션 1: Claude API 사용

```bash
# 전체 분석 (ANTHROPIC_API_KEY 필요)
export ANTHROPIC_API_KEY="your-api-key"
python scripts/analysis/run_daily_analysis.py

# 단일 마켓
python scripts/analysis/run_daily_analysis.py --market KOSPI
python scripts/analysis/run_daily_analysis.py --market SP500
```

### 옵션 2: Claude Code 연동

```bash
# 스크리닝 + 데이터 수집, JSON으로 저장
python scripts/analysis/run_daily_analysis.py --claude-code

# 이후 Claude Code에서 /analyze-stocks 스킬 사용
# 또는 저장된 JSON 파일을 Claude Code에게 분석 요청
```

### 기타 옵션

```bash
# 데이터 수집만 (분석 없이)
python scripts/analysis/run_daily_analysis.py --enrich-only

# 자본금 설정 (포지션 사이징용)
python scripts/analysis/run_daily_analysis.py --capital 50000000
```

**분석 결과:**
- 저평가 점수 (1-10)
- 리스크 평가
- 진입 추천 (BUY/WAIT/AVOID)
- 손절가 포함 포지션 사이징

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

### 돌파 감지
```bash
# 새로운 조건 기반 스크리너 사용
from screener import StockScreener, BottomBreakoutCondition, BreakoutWithVolumeCondition
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
| `config/base_config.yaml` | 데이터 경로, API, 로깅 설정 |

**환경 변수:**
| 변수 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API 키 (AI 분석용) |
| `FINNHUB_API_KEY` | Finnhub API 키 (뉴스, 선택) |
| `MARKETAUX_API_KEY` | Marketaux API 키 (뉴스, 선택) |

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
- **Claude API** - AI 기반 주식 분석
- **Backtesting.py** - 전략 백테스팅
- **yfinance** - 미국 주가 데이터
- **pykrx** - 한국 주식 데이터 (코스피/코스닥)
- **pandas/numpy** - 데이터 처리

---

## 프로젝트 구조

```
quant-investment/
├── scripts/
│   ├── analysis/               # AI 기반 분석
│   │   └── run_daily_analysis.py
│   ├── screening/              # 종목 스크리닝
│   │   ├── accumulation_screen.py
│   │   ├── korean_daily_report.py
│   │   ├── us_daily_report.py
│   │   └── korean_ma_*.py
│   ├── backtesting/            # 백테스팅
│   │   └── run_backtest.py
│   └── live/                   # 실시간 모니터링
│       ├── portfolio_sell_checker.py
│       └── options_tracker.py
├── llm/                        # Claude AI 연동
│   ├── claude_client.py
│   ├── stock_analyzer.py
│   └── prompts/
├── data_enrichment/            # 데이터 수집 모듈
│   ├── technical.py
│   ├── fundamental.py
│   └── news.py
├── pipeline/                   # 분석 파이프라인
│   └── report_generator.py
├── screener/                   # 스크리닝 라이브러리
│   ├── conditions/             # 스크리닝 조건
│   └── stock_screener.py
├── portfolio/                  # 포트폴리오 관리
│   └── position_sizing.py
├── config/                     # 설정 파일
└── data/                       # 데이터 캐시
```

---

## 문서

- [백엔드 핵심 로직 개요 (데이터 수집/스크리닝/전략 실행)](docs/ko/BACKEND_LOGIC_OVERVIEW.md)
- [돌파 조건 (Breakout Conditions)](docs/BREAKOUT_CONDITIONS.md)
- [한국 주식 MA 스크리너](docs/KOREAN_MA_SCREENER.md)
- [옵션 추적 봇](docs/OPTIONS_TRACKER_README.md)
- [마켓 캘린더](docs/MARKET_CALENDAR_README.md)
- [분석 파이프라인 계획](docs/works/20260211_semi_auto_analysis_pipeline.md)

---

## 라이선스

MIT
