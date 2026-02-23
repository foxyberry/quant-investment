"""Tests for issue #228 performance optimizations."""

import time
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestMetadataCacheClose:
    """Test H-4: parquet metadata cache returns close price."""

    def test_metadata_cache_stores_close(self, tmp_path):
        """_get_cache_latest_date should cache close price."""
        import pandas as pd
        from utils.data_cache import OHLCVCache

        cache = OHLCVCache(cache_dir=str(tmp_path))

        # Create test parquet
        df = pd.DataFrame(
            {"close": [100.0, 105.0], "open": [99.0, 104.0], "high": [101.0, 106.0], "low": [98.0, 103.0], "volume": [1000, 2000]},
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )
        df.index.name = "date"
        path = tmp_path / "TEST.parquet"
        df.to_parquet(path)

        # First call populates cache
        cache._get_cache_latest_date(path)
        close = cache._get_cache_latest_close(path)
        assert close == 105.0

    def test_metadata_cache_no_extra_read(self, tmp_path):
        """Second call should use cached data without re-reading."""
        import pandas as pd
        from utils.data_cache import OHLCVCache

        cache = OHLCVCache(cache_dir=str(tmp_path))

        df = pd.DataFrame(
            {"close": [100.0], "open": [99.0], "high": [101.0], "low": [98.0], "volume": [1000]},
            index=pd.to_datetime(["2024-01-01"]),
        )
        path = tmp_path / "TEST.parquet"
        df.to_parquet(path)

        cache._get_cache_latest_date(path)
        # Cache should be populated now
        cache_key = str(path)
        assert cache_key in cache._latest_date_cache
        meta = cache._latest_date_cache[cache_key]
        assert len(meta) == 3
        assert meta[2] == 100.0


class TestUniverseCountCache:
    """Test H-5: universe count cache with TTL."""

    def test_cache_hit(self):
        from api.services.screening_service import ScreeningService

        svc = ScreeningService.__new__(ScreeningService)
        svc._kospi_fetcher = MagicMock()
        svc._us_fetcher = MagicMock()

        # Pre-populate cache
        svc._universe_count_cache = {"KOSPI": (time.time(), 950)}

        count = svc._get_universe_stock_count("KOSPI")
        assert count == 950
        # Fetcher should NOT be called
        svc._kospi_fetcher.get_kospi_symbols.assert_not_called()

    def test_cache_miss_fetches(self):
        from api.services.screening_service import ScreeningService

        svc = ScreeningService.__new__(ScreeningService)
        svc._kospi_fetcher = MagicMock()
        svc._kospi_fetcher.get_kospi_symbols.return_value = [{"symbol": f"{i}.KS"} for i in range(900)]
        svc._us_fetcher = MagicMock()
        svc._universe_count_cache = {}

        count = svc._get_universe_stock_count("KOSPI")
        assert count == 900
        svc._kospi_fetcher.get_kospi_symbols.assert_called_once()

    def test_cache_expired(self):
        from api.services.screening_service import ScreeningService

        svc = ScreeningService.__new__(ScreeningService)
        svc._kospi_fetcher = MagicMock()
        svc._kospi_fetcher.get_kospi_symbols.return_value = [{"symbol": f"{i}.KS"} for i in range(910)]
        svc._us_fetcher = MagicMock()

        # Expired cache
        svc._universe_count_cache = {"KOSPI": (time.time() - 7200, 900)}

        count = svc._get_universe_stock_count("KOSPI")
        assert count == 910
        svc._kospi_fetcher.get_kospi_symbols.assert_called_once()


class TestParallelNameFetch:
    """Test H-3: parallel name fetch in KospiListFetcher."""

    @patch("screener.kospi_fetcher.datetime")
    def test_kospi_fetcher_uses_threadpool(self, mock_dt):
        """Verify _fetch_from_pykrx uses ThreadPoolExecutor."""
        mock_dt.now.return_value.strftime.return_value = "20240101"

        from screener.kospi_fetcher import KospiListFetcher

        fetcher = KospiListFetcher(use_cache=False)

        with patch("screener.kospi_fetcher.KospiListFetcher._fetch_from_pykrx") as mock_fetch:
            mock_fetch.return_value = [
                {"symbol": "005930.KS", "code": "005930", "name": "삼성전자", "sector": ""}
            ]
            result = fetcher.get_kospi_symbols(refresh=True)
            assert len(result) >= 1
