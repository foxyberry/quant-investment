# Directory Restructure Plan

**Date**: 2026-04-27  
**Status**: Completed.  
**Epic Issue**: TBD

---

## Background

As the project grew to support strategy building, portfolio management, broker integrations, and AI chat, the codebase accumulated structural debt. Key symptoms:

- `api/services/portfolio_service.py` is 80KB — execution, monitoring, risk, and notification all in one file
- Strategy logic is split across 9+ service files
- Data fetch logic lives in 12+ locations with no unified interface
- Kiwoom broker code exists in 3 separate locations
- `web/src/lib/api.ts` is 54KB — all API calls in a single file
- Backend Pydantic schemas and frontend TypeScript types are maintained manually in sync

The restructure is also a prerequisite for integrating external data sources (e.g. worldmonitor) cleanly.

---

## Goals

1. Each service file has a single, clear responsibility
2. Data fetching is consolidated under one interface
3. Duplicate modules (Kiwoom, notifiers) are merged
4. Frontend API calls are split by domain
5. Structure is ready to accept new data sources (worldmonitor, FRED, EIA)

## Non-Goals

- No changes to public API contracts (routes, request/response shapes)
- No database schema changes
- No UI layout changes
- Not a full DDD migration — pragmatic refactor only

---

## Phases

### Phase 1 — Service Layer Split (Internal, No API Change)

Split the three oversized service files into focused sub-services.  
All existing imports and route handlers are updated to point to the new locations.  
No router or schema changes.

#### 1-A: `portfolio_service.py` (80KB → 4 files)

| New File | Responsibility |
|---|---|
| `portfolio_core_service.py` | Holdings state, CRUD, summary queries |
| `portfolio_execution_service.py` | Order placement, position sizing, trade history |
| `portfolio_risk_service.py` | Risk rule evaluation, drawdown checks |
| `portfolio_alert_service.py` | Alert scanning, condition matching (absorb `portfolio_alert_scanner.py`) |

#### 1-B: `strategy_service.py` (52KB → 3 files)

| New File | Responsibility |
|---|---|
| `strategy_core_service.py` | Strategy CRUD, graph serialization, validation |
| `strategy_execution_service.py` | Run lifecycle, progress tracking, result storage |
| `strategy_analytics_service.py` | Comparison, leaderboard, backtest result queries (absorb `strategy_comparison_service.py`, `strategy_backtest_result_service.py`) |

#### 1-C: `macro_market_service.py` (55KB → 2 files)

| New File | Responsibility |
|---|---|
| `macro_service.py` | Macro indicators: GDP, CPI, yield curve, fear/greed |
| `market_data_service.py` | Exchange status, index prices, sector performance |

#### 1-D: `web/src/lib/api.ts` (54KB → 5 files)

| New File | Responsibility |
|---|---|
| `api/portfolioApi.ts` | Portfolio endpoints |
| `api/strategyApi.ts` | Strategy + backtest endpoints |
| `api/screeningApi.ts` | Screening endpoints |
| `api/analysisApi.ts` | Analysis + watchlist endpoints |
| `api/marketApi.ts` | Market + macro endpoints |
| `api/index.ts` | Re-exports (backward compat) |

---

### Phase 2 — Duplicate Removal

#### 2-A: Kiwoom Consolidation

Current state: `kiwoom/` (legacy root) + `brokers/kiwoom/` + `api/services/kiwoom_service.py`

Target:
- Delete `kiwoom/` root directory (legacy)
- Keep `brokers/kiwoom/` as the canonical broker implementation
- `api/services/kiwoom_service.py` stays as a thin API adapter only (no business logic)

#### 2-B: Notification System Consolidation

Current state: `portfolio/notifiers/` (Telegram, Slack, Console, Multi) + `api/services/notification_dispatcher.py`

Target:
- `portfolio/notifiers/` becomes the canonical channel implementations
- `notification_dispatcher.py` is the single entry point (already partially done)
- Remove any duplicate send logic from `portfolio/notifier.py`

#### 2-C: Data Fetcher Consolidation

Current state: `screener/us_fetcher.py`, `screener/kospi_fetcher.py`, `screener/sector_fetcher.py`, `data_enrichment/fundamental.py`, `data_enrichment/technical.py`, `utils/fetch.py`

