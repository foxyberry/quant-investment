"""
Data Enrichment Module

This module provides enrichment capabilities for stock data,
including fundamental data, technical indicators and news integration.

Usage:
    from data_enrichment import TechnicalEnricher, NewsEnricher, FundamentalEnricher

    # Fundamental data
    fund_enricher = FundamentalEnricher()
    result = fund_enricher.enrich("AAPL")

    # Technical indicators
    tech_enricher = TechnicalEnricher()
    result = tech_enricher.enrich("AAPL", ohlcv_data)

    # News enrichment
    news_enricher = NewsEnricher()
    result = news_enricher.enrich("AAPL", name="Apple Inc.")
"""

from data_sources.fundamental.fundamental import (
    FundamentalEnricher,
    FundamentalData,
    enrich_fundamental,
)
from data_sources.news.aggregator import NewsEnricher
from data_sources.technical.technical import (
    TechnicalEnricher,
    TechnicalEnricherConfig,
    enrich_technical,
    RSISignal,
    MACDCross,
    BBPosition,
    OBVTrend,
)

__all__ = [
    # Fundamental
    "FundamentalEnricher",
    "FundamentalData",
    "enrich_fundamental",
    # News
    "NewsEnricher",
    # Technical
    "TechnicalEnricher",
    "TechnicalEnricherConfig",
    "enrich_technical",
    "RSISignal",
    "MACDCross",
    "BBPosition",
    "OBVTrend",
]
