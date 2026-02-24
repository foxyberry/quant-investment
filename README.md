# quant-investment

A full-stack quant investing workspace for screening, strategy design, backtesting, portfolio monitoring, and analysis.

Language: [한국어 README](README_KO.md)

## What Is This Project?

`quant-investment` combines:
- FastAPI backend for screening, strategy execution, and portfolio APIs
- Next.js web UI for daily quant workflows
- Python research/runtime modules for data, indicators, and backtests

Primary goal: move from idea to executable strategy with one connected toolchain.

## What You Can Do In The UI

| Area | Route | What You Can Do |
|---|---|---|
| Dashboard | `/[locale]` | Check market/portfolio summary and recent activity |
| Screening | `/[locale]/screening` | Build filters, run scans, inspect condition matches |
| Strategy Builder | `/[locale]/strategy` | Compose node-based strategy graph, save/load strategy, deploy run |
| Backtest | Strategy page panel | Backtest selected strategy parameters and review results |
| Portfolio | `/[locale]/portfolio` | Track holdings, positions, and order desk actions |
| Analysis & Reports | `/[locale]/analysis`, `/[locale]/reports` | Review chart/indicator context and generated analysis reports |

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

### 3) Run (Recommended Dev Ports)

API (port `8002`):
```bash
source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload
```

Web (port `3002`):
```bash
cd web && PORT=3002 npm run dev
```

### 4) Open

- Web UI: `http://localhost:3002`
- API Docs: `http://localhost:8002/docs`

## Core Workflows

### Workflow A: Build And Execute A Strategy

1. Open Strategy Builder (`/[locale]/strategy`)
2. Add universe + condition nodes
3. Configure condition parameters
4. Click deploy/run
5. Inspect matched symbols and intermediate results

### Workflow B: Strategy To Backtest

1. Save or load a strategy in Strategy Builder
2. Open backtest panel
3. Select period and strategy inputs
4. Run backtest and inspect equity/trade metrics

### Workflow C: Screening To Analysis

1. Run screening on `/[locale]/screening`
2. Open symbol analysis page
3. Review technical/fundamental/AI context
4. Save findings into report workflow

## Configuration

### Key Config Files

- `config/base_config.yaml`: global runtime/data/logging config
- `config/screening_criteria.yaml`: screening defaults
- `portfolio/`: portfolio logic and sizing modules

### Environment Variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | AI analysis integration |
| `FINNHUB_API_KEY` | Optional news/data source |
| `MARKETAUX_API_KEY` | Optional news/data source |

## API/Web Development

### Backend

```bash
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload
```

### Frontend

```bash
cd web
PORT=3002 npm run dev
```

### Useful Checks

```bash
npm --prefix web run lint
npm --prefix web run check:condition-i18n
npm --prefix web run check:strategy-i18n
```

## Troubleshooting

- Web cannot call API:
  - Check API is running on the expected port
  - Check frontend API base URL/env for your local setup
- i18n key errors (`MISSING_MESSAGE`):
  - Run `npm --prefix web run check:strategy-i18n`
  - Run `npm --prefix web run check:condition-i18n`
- Strategy run returns empty results:
  - Confirm universe/condition thresholds are not overly strict

## Roadmap / Limitations

- Broker integrations are in progress (Kiwoom/IBKR related issues)
- Some advanced quant conditions are still being expanded
- Multi-market workflow is evolving by issue-based increments

## Language Switch (EN/KO)

- English (primary): `README.md`
- Korean: `README_KO.md`
