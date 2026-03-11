# Portfolio Data Flow & Caching Architecture

How the portfolio service fetches, caches, and serves holding data.

## Quick Overview

```
Browser Request
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI Router (api/routers/portfolio.py)                │
│  GET /api/portfolio/holdings                              │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│  PortfolioService (api/services/portfolio_service.py)     │
│                                                          │
│  1. DB Read ─── SQLite (holdings table)                  │
│     ~1-5 ms   static data: ticker, qty, avg_price,      │
│               sector, industry, country, exchange        │
│                                                          │
│  2. Price Enrichment ─── ThreadPoolExecutor(2) parallel  │
│     ├── _get_current_prices()                            │
│     │   TTLCache(60s) → OHLCVCache(parquet) → yfinance  │
│     │   ~0ms (cached) / ~2-8s (cold)                    │
│     └── _get_daily_changes()                             │
│         TTLCache(60s) → OHLCVCache(parquet)              │
│         ~0ms (cached) / ~2-8s (cold)                    │
│                                                          │
│  3. P&L Calculation ─── in-memory, instant               │
└──────────────────────────────────────────────────────────┘
```

## Data Classification

| Field | Type | Source | Fetch Timing |
|-------|------|--------|-------------|
| ticker, name, quantity, avg_price | **Static** | SQLite DB | Page load (DB read) |
| sector, industry, country, exchange | **Static** | SQLite DB | Stored once at holding creation |
| current_price | **Dynamic** | yfinance / pykrx | Every request (with caching) |
| change_pct | **Dynamic** | Computed from OHLCV | Every request (with caching) |
| market_value, pnl, pnl_pct | **Derived** | Computed in-memory | Every request |
| cost_basis | **Derived** | quantity * avg_price | Every request |

## Caching Layers

### Layer 1: TTLCache (In-Memory)

```
File: utils/ttl_cache.py
Type: Per-ticker in-memory OrderedDict with LRU eviction
Thread Safety: RLock + per-key locks for thundering-herd prevention
```

| Cache Instance | TTL | Max Size | Purpose |
|----------------|-----|----------|---------|
| `_price_cache` | 60s | 512 | Current prices |
| `_change_cache` | 60s | 512 | Daily change percentages |
| `_sector_cache` | 3600s | 512 | Sector names (legacy, still used by `_get_sectors()`) |

**Behavior**: On cache hit, returns immediately (~0ms). On miss, falls through to Layer 2.

### Layer 2: OHLCVCache (Disk Parquet)

```
File: utils/data_cache.py
Type: Per-ticker Parquet files on disk
Location: data/cache/ohlcv/{ticker}.parquet
Freshness: 18 hours (STALE_HOURS)
```

**Behavior**:
- Stores up to 730 days (2 years) of OHLCV data per ticker
- Fresh = latest data date >= latest trading date (weekends adjusted)
- On hit: reads Parquet file, extracts last close price (~5-20ms)
- On miss: fetches from external API, saves to Parquet, returns data
- Supports incremental updates (only fetches missing days)
- Metadata cache avoids repeated Parquet reads for latest date/close

### Layer 3: External APIs (Network)

| Market | Primary API | Fallback | Typical Latency |
|--------|------------|----------|-----------------|
| Korean (.KS, .KQ) | pykrx | yfinance | 1-5s per ticker |
| US / Other | yfinance | None | 1-3s per ticker |

**Batch optimization**: `get_latest_prices()` uses `yf.download()` for a single network call when multiple tickers are missing.

## Response Time Estimates

| Scenario | Expected Time | Bottleneck |
|----------|--------------|------------|
| All prices cached (warm) | **50-100ms** | DB read + JSON serialization |
| Partial cache (some tickers stale) | **2-5s** | yfinance batch download |
| Cold start (no cache at all) | **5-15s** | N parallel yfinance calls |
| DB-only (with_prices=false) | **5-20ms** | SQLite query only |

## Detailed Flow: `get_all_holdings()`

```python
# Step 1: Read all holdings from SQLite
db = SessionLocal()
rows = db.query(Holding).all()           # ~1-5ms
holdings_dicts = [_row_to_dict(r) for r in rows]
db.close()

# Step 2: Parallel enrichment (ThreadPoolExecutor, max_workers=2)
with ThreadPoolExecutor(2) as outer:
    f_prices  = outer.submit(_get_current_prices, tickers)   # Thread A
    f_changes = outer.submit(_get_daily_changes, tickers)    # Thread B
    # Both threads run concurrently
    prices  = f_prices.result(timeout=30)
    changes = f_changes.result(timeout=30)

# Step 3: Build response objects (in-memory, ~0ms)
for h in holdings_dicts:
    _holding_to_response(h, prices[ticker], sector=h["sector"], ...)
```

### Price Fetch Detail (`_get_current_prices`)

