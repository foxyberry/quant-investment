# quant-investment

A full-stack quant investing workspace for screening, strategy design, backtesting, portfolio monitoring, watchlist tracking, and analysis.

Language: [한국어 README](README_KO.md)

## What Is This Project?

`quant-investment` combines:
- **FastAPI** backend for screening, strategy execution, portfolio, and watchlist APIs
- **Next.js 16 + React 19** web UI for daily quant workflows (EN/KO/ZH i18n)
- **Python** research/runtime modules for data, indicators, and backtests

Primary goal: move from idea to executable strategy with one connected toolchain.

## What You Can Do In The UI

| Area | Route | What You Can Do |
|---|---|---|
| Dashboard | `/[locale]` | Market/portfolio summary, recent sell signals, quick stats |
| Screening | `/[locale]/screening` | Build filters, run scans, inspect condition matches |
| Strategy Builder | `/[locale]/strategy` | Node-based strategy graph, save/load, deploy run, market badges |
| Portfolio | `/[locale]/portfolio` | Holdings, positions, sell rules, PnL treemap, order desk |
| Watchlist | `/[locale]/watchlist` | Track target stocks, set target prices, buy rules, quick-view popup |
| Analysis | `/[locale]/analysis` | Chart/indicator context, ticker-based analysis popup |
| Reports | `/[locale]/reports` | Generated analysis reports with target date tracking |
| Settings | `/[locale]/settings` | App preferences and configuration |

## Quick Start

### 1) Requirements

- Python 3.13+
- Node.js 20+
- npm 10+

### 2) Install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm --prefix web install
```

### 3) Run

API (default port `8001`):
```bash
source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

Web (default port `3001`):
```bash
cd web && npm run dev -- -p 3001
```

> Port numbers can be changed freely. Update `NEXT_PUBLIC_API_URL` in `web/.env.local` to match your API port.

### 4) Open

- Web UI: `http://localhost:3001`
- API Docs (Swagger): `http://localhost:8001/docs`

## Shared DB via Docker (Location/Port Independent)

Use this when you want one persistent local DB regardless of where you run API/web.

### 1) Configure env

```bash
cp .env.example .env
```

Set these in `.env`:
- `DB_PORT` (default `5432`, change if conflict)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `DATABASE_URL=postgresql://<DB_USER>:<DB_PASSWORD>@localhost:<DB_PORT>/<DB_NAME>`

### 2) Start DB only

```bash
docker compose up -d db
docker compose ps db
```

The DB data is persisted in named volume `quant-investment-pgdata`.

### 3) Initialize schema

```bash
source venv/bin/activate
python -c "from api.database import init_db; init_db()"
```

### 4) Port conflict policy

If `5432` is already in use, set `DB_PORT=55432` in `.env` and update `DATABASE_URL` accordingly, then restart:

```bash
docker compose up -d db
```

## Core Workflows

### Workflow A: Build And Execute A Strategy

1. Open Strategy Builder (`/strategy`)
2. Add universe + condition nodes, connect edges
3. Configure condition parameters
4. Click deploy/run
5. Inspect matched symbols with KOSPI/KOSDAQ market badges and intermediate results

### Workflow B: Strategy To Backtest

1. Save or load a strategy in Strategy Builder
2. Open backtest panel
3. Select period and strategy inputs
4. Run backtest and inspect equity/trade metrics

### Workflow C: Screening To Analysis

1. Run screening on `/screening`
2. Click ticker to open analysis popup (quick-view)
3. Review technical/fundamental/AI context
4. Save findings into report workflow

### Workflow D: Portfolio Monitoring

1. Add holdings via portfolio page (search by stock name)
2. Configure per-holding sell rules (stop-loss, take-profit, trailing stop, holding period)
3. Monitor PnL, treemap, and sell signal banners
4. Click ticker for analysis popup

### Workflow E: Watchlist Tracking

1. Add stocks to watchlist (search by name, auto-fill target price)
2. Track current price vs. target price
3. Set buy rules per watchlist item
4. Click ticker for analysis popup

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy, SQLite |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| i18n | next-intl (EN / KO / ZH) |
| Data | yfinance (US), pykrx (KR), Finnhub, Marketaux |
| Research | pandas, numpy, Backtesting.py |

## Configuration

### Key Config Files

- `config/base_config.yaml`: global runtime/data/logging config
- `config/screening_criteria.yaml`: screening defaults
- `portfolio/`: portfolio logic and sizing modules

### Environment Variables

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Frontend API base URL (e.g. `http://localhost:8001`) |
| `ANTHROPIC_API_KEY` | AI analysis integration |
| `FINNHUB_API_KEY` | Optional news/data source |
| `MARKETAUX_API_KEY` | Optional news/data source |

## API Endpoints

| Group | Prefix | Description |
|---|---|---|
| Portfolio | `/api/portfolio` | Holdings CRUD, sell rules, sell signals, trades |
| Watchlist | `/api/watchlist` | Watchlist items, buy rules |
| Strategy | `/api/strategy` | Execute, save/load, SSE streaming |
| Screening | `/api/screening` | Run conditions, universes |
| Search | `/api/search`, `/api/price` | Ticker search (name), current price |
| Analysis | `/api/analysis` | Stock analysis and AI insights |
| Reports | `/api/reports` | Analysis report management |
| Market | `/api/market` | Market calendar, exchange rates |
| Backtest | `/api/backtest` | Backtest execution |

Full interactive docs: `http://localhost:8001/docs`

## Development

### Backend

```bash
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd web
npm run dev -- -p 3001
```

### Useful Checks

```bash
npm --prefix web run lint
npm --prefix web run check:condition-i18n
npm --prefix web run check:strategy-i18n
```

## Troubleshooting

- **Web cannot call API**: Check API port and `NEXT_PUBLIC_API_URL` in `web/.env.local`
- **i18n key errors** (`MISSING_MESSAGE`): Run `npm --prefix web run check:strategy-i18n` / `check:condition-i18n`
- **Strategy run returns empty results**: Confirm universe/condition thresholds are not overly strict
- **Korean stock names not showing**: Ensure pykrx is installed and KRX master CSVs are up to date

## Roadmap / Limitations

- Broker integrations (Kiwoom/IBKR) in progress
- Background sell rule monitoring (Phase 2 — currently on-demand only)
- Advanced quant conditions expanding incrementally
- Multi-market workflow evolving by issue-based increments

## Language Switch

- English: `README.md`
- Korean: [`README_KO.md`](README_KO.md)
