# UI Integration Project: FastAPI + Next.js Web Dashboard

- **Date**: 2026-02-12
- **Branch**: `feature/ui-integration`
- **Status**: In Progress (Phase 1 & 2 Complete, Phase 3 Partial)

## Goal

Expose the existing quant-investment backend as a REST API and build a Next.js-based web dashboard for browser-based stock screening, portfolio management, and analysis result viewing.

## Background

- Currently CLI-based only
- Requires terminal script execution each time
- No visual charts or dashboards
- No mobile/remote access

---

# Phase 1: FastAPI Backend - COMPLETE

## Epic 1.1: Project Structure Setup

### Task 1.1.1: FastAPI Basic Structure - COMPLETE (2026-02-12)
- [x] Create `api/` folder
- [x] Create `api/__init__.py`
- [x] Create `api/main.py` (FastAPI app instance)
- [x] Create `api/config.py` (environment variables, settings)
- [x] Create `api/dependencies.py` (common dependencies)

**Changed Files:**
| File | Changes |
|------|---------|
| `api/__init__.py` | Created |
| `api/main.py` | FastAPI app initialization, CORS settings |
| `api/config.py` | Settings class (pydantic-settings) |
| `api/dependencies.py` | Common dependency injection |

### Task 1.1.2: Router Structure - COMPLETE (2026-02-12)
- [x] Create `api/routers/` folder
- [x] Create `api/routers/__init__.py`
- [x] Create `api/routers/health.py` (health check)

**Changed Files:**
| File | Changes |
|------|---------|
| `api/routers/__init__.py` | Router exports |
| `api/routers/health.py` | GET /health endpoint |

### Task 1.1.3: Schema Structure - COMPLETE (2026-02-12)
- [x] Create `api/schemas/` folder
- [x] Create `api/schemas/__init__.py`
- [x] Create `api/schemas/common.py` (common response schemas)

**Changed Files:**
| File | Changes |
|------|---------|
| `api/schemas/__init__.py` | Schema exports |
| `api/schemas/common.py` | ApiResponse, PaginatedResponse |

### Task 1.1.4: Dependencies Added - COMPLETE (2026-02-12)
- [x] Add FastAPI packages to `requirements.txt`
- [x] Create `requirements-dev.txt` (testing, linting, type checking)

