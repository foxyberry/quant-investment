# Portfolio Data Flow & Caching Architecture

이 문서는 [영문 버전](../PORTFOLIO_DATA_FLOW.md)의 번역입니다.

포트폴리오 서비스가 보유 종목 데이터를 어떻게 가져오고, 캐싱하고, 응답하는지 설명합니다.

## 전체 흐름

```
브라우저 요청
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI 라우터 (api/routers/portfolio.py)                │
│  GET /api/portfolio/holdings                              │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│  PortfolioService (api/services/portfolio_service.py)     │
│                                                          │
│  1. DB 조회 ─── SQLite (holdings 테이블)                  │
│     ~1-5 ms   정적 데이터: ticker, qty, avg_price,       │
│               sector, industry, country, exchange        │
│                                                          │
│  2. 가격 보강 ─── ThreadPoolExecutor(2) 병렬 실행         │
│     ├── _get_current_prices()                            │
│     │   TTLCache(60초) → OHLCVCache(parquet) → yfinance  │
│     │   ~0ms (캐시) / ~2-8초 (콜드)                      │
│     └── _get_daily_changes()                             │
│         TTLCache(60초) → OHLCVCache(parquet)              │
│         ~0ms (캐시) / ~2-8초 (콜드)                      │
│                                                          │
│  3. 손익 계산 ─── 인메모리, 즉시                          │
└──────────────────────────────────────────────────────────┘
```

## 데이터 분류

| 필드 | 분류 | 데이터 소스 | 조회 시점 |
|------|------|------------|----------|
| ticker, name, quantity, avg_price | **정적** | SQLite DB | 페이지 로드 (DB 조회) |
| sector, industry, country, exchange | **정적** | SQLite DB | 종목 생성 시 1회 저장 |
| current_price | **동적** | yfinance / pykrx | 매 요청 (캐시 적용) |
| change_pct | **동적** | OHLCV에서 계산 | 매 요청 (캐시 적용) |
| market_value, pnl, pnl_pct | **파생** | 인메모리 계산 | 매 요청 |
| cost_basis | **파생** | quantity * avg_price | 매 요청 |

## 캐싱 레이어

### Layer 1: TTLCache (인메모리)

```
파일: utils/ttl_cache.py
구조: 티커별 OrderedDict + LRU 제거
스레드 안전: RLock + 키별 잠금 (thundering-herd 방지)
```

| 캐시 인스턴스 | TTL | 최대 크기 | 용도 |
|--------------|-----|----------|------|
| `_price_cache` | 60초 | 512 | 현재가 |
| `_change_cache` | 60초 | 512 | 일간 변동률 |
| `_sector_cache` | 3600초 | 512 | 업종명 (레거시, `_get_sectors()`에서 사용) |

**동작**: 캐시 히트 시 즉시 반환 (~0ms). 미스 시 Layer 2로 전달.

### Layer 2: OHLCVCache (디스크 Parquet)

```
파일: utils/data_cache.py
구조: 티커별 Parquet 파일
위치: data/cache/ohlcv/{ticker}.parquet
신선도: 18시간 (STALE_HOURS)
```

**동작**:
- 티커당 최대 730일 (2년) OHLCV 데이터 보관
- 신선 = 캐시 최신 날짜 >= 최근 거래일 (주말 보정)
- 히트 시: Parquet 파일 읽기, 마지막 종가 추출 (~5-20ms)
- 미스 시: 외부 API에서 가져오기, Parquet 저장 후 반환
- 증분 업데이트 지원 (누락된 날짜만 가져옴)
- 메타데이터 캐시로 Parquet 반복 읽기 방지

### Layer 3: 외부 API (네트워크)

| 시장 | 주 API | 폴백 | 일반 지연 |
|------|--------|------|----------|
| 한국 (.KS, .KQ) | pykrx | yfinance | 1-5초/종목 |
| 미국/기타 | yfinance | 없음 | 1-3초/종목 |

**배치 최적화**: `get_latest_prices()`는 다수 종목 미스 시 `yf.download()`로 단일 네트워크 호출 수행.

