# API Reference

REST API documentation for the quant-investment platform.

**Base URL**: `http://localhost:8000`

**Interactive Documentation**:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Table of Contents

- [Overview](#overview)
- [Error Responses](#error-responses)
- [Endpoints](#endpoints)
  - [Health](#health)
  - [Screening](#screening)
  - [Market Data](#market-data)
  - [Portfolio](#portfolio)
  - [Analysis](#analysis)
- [Authentication](#authentication)

---

## Overview

The API follows RESTful conventions and returns JSON responses. All endpoints are prefixed with `/api/` except for health checks.

### Response Format

Successful responses return the data directly. Error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource does not exist |
| 500 | Internal Server Error |
| 503 | Service Unavailable (e.g., Claude API not configured) |

---

## Error Responses

All errors return a JSON object with a `detail` field:

```json
{
  "detail": "Holding not found: INVALID_TICKER"
}
```

For validation errors (400), the detail may include field-specific information:

```json
{
  "detail": [
    {
      "loc": ["body", "quantity"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

---

## Endpoints

### Health

Health check endpoints for monitoring and load balancers.

#### GET /health

Check API server health status.

**Response**: `200 OK`

```json
{
  "status": "healthy",
  "timestamp": "2026-02-12T10:30:00Z",
  "version": "0.1.0"
}
```

---

### Screening

Stock screening endpoints for finding investment opportunities.

#### GET /api/screening/presets

Get list of available screening presets.

**Response**: `200 OK`

```json
[
  {
    "name": "accumulation_basic",
    "description": "Basic accumulation zone detection",
    "conditions": ["LowVolatilityCondition", "VolumeContractionCondition"]
  },
  {
    "name": "accumulation_obv",
    "description": "Accumulation with OBV divergence",
    "conditions": ["LowVolatilityCondition", "VolumeContractionCondition", "OBVDivergenceCondition"]
  }
]
```

#### GET /api/screening/universes

Get list of available stock universes.

**Response**: `200 OK`

```json
[
  {
    "name": "KOSPI",
    "description": "Korea Stock Price Index",
    "stock_count": 940
  },
  {
    "name": "KOSDAQ",
    "description": "Korea Securities Dealers Automated Quotations",
    "stock_count": 1600
  },
  {
    "name": "SP500",
    "description": "S&P 500 Index",
    "stock_count": 503
  }
]
```

#### POST /api/screening/run

Run stock screening with specified preset and universe.

**Request Body**:

```json
{
  "preset": "accumulation_basic",
  "universe": "KOSPI",
  "params": {
    "min_price": 10000
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| preset | string | No | "accumulation_basic" | Preset name |
| universe | string | No | "KOSPI" | Stock universe |
| params | object | No | null | Override preset parameters |

**Response**: `200 OK`

```json
{
  "results": [
    {
      "ticker": "005930.KS",
      "name": "Samsung Electronics",
      "current_price": 71500,
      "matched": true,
      "conditions": [
        {
          "condition_name": "LowVolatilityCondition",
          "matched": true,
          "details": {
            "volatility": 0.015,
            "threshold": 0.02
          }
        }
      ]
    }
  ],
  "total_count": 940,
  "matched_count": 12
}
```

**Note**: This operation may take several minutes for large universes.

#### GET /api/screening/stock/{ticker}

Check a single stock against screening conditions.

**Path Parameters**:
- `ticker` (string, required): Stock ticker symbol (e.g., "AAPL", "005930.KS")

**Query Parameters**:
- `preset` (string, optional): Preset name (default: "accumulation_basic")

**Response**: `200 OK`

```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "current_price": 185.50,
  "matched": true,
  "conditions": [
    {
      "condition_name": "LowVolatilityCondition",
      "matched": true,
      "details": {}
    }
  ]
}
```

#### POST /api/screening/stock/{ticker}

Check a single stock with custom parameters.

**Path Parameters**:
- `ticker` (string, required): Stock ticker symbol

**Request Body**:

```json
{
  "preset": "accumulation_obv",
  "params": {
    "volatility_threshold": 0.025
  }
}
```

---

### Market Data

Endpoints for retrieving market data, quotes, and technical indicators.

#### GET /api/market/quote/{ticker}

Get current price quote for a stock.

**Path Parameters**:
- `ticker` (string, required): Stock ticker symbol

**Response**: `200 OK`

```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "current_price": 185.50,
  "change": 2.30,
  "change_pct": 1.25,
  "volume": 45000000,
  "timestamp": "2026-02-12T16:00:00Z"
}
```

#### GET /api/market/ohlcv/{ticker}

Get historical OHLCV (Open-High-Low-Close-Volume) data.

**Path Parameters**:
- `ticker` (string, required): Stock ticker symbol

**Query Parameters**:
- `days` (integer, optional): Number of days (1-730, default: 100)

**Response**: `200 OK`

```json
{
  "ticker": "AAPL",
  "data": [
    {
      "date": "2026-02-12",
      "open": 183.20,
      "high": 186.00,
      "low": 182.50,
      "close": 185.50,
      "volume": 45000000
    }
  ],
  "period_days": 100
}
```

#### GET /api/market/technical/{ticker}

Get technical indicators for a stock.

**Path Parameters**:
- `ticker` (string, required): Stock ticker symbol

**Response**: `200 OK`

```json
{
  "ticker": "AAPL",
  "rsi": 55.2,
  "rsi_signal": "neutral",
  "macd": 1.25,
  "macd_signal": 0.98,
  "macd_histogram": 0.27,
  "bb_upper": 190.50,
  "bb_middle": 183.00,
  "bb_lower": 175.50,
  "bb_position": "middle",
  "ma_20": 182.50,
  "ma_60": 178.30,
  "ma_120": 175.00,
  "ma_240": 170.25
}
```

---

### Portfolio

Endpoints for managing investment portfolio.

#### GET /api/portfolio

Get full portfolio with holdings and summary.

**Response**: `200 OK`

```json
{
  "holdings": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "quantity": 100,
      "avg_price": 150.00,
      "current_price": 185.50,
      "market_value": 18550.00,
      "cost_basis": 15000.00,
      "pnl": 3550.00,
      "pnl_pct": 23.67,
      "currency": "USD",
      "bought_at": "2025-06-15",
      "note": "Long-term hold"
    }
  ],
  "summary": {
    "total_investment": 15000.00,
    "total_market_value": 18550.00,
    "total_pnl": 3550.00,
    "total_pnl_pct": 23.67,
    "holdings_count": 1,
    "currency": "USD",
    "last_updated": "2026-02-12T10:30:00Z"
  }
}
```

#### GET /api/portfolio/holdings

Get all holdings with current prices.

**Query Parameters**:
- `with_prices` (boolean, optional): Include current prices (default: true)

**Response**: `200 OK`

Returns array of holding objects (see GET /api/portfolio response).

#### POST /api/portfolio/holdings

Add a new holding or add to existing position.

**Request Body**:

```json
{
  "ticker": "AAPL",
  "quantity": 100,
  "avg_price": 150.00,
  "name": "Apple Inc.",
  "currency": "USD",
  "note": "Long-term hold"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ticker | string | Yes | Stock ticker symbol |
| quantity | integer | Yes | Number of shares (> 0) |
| avg_price | float | Yes | Average purchase price (> 0) |
| name | string | No | Stock name |
| currency | string | No | Currency code (default: "KRW") |
| note | string | No | Optional note |

**Response**: `201 Created`

Returns the created/updated holding object.

#### GET /api/portfolio/holdings/{ticker}

Get a single holding by ticker.

**Response**: `200 OK` or `404 Not Found`

#### PUT /api/portfolio/holdings/{ticker}

Update an existing holding.

**Request Body**:

```json
{
  "quantity": 150,
  "avg_price": 155.00,
  "note": "Added more shares"
}
```

All fields are optional - only provided fields are updated.

**Response**: `200 OK` or `404 Not Found`

#### DELETE /api/portfolio/holdings/{ticker}

Remove a holding from portfolio.

**Response**: `204 No Content` or `404 Not Found`

#### GET /api/portfolio/summary

Get aggregated portfolio summary.

**Response**: `200 OK`

```json
{
  "total_investment": 15000.00,
  "total_market_value": 18550.00,
  "total_pnl": 3550.00,
  "total_pnl_pct": 23.67,
  "holdings_count": 1,
  "currency": "KRW",
  "last_updated": "2026-02-12T10:30:00Z"
}
```

#### GET /api/portfolio/sell-signals

Get sell signals based on P&L thresholds.

**Query Parameters**:
- `stop_loss_pct` (float, optional): Stop loss threshold (negative, e.g., -10)
- `take_profit_pct` (float, optional): Take profit threshold (positive, e.g., 20)

**Response**: `200 OK`

```json
{
  "signals": [
    {
      "ticker": "TSLA",
      "name": "Tesla Inc.",
      "signal_type": "stop_loss",
      "reason": "Price dropped below stop loss threshold (-10%)",
      "current_price": 180.00,
      "trigger_price": 200.00,
      "avg_price": 220.00,
      "pnl_pct": -18.18
    }
  ],
  "checked_at": "2026-02-12T10:30:00Z"
}
```

---

### Analysis

Endpoints for AI-powered stock analysis and data enrichment.

#### POST /api/analysis/enrich

Enrich a single stock with technical, fundamental, and news data.

**Request Body**:

```json
{
  "ticker": "AAPL"
}
```

**Response**: `200 OK`

```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "current_price": 185.50,
  "ma_240": 170.25,
  "distance_pct": 8.96,
  "technical": {
    "rsi": 55.2,
    "macd": 1.25,
    "bb_position": "middle"
  },
  "fundamental": {
    "pe_ratio": 28.5,
    "pb_ratio": 45.2,
    "roe": 0.147,
    "market_cap": 2850000000000
  },
  "news": {
    "articles": [],
    "sentiment": "neutral"
  }
}
```

**Note**: This operation may take 10-30 seconds.

#### POST /api/analysis/analyze

Analyze a stock using Claude AI.

**Request Body**:

```json
{
  "ticker": "AAPL",
  "include_news": true
}
```

**Response**: `200 OK`

```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "current_price": 185.50,
  "valuation_score": 6.5,
  "risk_score": 4.0,
  "entry_recommendation": "WAIT",
  "reasoning": "Stock is trading above fair value based on current fundamentals...",
  "key_risks": [
    "Premium valuation relative to sector",
    "China revenue exposure"
  ],
  "catalysts": [
    "AI integration in devices",
    "Services revenue growth"
  ]
}
```

**Error**: `503 Service Unavailable` if ANTHROPIC_API_KEY is not set.

#### GET /api/analysis/reports

Get list of available analysis reports.

**Response**: `200 OK`

```json
{
  "reports": [
    {
      "date": "20260212",
      "market": "SP500",
      "total_stocks": 15,
      "buy_count": 3,
      "wait_count": 8,
      "avoid_count": 4
    }
  ],
  "total_count": 1
}
```

#### GET /api/analysis/reports/{date}

Get detailed analysis report for a specific date.

**Path Parameters**:
- `date` (string, required): Report date in YYYYMMDD format

**Query Parameters**:
- `market` (string, optional): Filter by market (KOSPI, SP500)

**Response**: `200 OK`

```json
{
  "date": "20260212",
  "market": "SP500",
  "content": "# Analysis Report for 2026-02-12\n\n...",
  "stocks": []
}
```

#### GET /api/analysis/enriched/{date}

Get enriched JSON data for a specific date and market.

**Path Parameters**:
- `date` (string, required): Data date in YYYYMMDD format

**Query Parameters**:
- `market` (string, optional): Market name (default: "SP500")

**Response**: `200 OK`

```json
{
  "date": "20260212",
  "market": "SP500",
  "stock_count": 15,
  "stocks": []
}
```

#### GET /api/analysis/enriched

List all available enriched data files.

**Response**: `200 OK`

```json
[
  {
    "market": "SP500",
    "date": "20260212",
    "file": "SP500_20260212_enriched.json"
  }
]
```

#### GET /api/analysis/status

Get analysis service status.

**Response**: `200 OK`

```json
{
  "claude_available": true,
  "cache_available": true,
  "enrichers": {
    "technical": true,
    "fundamental": true,
    "news": true
  },
  "data_dir": "/app/data/cache/ohlcv"
}
```

---

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

### Future Plans

Authentication will be added in a future release:

1. **API Key Authentication**: For programmatic access
2. **JWT Tokens**: For web dashboard sessions
3. **Rate Limiting**: To prevent abuse

When authentication is implemented:
- API keys will be passed via `X-API-Key` header
- JWT tokens will be passed via `Authorization: Bearer <token>` header

---

## Rate Limits

Currently no rate limits are enforced. However, some operations are naturally slow:

| Operation | Typical Duration |
|-----------|-----------------|
| Single stock screening | 1-3 seconds |
| Full universe screening | 2-10 minutes |
| Stock enrichment | 10-30 seconds |
| AI analysis | 30-60 seconds |

Consider implementing client-side timeouts accordingly.

---

## OpenAPI Specification

The full OpenAPI 3.0 specification is available at:
- JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

This can be used to generate client SDKs in various languages.
