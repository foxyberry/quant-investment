# Semi-Automated Stock Analysis Pipeline

## Overview

240일선 터치 종목을 자동으로 분석하고, Claude API를 활용해 저평가 종목을 찾아 매수 추천을 생성하는 반자동 파이프라인.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     ANALYSIS PIPELINE                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐                                                 │
│  │  Screening  │  Phase 1: 240일선 터치 종목 추출                │
│  └──────┬──────┘                                                 │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────┐            │
│  │           Data Enrichment (Parallel)            │            │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐     │            │
│  │  │ Technical │ │   News    │ │Fundamental│     │  Phase 2   │
│  │  │ Indicators│ │  Fetcher  │ │   Data    │     │            │
│  │  └───────────┘ └───────────┘ └───────────┘     │            │
│  └─────────────────────┬───────────────────────────┘            │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────┐            │
│  │              Claude Analysis                     │            │
│  │  ┌───────────────────────────────────────────┐  │            │
│  │  │ • 저평가 분석                              │  │  Phase 3   │
│  │  │ • 리스크 평가                              │  │            │
│  │  │ • 진입 타이밍 판단                         │  │            │
│  │  └───────────────────────────────────────────┘  │            │
│  └─────────────────────┬───────────────────────────┘            │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────┐                                                 │
│  │   Report    │  Phase 4: 리포트 생성 + 매수 추천               │
│  └─────────────┘                                                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Tasks Breakdown

### Phase 1: Screening (기존 기능 활용)
| Task ID | Task | Status | Dependency |
|---------|------|--------|------------|
| P1-1 | 240일선 터치 종목 추출 (KOSPI) | ✅ Done | - |
| P1-2 | 240일선 터치 종목 추출 (S&P 500) | ✅ Done | - |

### Phase 2: Data Enrichment (병렬 처리 가능)
| Task ID | Task | Status | Dependency | Parallel Group |
|---------|------|--------|------------|----------------|
| P2-1 | 기술적 지표 수집 모듈 | 🔧 Enhance | P1 | A |
| P2-2 | 뉴스 수집 통합 | 🔧 Enhance | P1 | A |
| P2-3 | 재무제표 수집 모듈 (신규) | ⬜ Todo | P1 | A |

**Parallel Group A**: P2-1, P2-2, P2-3은 서로 독립적이므로 동시 실행 가능

### Phase 3: Claude Analysis (신규)
| Task ID | Task | Status | Dependency |
|---------|------|--------|------------|
| P3-1 | Claude API 클라이언트 | ⬜ Todo | - |
| P3-2 | 분석 프롬프트 템플릿 | ⬜ Todo | P3-1 |
| P3-3 | 저평가 분석 로직 | ⬜ Todo | P2, P3-2 |
| P3-4 | 진입 타이밍 분석 | ⬜ Todo | P2, P3-2 |

### Phase 4: Report & Recommendation (신규)
| Task ID | Task | Status | Dependency |
|---------|------|--------|------------|
| P4-1 | 리포트 생성기 | ⬜ Todo | P3 |
| P4-2 | 포지션 사이징 계산 | ⬜ Todo | P3 |
| P4-3 | 매수 추천 출력 | ⬜ Todo | P4-1, P4-2 |

### Phase 5: Pipeline Orchestration (신규)
| Task ID | Task | Status | Dependency |
|---------|------|--------|------------|
| P5-1 | 파이프라인 스크립트 | ⬜ Todo | P1-P4 |
| P5-2 | 설정 파일 (config) | ⬜ Todo | - |

---

## Detailed Task Specifications

### P2-3: 재무제표 수집 모듈

**File**: `data_enrichment/fundamental.py`