## 응답 시간 예상

| 시나리오 | 예상 시간 | 병목 |
|---------|---------|------|
| 전체 가격 캐시됨 (웜) | **50-100ms** | DB 읽기 + JSON 직렬화 |
| 부분 캐시 (일부 종목 만료) | **2-5초** | yfinance 배치 다운로드 |
| 콜드 스타트 (캐시 없음) | **5-15초** | N개 병렬 yfinance 호출 |
| DB만 (with_prices=false) | **5-20ms** | SQLite 쿼리만 |

## 상세 흐름: `get_all_holdings()`

```python
# Step 1: SQLite에서 전체 보유 종목 조회
db = SessionLocal()
rows = db.query(Holding).all()           # ~1-5ms
holdings_dicts = [_row_to_dict(r) for r in rows]
db.close()

# Step 2: 병렬 보강 (ThreadPoolExecutor, max_workers=2)
with ThreadPoolExecutor(2) as outer:
    f_prices  = outer.submit(_get_current_prices, tickers)   # 스레드 A
    f_changes = outer.submit(_get_daily_changes, tickers)    # 스레드 B
    # 두 스레드 동시 실행
    prices  = f_prices.result(timeout=30)
    changes = f_changes.result(timeout=30)

# Step 3: 응답 객체 생성 (인메모리, ~0ms)
for h in holdings_dicts:
    _holding_to_response(h, prices[ticker], sector=h["sector"], ...)
```

### 가격 조회 상세 (`_get_current_prices`)

```
각 티커별:
  1. TTLCache 확인 (60초) ──── 히트? → 즉시 반환
  2. OHLCVCache.get_latest_prices() 확인
     a. 신선한 Parquet 존재? → 메타데이터 캐시에서 종가 읽기
     b. 만료? → 배치 조회 목록에 추가
  3. 배치: yf.download(missing_tickers, period="10d")
  4. 폴백: 티커별 ThreadPoolExecutor(max_workers=8)
```

## 데이터베이스 스키마

### `holdings` 테이블

```sql
CREATE TABLE holdings (
    ticker     VARCHAR(20)  PRIMARY KEY,
    name       VARCHAR(100),
    quantity   INTEGER      NOT NULL,
    avg_price  FLOAT        NOT NULL,
    currency   VARCHAR(10)  DEFAULT 'KRW',
    note       TEXT,
    bought_at  DATE,
    -- 정적 메타데이터 (생성 시 1회 저장)
    sector     VARCHAR(128),
    industry   VARCHAR(128),
    country    VARCHAR(64),
    exchange   VARCHAR(32)
);
```

### `trades` 테이블

```sql
CREATE TABLE trades (
    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
    ticker            VARCHAR(20)  NOT NULL,
    name              VARCHAR(100),
    trade_type        VARCHAR(10)  NOT NULL,  -- BUY, SELL, ADJUST
    quantity          INTEGER      NOT NULL,
    price             FLOAT        NOT NULL,
    fee               FLOAT        DEFAULT 0,
    tax               FLOAT        DEFAULT 0,
    realized_pnl      FLOAT,
    avg_price_at_trade FLOAT,
    currency          VARCHAR(10),
    note              TEXT,
    traded_at         DATE,
    created_at        DATETIME     DEFAULT CURRENT_TIMESTAMP
);
```

## 정적 메타데이터 흐름

정적 메타데이터(sector, industry, country, exchange)는 종목 최초 생성 시 **1회만** 가져와서 DB에 영구 저장됩니다.

```
신규 종목 생성
    │
    ├── 한국 주식 (.KS/.KQ)
    │   ├── sector ← SectorFetcher (pykrx → CSV 폴백)
    │   ├── industry ← NULL (pykrx에서 미제공)
    │   ├── country ← "South Korea" (suffix에서 추론)
    │   └── exchange ← "KOSPI" 또는 "KOSDAQ" (suffix에서 추론)
    │
    └── 미국/기타 주식
        ├── sector ← yfinance Ticker.info["sector"]
        ├── industry ← yfinance Ticker.info["industry"]
        ├── country ← yfinance Ticker.info["country"]
        └── exchange ← yfinance Ticker.info["exchange"]
```

