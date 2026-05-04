# Development Guide

Complete guide for setting up and developing the quant-investment platform.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Project Structure](#project-structure)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [Adding New Features](#adding-new-features)
- [Docker Development](#docker-development)
- [Code Style](#code-style)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.13+ | Backend API and analysis |
| Node.js | 20+ | Web frontend |
| Git | Latest | Version control |

### Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 24+ | Containerized deployment |
| Docker Compose | 2.0+ | Multi-container orchestration |

### Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8002
WEB_PORT=3002
DEBUG=true

# AI Analysis (optional)
ANTHROPIC_API_KEY=your-api-key-here

# News APIs (optional)
FINNHUB_API_KEY=your-finnhub-key
MARKETAUX_API_KEY=your-marketaux-key
```

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/quant-investment.git
cd quant-investment
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 3. Set Up Web Frontend

```bash
cd web

# Install Node.js dependencies
npm install

# Create local environment file
cp .env.example .env.local

# Return to project root
cd ..
```

### 4. Verify Setup

```bash
# Test Python environment
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"

# Test Node.js environment
node -v
npm -v

# Run health check
./scripts/run_api.sh &
sleep 3
curl http://localhost:8002/health
```

---

## Project Structure

```
quant-investment/
├── api/                      # FastAPI backend
│   ├── __init__.py
│   ├── main.py               # Application entry point
│   ├── config.py             # Configuration settings
│   ├── routers/              # API route handlers
│   ├── schemas/              # Pydantic models
│   └── services/             # Business logic
│       ├── portfolio/        # Portfolio sub-services
│       ├── strategy/         # Strategy sub-services
│       ├── market_service.py
│       ├── macro_service.py
│       ├── notification_dispatcher.py
│       └── screening_service.py
│
├── web/                      # Next.js frontend
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── features/        # Feature-first UI modules
│   │   ├── components/ui/   # Shared UI primitives
│   │   └── lib/api/         # Generated + handwritten API clients
│   ├── package.json
│   └── Dockerfile
│
├── screener/                # Screening runtime library
│   ├── conditions/          # Screening conditions
│   └── stock_screener.py    # Main screener class
│
├── data_sources/            # Unified data fetch layer
├── portfolio/               # Portfolio/domain logic
├── engine/                  # Backtesting engine
├── llm/                     # AI integration
├── data_enrichment/         # Derived metrics and enrichment
│
├── scripts/                  # Utility scripts
│   ├── dev.sh               # Start all services
│   ├── run_api.sh           # Start API only
│   └── run_web.sh           # Start web only
│
├── config/                   # Configuration files
├── data/                     # Data storage
├── logs/                     # Log files
├── docs/                     # Documentation
│
├── docker-compose.yml        # Docker Compose config
├── Dockerfile.api           # API Docker image
├── requirements.txt         # Python dependencies
└── requirements-dev.txt     # Dev dependencies
```

---

## Running the Application

### Development Mode (Recommended)

Start both API and Web servers with hot reload:

```bash
# Start all services
./scripts/dev.sh
```

This will start:
- **API**: http://localhost:8002
- **API Docs**: http://localhost:8002/docs
- **Web**: http://localhost:3002

Press `Ctrl+C` to stop all servers.

### Individual Services

```bash
# API only
./scripts/run_api.sh

# Web only (requires API running)
./scripts/run_web.sh
```

### Production Mode

```bash
# Using Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Running Tests

### API Tests (Python)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test file
pytest api/tests/test_screening.py

# Run with verbose output
pytest -v
```

### Web Tests (JavaScript)

```bash
cd web

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

### Integration Tests

```bash
# Start services first
./scripts/dev.sh &

# Run integration tests
pytest tests/integration/

# Or use httpx for manual testing
python -c "
import httpx
r = httpx.get('http://localhost:8002/health')
print(r.json())
"
```

---

## Adding New Features

### Adding a New API Endpoint

1. **Create/Update Schema** (`api/schemas/`)

```python
# api/schemas/my_feature.py
from pydantic import BaseModel, Field

class MyRequest(BaseModel):
    """Request schema for my feature."""
    param1: str = Field(..., description="First parameter")

class MyResponse(BaseModel):
    """Response schema for my feature."""
    result: str = Field(..., description="Result data")
```

2. **Create/Update Service** (`api/services/`)

```python
# api/services/my_feature_service.py
class MyFeatureService:
    def process(self, param1: str) -> dict:
        """Business logic here."""
        return {"result": f"Processed: {param1}"}

def get_my_feature_service() -> MyFeatureService:
    return MyFeatureService()
```

3. **Create/Update Router** (`api/routers/`)

```python
# api/routers/my_feature.py
from fastapi import APIRouter
from api.schemas.my_feature import MyRequest, MyResponse
from api.services.my_feature_service import get_my_feature_service

router = APIRouter(prefix="/api/my-feature", tags=["My Feature"])

@router.post("", response_model=MyResponse)
async def process_feature(request: MyRequest) -> MyResponse:
    """Process my feature."""
    service = get_my_feature_service()
    result = service.process(request.param1)
    return MyResponse(**result)
```

4. **Register Router** (`api/main.py`)

```python
from api.routers.my_feature import router as my_feature_router

# In create_app():
app.include_router(my_feature_router)
```

5. **Add Tests**

```python
# api/tests/test_my_feature.py
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_process_feature():
    response = client.post("/api/my-feature", json={"param1": "test"})
    assert response.status_code == 200
    assert response.json()["result"] == "Processed: test"
```

### Adding a New Frontend Page

1. **Create Page** (`web/src/app/`)

```tsx
// web/src/app/[locale]/my-page/page.tsx
export default function MyPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">My Page</h1>
      {/* Page content */}
    </div>
  );
}
```

2. **Create Feature Components** (`web/src/features/`)

```tsx
// web/src/features/my-page/components/MyComponent.tsx
interface MyComponentProps {
  title: string;
}

export function MyComponent({ title }: MyComponentProps) {
  return <div className="card">{title}</div>;
}
```

3. **Add API Types / Client** (`web/src/lib/api/`)

```typescript
export interface MyFeatureRequest {
  param1: string;
}

export interface MyFeatureResponse {
  result: string;
}
```

4. **Add API Function** (`web/src/lib/api/myFeatureApi.ts`)

```typescript
export async function processMyFeature(
  request: MyFeatureRequest
): Promise<MyFeatureResponse> {
  const response = await fetch(`${API_BASE_URL}/api/my-feature`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return response.json();
}
```

5. **Add Navigation** (`web/src/features/layout/Sidebar.tsx`)

Add link to the new page in the sidebar navigation.

---

## Docker Development

### Build Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build api
docker-compose build web
```

### Development with Docker

```bash
# Start with live reload (mount source code)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Rebuild and start
docker-compose up --build

# View logs for specific service
docker-compose logs -f api
docker-compose logs -f web
```

### Useful Docker Commands

```bash
# List running containers
docker-compose ps

# Execute command in container
docker-compose exec api bash
docker-compose exec web sh

# Remove all containers and volumes
docker-compose down -v

# Prune unused images
docker image prune -a
```

---

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints for function arguments and return values
- Write docstrings for all public functions and classes
- Maximum line length: 88 characters (Black formatter)

```bash
# Format code
black api/

# Sort imports
isort api/

# Lint code
flake8 api/

# Type check
mypy api/
```

### TypeScript/JavaScript

- Use TypeScript for all new code
- Follow ESLint configuration
- Use functional components with hooks

```bash
cd web

# Lint code
npm run lint

# Format code (if prettier is configured)
npm run format
```

### Git Commit Messages

Follow conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(api): add portfolio sell signals endpoint
fix(web): correct P&L calculation display
docs: update API reference with new endpoints
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port 8002
lsof -i :8002
# Kill the process
kill -9 <PID>

# Or use different ports
API_PORT=8010 WEB_PORT=3010 ./scripts/dev.sh
```

#### Module Not Found

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### CORS Errors in Browser

The API is configured to allow requests from explicit local dev origins, including `localhost:3002`. If using a different port:

1. Update `api/config.py`:
```python
cors_origins: list[str] = ["http://localhost:3002", "http://localhost:YOUR_PORT"]
```

2. Or set environment variable:
```bash
CORS_ORIGINS=http://localhost:3002,http://localhost:YOUR_PORT
```

#### Next.js Build Errors

```bash
cd web

# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules
npm install

# Rebuild
npm run build
```

#### Docker Container Fails to Start

```bash
# Check logs
docker-compose logs api

# Common fixes:
# 1. Rebuild image
docker-compose build --no-cache api

# 2. Check environment variables
docker-compose config

# 3. Verify Dockerfile syntax
docker build -f Dockerfile.api .
```

### Getting Help

1. Check existing documentation in `docs/`
2. Review error logs in `logs/quant_investment.log`
3. Search existing issues on GitHub
4. Create a new issue with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs
   - Environment details (OS, Python version, etc.)