```
For each ticker:
  1. Check TTLCache (60s) ──── HIT? → return immediately
  2. Check OHLCVCache.get_latest_prices()
     a. Fresh parquet exists? → read close from metadata cache
     b. Not fresh? → add to batch-fetch list
  3. Batch: yf.download(missing_tickers, period="10d")
  4. Fallback: per-ticker ThreadPoolExecutor(max_workers=8)
```

## Database Schema

### `holdings` table

```sql
CREATE TABLE holdings (
    ticker     VARCHAR(20)  PRIMARY KEY,
    name       VARCHAR(100),
    quantity   INTEGER      NOT NULL,
    avg_price  FLOAT        NOT NULL,
    currency   VARCHAR(10)  DEFAULT 'KRW',
    note       TEXT,
    bought_at  DATE,
    -- Static metadata (persisted once at creation)
    sector     VARCHAR(128),
    industry   VARCHAR(128),
    country    VARCHAR(64),
    exchange   VARCHAR(32)
);
```

### `trades` table

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

## Static Metadata Flow

Static metadata (sector, industry, country, exchange) is fetched **once** when a holding is first created and stored permanently in the DB.

```
New Holding Created
    │
    ├── Korean Stock (.KS/.KQ)
    │   ├── sector ← SectorFetcher (pykrx → CSV fallback)
    │   ├── industry ← NULL (not available from pykrx)
    │   ├── country ← "South Korea" (inferred from suffix)
    │   └── exchange ← "KOSPI" or "KOSDAQ" (inferred from suffix)
    │
    └── US/Other Stock
        ├── sector ← yfinance Ticker.info["sector"]
        ├── industry ← yfinance Ticker.info["industry"]
        ├── country ← yfinance Ticker.info["country"]
        └── exchange ← yfinance Ticker.info["exchange"]
```

### Backfill (Server Startup)

On server startup, a daemon thread backfills metadata for existing holdings that have NULL columns:

```
api/main.py → lifespan() → threading.Thread(_backfill_metadata)
  │
  ├── KR stocks: batch SectorFetcher for KOSPI/KOSDAQ
  └── US stocks: parallel yfinance (ThreadPoolExecutor, max_workers=8)
```

This runs non-blocking and does not delay server startup.

## Exchange Rate Flow

Used only in `get_summary(base_currency=...)` for multi-currency portfolios.

```
ExchangeRateService (api/services/exchange_rate_service.py)
    │
    ├── In-memory cache (Dict + monotonic timestamp)
    │   TTL: 3600s (1 hour)
    │
    └── External: frankfurter.app/latest?from={base}&to=KRW,SGD,...
        Timeout: 8s
        Fallback: returns stale cached rates on failure
```

## WebSocket Realtime Feed

```
WS /api/portfolio/realtime/ws?tickers=AAPL,005930.KS
    │
    └── Every 10 seconds:
        1. get_all_holdings(with_prices=False)  → ticker list
        2. _get_current_prices(tickers)         → latest prices
        3. Send JSON: { "updates": [{ticker, current_price, currency}] }
```

## API Endpoints

| Method | Path | Service Method | External Calls |
|--------|------|---------------|----------------|
| GET | `/api/portfolio` | `get_all_holdings()` + `get_summary()` | prices + changes |
| GET | `/api/portfolio/holdings` | `get_all_holdings()` | prices + changes |
| GET | `/api/portfolio/holdings/{ticker}` | `get_holding()` | price + change |
| POST | `/api/portfolio/holdings` | `add_holding()` | price + metadata (new only) |
| PUT | `/api/portfolio/holdings/{ticker}` | `update_holding()` | price |
| POST | `/api/portfolio/holdings/{ticker}/add-purchase` | `add_purchase()` | price |
| DELETE | `/api/portfolio/holdings/{ticker}` | `remove_holding()` | None |
| GET | `/api/portfolio/summary` | `get_summary()` | prices + changes + FX |
| GET | `/api/portfolio/sell-signals` | `get_sell_signals()` | prices + changes |
| POST | `/api/portfolio/trades` | `record_sell()` | None |
| GET | `/api/portfolio/trades` | `get_trade_history()` | None |
| WS | `/api/portfolio/realtime/ws` | `_get_current_prices()` | prices (every 10s) |

## File Structure

```
api/
├── routers/portfolio.py           # HTTP endpoints + WebSocket
├── services/
│   ├── portfolio_service.py       # Core business logic, caching, enrichment
│   └── exchange_rate_service.py   # FX rates (frankfurter.app, 1h TTL)
├── models/portfolio.py            # SQLAlchemy ORM (Holding, Trade)
├── schemas/portfolio.py           # Pydantic request/response models
└── database.py                    # Engine, session, migrations

utils/
├── ttl_cache.py                   # In-memory TTL cache (generic)
└── data_cache.py                  # OHLCV disk cache (Parquet)
```

## Related

- [Strategy Builder](./STRATEGY_BUILDER_README.md) - Strategy execution that uses the same OHLCVCache
- [Market Calendar](./MARKET_CALENDAR_README.md) - Trading day calculations