```python
class FundamentalDataFetcher:
    def get_fundamentals(ticker: str) -> dict:
        """
        Returns:
            {
                'pe_ratio': float,      # P/E
                'pb_ratio': float,      # P/B
                'ps_ratio': float,      # P/S
                'peg_ratio': float,     # PEG
                'eps': float,           # EPS
                'revenue_growth': float,
                'profit_margin': float,
                'debt_to_equity': float,
                'roe': float,           # ROE
                'roa': float,           # ROA
                'dividend_yield': float,
                'market_cap': float,
                'sector': str,
                'industry': str,
            }
        """
```

**Data Sources**:
- US: yfinance
- KR: pykrx + 네이버 금융

---

### P3-1: Claude API 클라이언트

**File**: `llm/claude_client.py`

```python
class ClaudeAnalyzer:
    def __init__(self, api_key: str = None):
        # ANTHROPIC_API_KEY 환경변수 사용
        pass

    def analyze_stock(self, stock_profile: dict) -> AnalysisResult:
        """
        단일 종목 분석

        Args:
            stock_profile: {
                'ticker': str,
                'name': str,
                'price': float,
                'technical': dict,  # RSI, MACD, BB 등
                'fundamental': dict,  # P/E, P/B 등
                'news': list,  # 최근 뉴스
            }

        Returns:
            AnalysisResult: {
                'ticker': str,
                'valuation_score': float,  # 1-10
                'risk_score': float,  # 1-10
                'entry_recommendation': str,  # 'BUY', 'WAIT', 'AVOID'
                'reasoning': str,
                'key_risks': list,
                'catalysts': list,
            }
        """
```

---

### P3-2: 분석 프롬프트 템플릿

**File**: `llm/prompts/stock_analysis.py`

```python
VALUATION_PROMPT = """
You are a professional equity analyst. Analyze this stock for potential undervaluation.

## Stock Profile
- Ticker: {ticker}
- Name: {name}
- Current Price: {price}
- 240-day MA: {ma_240}
- Distance from MA: {distance_pct}%

## Technical Indicators
{technical_summary}

## Fundamental Data
{fundamental_summary}

## Recent News
{news_summary}

## Task
1. Is this stock undervalued? Score 1-10 (10 = extremely undervalued)
2. What are the key risks?
3. What are potential catalysts for price recovery?
4. Should I buy today, wait, or avoid?

Respond in JSON format:
{
    "valuation_score": <1-10>,
    "risk_score": <1-10, 10=highest risk>,
    "entry_recommendation": "<BUY|WAIT|AVOID>",
    "reasoning": "<2-3 sentences>",
    "key_risks": ["<risk1>", "<risk2>"],
    "catalysts": ["<catalyst1>", "<catalyst2>"]
}
"""
```

---

### P4-2: 포지션 사이징

**File**: `portfolio/position_sizing.py`

```python
class PositionSizer:
    def __init__(self, total_capital: float, max_position_pct: float = 0.1):
        """
        Args:
            total_capital: 총 투자 가능 금액
            max_position_pct: 단일 종목 최대 비중 (기본 10%)
        """
        pass

    def calculate_position(
        self,
        ticker: str,
        current_price: float,
        risk_score: float,
        stop_loss_pct: float = 0.05
    ) -> PositionRecommendation:
        """
        Returns:
            PositionRecommendation: {
                'ticker': str,
                'shares': int,
                'amount': float,
                'position_pct': float,
                'stop_loss_price': float,
                'risk_amount': float,
            }
        """
```

---

## Parallel Execution Plan

```
Time →
─────────────────────────────────────────────────────────────────►

Phase 1 (Sequential):
[P1-1: KOSPI Screening] [P1-2: S&P 500 Screening]

Phase 2 (Parallel - Group A):
┌─────────────────────────────────────────────────────────────────┐
│ [P2-1: Technical Indicators]                                    │
│ [P2-2: News Fetching]                                          │
│ [P2-3: Fundamental Data]                                        │
└─────────────────────────────────────────────────────────────────┘

Phase 3 (Sequential, but parallelizable per stock):
[P3-3: Valuation Analysis] → [P3-4: Entry Timing]

Phase 4 (Sequential):
[P4-1: Report] → [P4-2: Position Sizing] → [P4-3: Recommendation]
```

