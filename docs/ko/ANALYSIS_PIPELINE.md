# 분석 파이프라인

이 문서는 Claude AI를 사용하여 종목을 스크리닝, 데이터 보강, 분석하는 일일 주식 분석 파이프라인을 설명합니다.

---

## 파이프라인 개요

```
+-------------------------------------------------------------+
|  1. Screening (종목 발굴)                                     |
|     240일 이동평균선 터치 종목 필터링                            |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  2. Enrichment (데이터 수집)                                  |
|     기술적/재무/뉴스 데이터 추가                                 |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  3. Analysis (분석)                                          |
|     Claude API 또는 Claude Code로 분석                        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  4. Report (리포트 생성)                                      |
|     BUY/WAIT/AVOID + 포지션 사이징                            |
+-------------------------------------------------------------+
```

---

## 한국 vs 미국 차이점

| 항목 | KOSPI (한국) | S&P 500 (미국) |
|------|-------------|----------------|
| **종목 리스트** | `KospiListFetcher` (pykrx) | `UsStockFetcher` (Wikipedia) |
| **최소 가격** | 1,000원 | $5 |
| **최소 거래량** | 100,000주 | 500,000주 |
| **티커 형식** | `005930.KS` | `AAPL` |
| **통화** | KRW (원) | USD (달러) |

---

## 데이터 소스

**동일하게 사용:**

- **OHLCV 데이터**: `OHLCVCache` - yfinance 사용 (캐시 적용)
- **기술적 지표**: `TechnicalEnricher` (RSI, MACD, 볼린저 밴드, OBV, 스토캐스틱)
- **재무 데이터**: `FundamentalEnricher` - yfinance `.info` 사용
- **뉴스**: `NewsEnricher` - Finnhub/Marketaux API 사용

---

## 현재 이슈

한국 주식의 경우 yfinance에서 재무 데이터(P/E, 시가총액 등)가 null로 나오는 경우가 많습니다. 미국 주식은 대부분 정상적으로 작동합니다.

한국 주식 재무 데이터 개선을 위해 KRX나 네이버 금융 등 별도 소스가 필요합니다.

---

## 사용법

### 사전 준비

1. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

2. 환경 변수 설정 (선택):
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"    # Claude API 분석용
   export FINNHUB_API_KEY="your-api-key"      # 뉴스용 (선택)
   export MARKETAUX_API_KEY="your-api-key"    # 뉴스용 (선택)
   ```

### 기본 명령어

```bash
# Claude API로 전체 분석 (ANTHROPIC_API_KEY 필요)
python scripts/analysis/run_daily_analysis.py

# 단일 마켓만 분석
python scripts/analysis/run_daily_analysis.py --market KOSPI
python scripts/analysis/run_daily_analysis.py --market SP500

# 데이터 수집만 (Claude 분석 없이)
python scripts/analysis/run_daily_analysis.py --enrich-only

# Claude Code 연동 (수동 분석용 JSON 저장)
python scripts/analysis/run_daily_analysis.py --claude-code

# 포지션 사이징용 자본금 지정
python scripts/analysis/run_daily_analysis.py --capital 50000000
```

### 명령줄 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--market`, `-m` | `ALL` | 분석할 시장: `ALL`, `KOSPI`, `SP500` |
| `--capital`, `-c` | `10000000` | 포지션 사이징용 총 자본금 |
| `--enrich-only` | `false` | 스크리닝과 데이터 수집만 실행 |
| `--claude-code` | `false` | Claude Code 분석용 JSON 저장 |
| `--ma-period` | `240` | 스크리닝용 이동평균 기간 |
| `--threshold` | `0.02` | MA 터치 임계값 (2%) |

### Claude Code 연동

`--claude-code` 플래그 사용 시:

1. 파이프라인을 실행하여 보강된 JSON 생성:
   ```bash
   python scripts/analysis/run_daily_analysis.py --claude-code
   ```

2. 보강된 데이터가 `data/analysis/enriched_{market}_{date}.json`에 저장됩니다.

3. Claude Code에서:
   - `/analyze-stocks` 스킬 사용 (설정된 경우)
   - 저장된 JSON 파일을 직접 분석하도록 요청

### 출력 결과

파이프라인은 다음을 생성합니다:

- **밸류에이션 점수** (1-10): 현재 가격에서의 매력도
- **리스크 점수** (1-10): 변동성과 펀더멘털 기반 위험 평가
- **진입 추천**: `BUY`, `WAIT`, 또는 `AVOID`
- **포지션 사이징**: 손절가와 함께 제안된 포지션 규모
- **분석 근거**: 각 추천에 대한 상세 설명

리포트는 `data/reports/` 디렉토리에 저장됩니다.

---

## 아키텍처

```
scripts/analysis/run_daily_analysis.py
        |
        +-- screener/
        |       +-- stock_screener.py      # 핵심 스크리닝 엔진
        |       +-- kospi_fetcher.py       # KOSPI 종목 리스트
        |       +-- us_fetcher.py          # S&P 500 종목 리스트
        |       +-- conditions/            # 스크리닝 조건들
        |
        +-- data_enrichment/
        |       +-- technical.py           # 기술적 지표
        |       +-- fundamental.py         # 재무 데이터
        |       +-- news.py                # 뉴스 수집
        |
        +-- llm/
        |       +-- stock_analyzer.py      # Claude API 연동
        |       +-- prompts/               # 분석 프롬프트
        |
        +-- pipeline/
        |       +-- report_generator.py    # 리포트 생성
        |
        +-- portfolio/
                +-- position_sizing.py     # 포지션 사이징 로직
```

---

## 관련 문서

- [돌파 조건](BREAKOUT_CONDITIONS.md)
- [한국 MA 스크리너](KOREAN_MA_SCREENER.md)
- [스크리너 README](SCREENER_README.md)
