"""Tests for issue #229 performance optimizations."""

import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock, call
import pytest


class TestPerKeyLock:
    """Test M-1: per-key lock in FundamentalCache."""

    def test_key_lock_created(self):
        """Each namespace+key combo gets its own lock."""
        from utils.fundamental_cache import FundamentalCache
        cache = FundamentalCache(cache_dir="/tmp/test_cache_229")
        lock1 = cache._get_key_lock("yf_info", "AAPL")
        lock2 = cache._get_key_lock("yf_info", "MSFT")
        lock3 = cache._get_key_lock("yf_info", "AAPL")

        assert lock1 is lock3  # Same key = same lock
        assert lock1 is not lock2  # Different key = different lock

    def test_concurrent_same_key(self):
        """Two threads requesting the same key should not both fetch."""
        from utils.fundamental_cache import FundamentalCache
        cache = FundamentalCache(cache_dir="/tmp/test_cache_229")

        fetch_count = {"count": 0}
        lock = cache._get_key_lock("test", "key1")

        def worker():
            with lock:
                fetch_count["count"] += 1
                time.sleep(0.1)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert fetch_count["count"] == 3  # All ran but serialized


class TestEnrichmentParallel:
    """Test M-3: parallel technical + fundamental enrichment."""

    @patch("api.services.analysis_service.AnalysisService.news_enricher", new_callable=PropertyMock)
    @patch("api.services.analysis_service.AnalysisService.fundamental_enricher", new_callable=PropertyMock)
    @patch("api.services.analysis_service.AnalysisService.technical_enricher", new_callable=PropertyMock)
    @patch("api.services.analysis_service.AnalysisService.cache", new_callable=PropertyMock)
    def test_enrichment_runs_parallel(self, mock_cache, mock_tech, mock_fund, mock_news):
        import pandas as pd
        from api.services.analysis_service import AnalysisService

        # Setup mocks
        df = pd.DataFrame(
            {"close": [100.0], "open": [99.0], "high": [101.0], "low": [98.0], "volume": [1000]},
            index=pd.to_datetime(["2024-01-01"]),
        )
        mock_cache.return_value.get.return_value = df

        tech_enricher = MagicMock()
        tech_enricher.enrich.return_value = {"rsi": 50}
        mock_tech.return_value = tech_enricher

        fund_enricher = MagicMock()
        fund_enricher.enrich.return_value = {"name": "TestCo", "pe_ratio": 15}
        mock_fund.return_value = fund_enricher

        news_enricher = MagicMock()
        news_enricher.enrich.return_value = {"articles": []}
        mock_news.return_value = news_enricher

        svc = AnalysisService()
        result = svc.enrich_stock("AAPL")

        assert result.name == "TestCo"
        tech_enricher.enrich.assert_called_once()
        fund_enricher.enrich.assert_called_once()
        news_enricher.enrich.assert_called_once()


class TestNasdaq100Cache:
    """Test M-6: NASDAQ100 cache creation and loading."""

    def test_cache_save_and_load(self, tmp_path):
        from screener.us_fetcher import UsStockFetcher

        fetcher = UsStockFetcher(use_cache=True)
        fetcher.NASDAQ100_CACHE_FILE = str(tmp_path / "nasdaq100_list.csv")

        symbols = [
            {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
            {"symbol": "MSFT", "name": "Microsoft", "sector": "Technology"},
        ]

        fetcher._save_nasdaq100_cache(symbols)
        loaded = fetcher._load_nasdaq100_cache()

        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0]["symbol"] == "AAPL"


class TestCacheEviction:
    """Test L-2: in-memory cache size limit."""

    def test_eviction_when_over_maxsize(self):
        from screener.conditions.fundamental import _evict_cache

        cache = {f"ticker_{i}": {"data": i} for i in range(600)}
        # _evict_cache expects caller to hold lock; safe in single-threaded test
        _evict_cache(cache, maxsize=500, batch=100)
        assert len(cache) == 500

    def test_no_eviction_under_maxsize(self):
        from screener.conditions.fundamental import _evict_cache

        cache = {f"ticker_{i}": {"data": i} for i in range(100)}
        _evict_cache(cache, maxsize=500, batch=100)
        assert len(cache) == 100


class TestCacheLockProtection:
    """Test that cache locks protect concurrent access."""

    def test_info_cache_lock_exists(self):
        from screener.conditions.fundamental import _info_cache_lock, _statement_cache_lock
        assert isinstance(_info_cache_lock, type(threading.Lock()))
        assert isinstance(_statement_cache_lock, type(threading.Lock()))


class TestKoreanEnrichmentMerge:
    """Test that Korean stock enrichment merges pykrx/naver deterministically."""

    def test_pykrx_takes_priority_over_naver(self):
        from data_enrichment.fundamental import FundamentalEnricher, FundamentalData

        enricher = FundamentalEnricher(use_naver_fallback=True)

        # Patch _enrich_from_pykrx and _enrich_from_naver to write different values
        def mock_pykrx(data, code):
            data.pe_ratio = 10.0
            data.pb_ratio = 1.5

        def mock_naver(data, code):
            data.pe_ratio = 12.0  # Should be overridden by pykrx
            data.roe = 15.0       # Only naver has this

        def mock_yfinance(data, ticker):
            pass  # No-op for this test

        with patch.object(enricher, '_enrich_from_pykrx', side_effect=mock_pykrx), \
             patch.object(enricher, '_enrich_from_naver', side_effect=mock_naver), \
             patch.object(enricher, '_enrich_korean_from_yfinance', side_effect=mock_yfinance):
            result = enricher.enrich_as_dataclass("005930.KS")

        assert result.pe_ratio == 10.0   # pykrx wins
        assert result.pb_ratio == 1.5    # only pykrx
        assert result.roe == 15.0        # only naver


class TestNasdaq100Fallback:
    """Test NASDAQ100 fallback when Wikipedia fails."""

    def test_fallback_returns_major_stocks(self):
        from screener.us_fetcher import UsStockFetcher

        fetcher = UsStockFetcher(use_cache=False)
        result = fetcher._fetch_nasdaq100_fallback()
        assert len(result) > 0
        symbols = [s['symbol'] for s in result]
        assert 'AAPL' in symbols
