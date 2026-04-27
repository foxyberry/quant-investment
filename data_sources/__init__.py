"""
data_sources — unified data layer (Phase 2 skeleton).

Centralises all external data fetching. Replaces scattered fetch calls across:
  utils/fetch.py, api/services/market_data_service.py, screener/, discovery/

Sub-packages:
  data_sources.market    — price/OHLCV, universe lists (yfinance, pykrx)
  data_sources.technical — indicator computation (moved from screener.indicators)
"""