**Added Packages:**
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-multipart>=0.0.6
```

### Task 1.1.5: Development Server Scripts - COMPLETE (2026-02-12)
- [x] Create `scripts/run_api.sh`
- [x] Create `scripts/run_web.sh`
- [x] Create `scripts/dev.sh` (run API + Web simultaneously)

---

## Epic 1.2: Screening API - COMPLETE

### Task 1.2.1: Screening Schema Definition - COMPLETE (2026-02-12)
- [x] Create `api/schemas/screening.py`
- [x] ScreeningRequest schema
- [x] ScreeningResult schema
- [x] ConditionResult schema
- [x] PresetInfo schema

### Task 1.2.2: Screening Router Implementation - COMPLETE (2026-02-12)
- [x] Create `api/routers/screening.py`
- [x] GET `/api/screening/presets` - Preset list (14 presets)
- [x] GET `/api/screening/universes` - Universe list (4 universes)
- [x] POST `/api/screening/run` - Run screening
- [x] GET `/api/screening/stock/{ticker}` - Check single stock

### Task 1.2.3: Screening Service Layer - COMPLETE (2026-02-12)
- [x] Create `api/services/` folder
- [x] Create `api/services/screening_service.py`
- [x] Integration with existing `screener` module

---

## Epic 1.3: Portfolio API - COMPLETE

### Task 1.3.1: Portfolio Schema Definition - COMPLETE (2026-02-12)
- [x] Create `api/schemas/portfolio.py`
- [x] HoldingCreate, HoldingUpdate schemas
- [x] HoldingResponse schema
- [x] PortfolioSummary schema
- [x] SellSignalResponse schema

### Task 1.3.2: Portfolio Router Implementation - COMPLETE (2026-02-12)
- [x] Create `api/routers/portfolio.py`
- [x] GET `/api/portfolio` - Full portfolio
- [x] POST `/api/portfolio/holdings` - Add stock
- [x] PUT `/api/portfolio/holdings/{ticker}` - Update stock
- [x] DELETE `/api/portfolio/holdings/{ticker}` - Delete stock
- [x] GET `/api/portfolio/summary` - P&L summary
- [x] GET `/api/portfolio/sell-signals` - Sell signals

### Task 1.3.3: Portfolio Service Layer - COMPLETE (2026-02-12)
- [x] Create `api/services/portfolio_service.py`
- [x] JSON file-based storage (`data/portfolio.json`)
- [x] OHLCVCache integration (current price lookup)

---

## Epic 1.4: Analysis API - COMPLETE

### Task 1.4.1: Analysis Schema Definition - COMPLETE (2026-02-12)
- [x] Create `api/schemas/analysis.py`
- [x] EnrichRequest, EnrichedStock schemas
- [x] AnalysisResult schema
- [x] ReportSummary, ReportDetail schemas

### Task 1.4.2: Analysis Router Implementation - COMPLETE (2026-02-12)
- [x] Create `api/routers/analysis.py`
- [x] POST `/api/analysis/enrich` - Data enrichment
- [x] POST `/api/analysis/analyze` - AI analysis (Claude)
- [x] GET `/api/analysis/reports` - Report list
- [x] GET `/api/analysis/reports/{date}` - Report detail
- [x] GET `/api/analysis/enriched/{date}` - Enriched JSON

### Task 1.4.3: Analysis Service Layer - COMPLETE (2026-02-12)
- [x] Create `api/services/analysis_service.py`
- [x] Integration with existing `data_enrichment`, `llm` modules
- [x] data/analysis/ folder report retrieval

---

## Epic 1.5: Market Data API - COMPLETE

### Task 1.5.1: Market Schema Definition - COMPLETE (2026-02-12)
- [x] Create `api/schemas/market.py`
- [x] OHLCVData schema
- [x] QuoteResponse schema
- [x] TechnicalIndicators schema

### Task 1.5.2: Market Router Implementation - COMPLETE (2026-02-12)
- [x] Create `api/routers/market.py`
- [x] GET `/api/market/quote/{ticker}` - Current price
- [x] GET `/api/market/ohlcv/{ticker}` - OHLCV data
- [x] GET `/api/market/technical/{ticker}` - Technical indicators

### Task 1.5.3: Cache Service Integration - COMPLETE (2026-02-12)
- [x] Create `api/services/market_service.py`
- [x] Utilize existing `OHLCVCache`
- [x] TechnicalEnricher integration

---

# Phase 2: Next.js Frontend - MOSTLY COMPLETE

## Epic 2.1: Initial Project Setup

### Task 2.1.1: Next.js Project Creation - COMPLETE (2026-02-12)
- [x] Create Next.js 16 (App Router) project in `web/` folder
- [x] TypeScript configuration
- [x] ESLint configuration
- [x] Tailwind CSS configuration

### Task 2.1.2: Basic Layout Configuration - COMPLETE (2026-02-12)
- [x] `web/src/app/layout.tsx` - Root layout
- [x] `web/src/components/layout/Header.tsx` - Header (mobile hamburger)
- [x] `web/src/components/layout/Sidebar.tsx` - Sidebar (collapsible)
- [x] `web/src/components/layout/Footer.tsx` - Footer
- [x] `web/src/components/ui/Button.tsx` - Button component
- [x] `web/src/components/ui/Card.tsx` - Card component

### Task 2.1.3: API Client Setup - COMPLETE (2026-02-12)
- [x] `web/src/lib/api.ts` - Fetch wrapper
- [x] `web/src/lib/types.ts` - API type definitions
- [x] Environment variable setup (`.env.local`)

### Task 2.1.4: State Management Setup - PENDING
- [ ] Install Zustand or React Query
- [ ] `web/src/stores/` folder structure
- [ ] `web/src/hooks/` custom hooks

---

## Epic 2.2: Dashboard Page - COMPLETE

### Task 2.2.1: Dashboard Layout - COMPLETE (2026-02-12)
- [x] `web/src/app/page.tsx` - Main dashboard (2x2 grid)
- [x] Portfolio summary card
- [x] Sell signals card
- [x] Recent analysis reports card
- [x] Quick actions card

### Task 2.2.2: Portfolio Summary Component - COMPLETE (2026-02-12)
- [x] `web/src/components/dashboard/PortfolioSummaryCard.tsx`
- [x] Total assets, returns, P&L display
- [x] Profit/loss color coding

### Task 2.2.3: Other Dashboard Components - COMPLETE (2026-02-12)
- [x] `web/src/components/dashboard/SellSignalsCard.tsx`
- [x] `web/src/components/dashboard/RecentReportsCard.tsx`
- [x] `web/src/components/dashboard/QuickActionsCard.tsx`

---

## Epic 2.3: Screening Page - COMPLETE

### Task 2.3.1: Screening Page Layout - COMPLETE (2026-02-12)
- [x] `web/src/app/screening/page.tsx`
- [x] Preset selection UI
- [x] Universe selection
- [x] Run button + loading state

### Task 2.3.2: Screening Results Table - COMPLETE (2026-02-12)
- [x] `web/src/components/screening/ResultTable.tsx`
- [x] Sorting (ticker, name, price)
- [x] Expandable rows (condition details)
- [x] Mobile responsive (card layout)

### Task 2.3.3: Screening Filter Component - COMPLETE (2026-02-12)
- [x] `web/src/components/screening/FilterPanel.tsx`
- [x] Preset dropdown (loaded from API)
- [x] Universe selection
- [x] `web/src/components/screening/ConditionDetails.tsx` - Condition details

---

## Epic 2.4: Portfolio Page - COMPLETE

### Task 2.4.1: Portfolio Page Layout - COMPLETE (2026-02-12)
- [x] `web/src/app/portfolio/page.tsx`
- [x] Holdings table
- [x] Summary card (investment, value, P&L)

### Task 2.4.2: Holdings Table - COMPLETE (2026-02-12)
- [x] `web/src/components/portfolio/HoldingsTable.tsx`
- [x] Sorting, profit/loss colors
- [x] Edit/Delete buttons
- [x] Responsive (mobile cards)

### Task 2.4.3: Add/Edit Holding Modals - COMPLETE (2026-02-12)
- [x] `web/src/components/portfolio/AddHoldingModal.tsx`
- [x] `web/src/components/portfolio/EditHoldingModal.tsx`
- [x] `web/src/components/portfolio/DeleteConfirmModal.tsx`
- [x] Validation

### Task 2.4.4: Sell Signal Banner - COMPLETE (2026-02-12)
- [x] `web/src/components/portfolio/SellSignalBanner.tsx`
- [x] Display stocks meeting sell conditions
- [x] Dismissible

---

## Epic 2.5: Chart and Analysis Pages - PENDING

### Task 2.5.1: Stock Detail Page
- [ ] `web/src/app/stock/[ticker]/page.tsx`
- [ ] Candlestick chart (TradingView Lightweight Charts)
- [ ] Technical indicator overlays
- [ ] Financial data display

### Task 2.5.2: Candlestick Chart Component
- [ ] `web/src/components/chart/CandleChart.tsx`
- [ ] TradingView Lightweight Charts integration
- [ ] Moving average, Bollinger Bands overlays
- [ ] Volume bar chart

### Task 2.5.3: Technical Indicator Panel
- [ ] `web/src/components/chart/IndicatorPanel.tsx`
- [ ] RSI, MACD, Stochastic display
- [ ] Signal interpretation text

### Task 2.5.4: Analysis Report Page
- [ ] `web/src/app/analysis/page.tsx`
- [ ] Daily report list
- [ ] Markdown rendering

---

# Phase 3: Integration and Deployment - PARTIAL

## Epic 3.1: Development Environment Integration

### Task 3.1.1: Docker Compose Setup - COMPLETE (2026-02-12)
- [x] Create `docker-compose.yml`
- [x] `Dockerfile.api` - FastAPI image
- [x] `web/Dockerfile` - Next.js image (multi-stage)
- [x] `.dockerignore` files

### Task 3.1.2: Development Scripts - COMPLETE (2026-02-12)
- [x] `scripts/dev.sh` - Full development server
- [x] Trap handler for graceful shutdown
- [x] `.env.example` environment variable examples

---

## Epic 3.2: Testing - PENDING

### Task 3.2.1: API Tests
- [ ] `api/tests/` folder structure
- [ ] pytest + httpx setup
- [ ] Tests for each endpoint

### Task 3.2.2: Frontend Tests
- [ ] Jest + React Testing Library setup
- [ ] Key component tests

---

## Epic 3.3: Documentation - COMPLETE (2026-02-12)

### Task 3.3.1: API Documentation - COMPLETE
- [x] FastAPI auto-generated Swagger
- [x] `docs/API_REFERENCE.md` - Complete API reference

### Task 3.3.2: Development Guide - COMPLETE
- [x] `docs/DEVELOPMENT_GUIDE.md` - Complete development guide
- [x] Local development setup instructions
- [x] Architecture explanation
- [x] README.md updated with Web UI section

---

# Work Priority and Schedule

## Recommended Order

| Order | Epic | Estimated Time | Status |
|-------|------|----------------|--------|
| 1 | 1.1 Project Structure Setup | 0.5 days | COMPLETE |
| 2 | 1.2 Screening API | 1 day | COMPLETE |
| 3 | 1.5 Market Data API | 0.5 days | COMPLETE |
| 4 | 2.1 Next.js Initial Setup | 0.5 days | COMPLETE |
| 5 | 2.3 Screening Page | 1 day | COMPLETE |
| 6 | 1.3 Portfolio API | 1 day | COMPLETE |
| 7 | 2.4 Portfolio Page | 1 day | COMPLETE |
| 8 | 2.5 Charts and Analysis | 1.5 days | PENDING |
| 9 | 1.4 Analysis API | 1 day | COMPLETE |
| 10 | 2.2 Dashboard | 1 day | COMPLETE |
| 11 | 3.x Integration and Deployment | 1 day | PARTIAL |

**Total Estimated**: 10 days
**Completed**: ~8 days
**Remaining**: ~2 days (Charts, Tests)

---

# Technical Considerations

## Notes

1. **CORS Configuration**: FastAPI allows Next.js dev server (localhost:3000)
2. **Environment Variable Management**: API keys (ANTHROPIC_API_KEY etc.) managed securely
3. **Cache Strategy**: OHLCV data uses existing Parquet cache
4. **Async Processing**: Screening and AI analysis can take time - polling or WebSocket for future

## Dependency Conflict Prevention

- Maintain Python virtual environment separation
- Node.js managed only within `web/` folder
- Shared data uses `data/` folder

---

# Results

## Completed Items (2026-02-12)

### Backend (FastAPI)
- Full REST API with 5 routers (health, screening, market, portfolio, analysis)
- 20+ endpoints implemented
- Pydantic schemas for all request/response validation
- Service layer with business logic separation
- Integration with existing modules (screener, data_enrichment, llm)

### Frontend (Next.js)
- Dashboard with 4 summary cards
- Screening page with preset/universe selection and results table
- Portfolio page with CRUD operations and P&L calculations
- Responsive design with mobile support
- API client with type definitions

### Infrastructure
- Docker Compose configuration for multi-service deployment
- Development scripts (dev.sh, run_api.sh, run_web.sh)
- Graceful shutdown handling

### Documentation
- Complete API Reference (docs/API_REFERENCE.md)
- Development Guide (docs/DEVELOPMENT_GUIDE.md)
- Updated README with Web UI section

## Pending Items
- Stock detail page with charts (TradingView Lightweight Charts)
- Analysis report page with Markdown rendering
- State management (Zustand/React Query)
- API and frontend tests