Target: Create `data_sources/` package as the unified data layer:
```
data_sources/
├── __init__.py
├── base.py              # Abstract fetcher interface
├── market/
│   ├── us_market.py     # ← screener/us_fetcher.py
│   ├── kr_market.py     # ← screener/kospi_fetcher.py
│   └── sector.py        # ← screener/sector_fetcher.py
├── fundamental/
│   └── fundamental.py   # ← data_enrichment/fundamental.py
├── technical/
│   └── technical.py     # ← data_enrichment/technical.py
├── news/
│   └── aggregator.py    # ← news/ module
└── external/
    └── worldmonitor.py  # ← NEW: worldmonitor API client
```

#### 2-D: `discovery/` vs `screener/conditions/` Boundary

- `discovery/evaluators/` → merge into `screener/conditions/` (they do the same thing)
- `discovery/decision.py` → move to `screener/decision.py`
- `discovery/indicators.py` → move to `data_sources/technical/indicators.py`
- Delete `discovery/` once fully migrated

---

### Phase 3 — Frontend Feature Structure + worldmonitor Integration

#### 3-A: Frontend `components/` → `features/`

```
web/src/
├── features/               # Feature-first structure
│   ├── portfolio/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── api/
│   ├── strategy/
│   ├── screening/
│   ├── analysis/
│   ├── macro/              # Worldmonitor data lands here
│   └── dashboard/
└── shared/
    ├── components/ui/      # shadcn UI components (unchanged)
    ├── hooks/              # Global hooks
    └── lib/
```

#### 3-B: worldmonitor External Data Integration

Self-host worldmonitor via Docker, expose internal API.  
Connect from `data_sources/external/worldmonitor.py` to our FastAPI `macro_service.py`.

New endpoints:
- `GET /api/macro/global-brief` — AI-synthesized world brief
- `GET /api/macro/country-risk/{country}` — Country intelligence index
- `GET /api/macro/market-radar` — 92-exchange finance radar

#### 3-C: OpenAPI → TypeScript Auto-generation

Replace manual type sync between `api/schemas/` and `web/src/lib/types.ts`:
- FastAPI auto-generates OpenAPI spec at `/openapi.json`
- Add `npm run generate:types` script using `openapi-typescript`
- CI enforces: types must be regenerated if schemas change

---

## Issue List

| # | Phase | Title | Size |
|---|---|---|---|
| TBD | 1-A | Split portfolio_service.py into 4 focused services | L |
| TBD | 1-B | Split strategy_service.py into 3 focused services | M |
| TBD | 1-C | Split macro_market_service.py into 2 focused services | M |
| TBD | 1-D | Split web/src/lib/api.ts into domain API clients | M |
| TBD | 2-A | Consolidate Kiwoom code into brokers/kiwoom/ | S |
| TBD | 2-B | Consolidate notification system under notification_dispatcher.py | S |
| TBD | 2-C | Create data_sources/ unified data layer | L |
| TBD | 2-D | Merge discovery/ into screener/conditions/ | M |
| TBD | 3-A | Restructure web/src/components/ to features/ | L |
| TBD | 3-B | worldmonitor self-host + FastAPI integration | L |
| TBD | 3-C | OpenAPI → TypeScript auto-generation pipeline | M |

---

## Completion Criteria

- [x] All service files under 500 lines (#1386-#1394)
- [x] No duplicate business logic across modules (#1377)
- [x] `data_sources/` package has >80% of all data fetch logic (#1380)
- [x] `web/src/lib/api.ts` deleted (split into domain files) (#1376)
- [x] `kiwoom/` root directory deleted (#1383)
- [x] `discovery/` deleted (merged into screener) (#1383)
- [x] worldmonitor integration working in macro page (#1382)
- [x] TypeScript types auto-generated from OpenAPI spec (#1378)

---

## Risk & Rollback

- Each phase is a separate PR — rollback is per-phase
- No API contract changes in Phase 1 or 2 — zero frontend risk for backend-only changes
- Phase 3 frontend restructure: feature flags not needed (component moves only, no logic change)
- worldmonitor integration (3-B) is additive — existing macro page unaffected if disabled