### 백필 (서버 시작 시)

서버 시작 시 데몬 스레드가 NULL 컬럼이 있는 기존 종목의 메타데이터를 자동 채웁니다:

```
api/main.py → lifespan() → threading.Thread(_backfill_metadata)
  │
  ├── 한국 주식: SectorFetcher 배치 (KOSPI/KOSDAQ)
  └── 미국 주식: yfinance 병렬 (ThreadPoolExecutor, max_workers=8)
```

서버 시작을 차단하지 않고 백그라운드에서 실행됩니다.

## 환율 서비스 흐름

`get_summary(base_currency=...)` 다중 통화 포트폴리오에서만 사용됩니다.

```
ExchangeRateService (api/services/exchange_rate_service.py)
    │
    ├── 인메모리 캐시 (Dict + monotonic 타임스탬프)
    │   TTL: 3600초 (1시간)
    │
    └── 외부: frankfurter.app/latest?from={base}&to=KRW,SGD,...
        타임아웃: 8초
        폴백: 실패 시 만료된 캐시 데이터 반환
```

## WebSocket 실시간 피드

```
WS /api/portfolio/realtime/ws?tickers=AAPL,005930.KS
    │
    └── 매 10초:
        1. get_all_holdings(with_prices=False)  → 티커 목록
        2. _get_current_prices(tickers)         → 최신 가격
        3. JSON 전송: { "updates": [{ticker, current_price, currency}] }
```

## API 엔드포인트

| 메서드 | 경로 | 서비스 메서드 | 외부 호출 |
|--------|------|-------------|----------|
| GET | `/api/portfolio` | `get_all_holdings()` + `get_summary()` | 가격 + 변동률 |
| GET | `/api/portfolio/holdings` | `get_all_holdings()` | 가격 + 변동률 |
| GET | `/api/portfolio/holdings/{ticker}` | `get_holding()` | 가격 + 변동률 |
| POST | `/api/portfolio/holdings` | `add_holding()` | 가격 + 메타데이터 (신규만) |
| PUT | `/api/portfolio/holdings/{ticker}` | `update_holding()` | 가격 |
| POST | `/api/portfolio/holdings/{ticker}/add-purchase` | `add_purchase()` | 가격 |
| DELETE | `/api/portfolio/holdings/{ticker}` | `remove_holding()` | 없음 |
| GET | `/api/portfolio/summary` | `get_summary()` | 가격 + 변동률 + 환율 |
| GET | `/api/portfolio/sell-signals` | `get_sell_signals()` | 가격 + 변동률 |
| POST | `/api/portfolio/trades` | `record_sell()` | 없음 |
| GET | `/api/portfolio/trades` | `get_trade_history()` | 없음 |
| WS | `/api/portfolio/realtime/ws` | `_get_current_prices()` | 가격 (10초마다) |

## 파일 구조

```
api/
├── routers/portfolio.py           # HTTP 엔드포인트 + WebSocket
├── services/
│   ├── portfolio_service.py       # 핵심 비즈니스 로직, 캐싱, 보강
│   └── exchange_rate_service.py   # 환율 (frankfurter.app, 1시간 TTL)
├── models/portfolio.py            # SQLAlchemy ORM (Holding, Trade)
├── schemas/portfolio.py           # Pydantic 요청/응답 모델
└── database.py                    # 엔진, 세션, 마이그레이션

utils/
├── ttl_cache.py                   # 인메모리 TTL 캐시 (범용)
└── data_cache.py                  # OHLCV 디스크 캐시 (Parquet)
```

## 관련 문서

- [전략 빌더](./STRATEGY_BUILDER_README.md) - 동일한 OHLCVCache를 사용하는 전략 실행
- [마켓 캘린더](./MARKET_CALENDAR_README.md) - 거래일 계산