---

## File Structure (New)

```
quant-investment/
├── data_enrichment/          # Phase 2 (신규 폴더)
│   ├── __init__.py
│   ├── technical.py          # P2-1: 기술적 지표
│   ├── news.py               # P2-2: 뉴스 통합
│   └── fundamental.py        # P2-3: 재무제표
│
├── llm/                      # Phase 3 (신규 폴더)
│   ├── __init__.py
│   ├── claude_client.py      # P3-1: Claude API
│   └── prompts/
│       └── stock_analysis.py # P3-2: 프롬프트
│
├── pipeline/                 # Phase 5 (신규 폴더)
│   ├── __init__.py
│   ├── analyzer.py           # P5-1: 파이프라인 오케스트레이션
│   └── config.py             # P5-2: 설정
│
└── scripts/
    └── analysis/
        └── run_daily_analysis.py  # 메인 실행 스크립트
```

---

## Configuration

**File**: `config/analysis_config.yaml`

```yaml
pipeline:
  markets:
    - KOSPI
    - SP500

  screening:
    ma_period: 240
    touch_threshold: 0.02  # ±2%

  enrichment:
    technical_indicators:
      - RSI
      - MACD
      - BB
      - OBV
    news_days: 7
    news_max_articles: 10

  analysis:
    claude_model: "claude-sonnet-4-20250514"
    max_tokens: 1000

  position_sizing:
    total_capital: 10000000  # 1천만원
    max_position_pct: 0.1    # 최대 10%
    default_stop_loss: 0.05  # 5%

  output:
    report_dir: "reports/analysis"
    format: "markdown"
```

---

## Implementation Priority

### Sprint 1: 데이터 수집 (병렬 구현)
1. ⬜ P2-3: 재무제표 수집 모듈
2. 🔧 P2-1: 기술적 지표 통합 (기존 코드 재구성)
3. 🔧 P2-2: 뉴스 수집 통합 (기존 코드 재구성)

### Sprint 2: LLM 분석
1. ⬜ P3-1: Claude API 클라이언트
2. ⬜ P3-2: 프롬프트 템플릿
3. ⬜ P3-3: 저평가 분석

### Sprint 3: 리포트 & 추천
1. ⬜ P4-1: 리포트 생성기
2. ⬜ P4-2: 포지션 사이징
3. ⬜ P5-1: 파이프라인 스크립트

---

## Usage (Target)

```bash
# 일일 분석 실행
python scripts/analysis/run_daily_analysis.py

# 특정 마켓만
python scripts/analysis/run_daily_analysis.py --market KOSPI

# 리포트만 재생성
python scripts/analysis/run_daily_analysis.py --report-only
```

---

## Output Example

```
======================================================================
 Daily Stock Analysis Report - 2026-02-11
======================================================================

📊 Screening Results:
  KOSPI 240d MA Touch: 5 stocks
  S&P 500 240d MA Touch: 19 stocks

======================================================================
 TOP RECOMMENDATIONS
======================================================================

1. 삼성전자 (005930.KS)
   ├── Valuation Score: 8/10 (Undervalued)
   ├── Risk Score: 3/10 (Low)
   ├── Entry: BUY
   ├── Reasoning: P/E 12.3 below sector avg 18.5, strong cash flow...
   ├── Key Risks: Memory cycle, geopolitical
   ├── Catalysts: AI server demand, HBM ramp
   └── Position: ₩1,000,000 (15주 @ ₩66,500)
       Stop Loss: ₩63,175 (-5%)

2. Disney (DIS)
   ├── Valuation Score: 7/10
   ├── Risk Score: 5/10 (Medium)
   ├── Entry: WAIT
   ├── Reasoning: Streaming losses narrowing, but...
   ...

======================================================================
```
