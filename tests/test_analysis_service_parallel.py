from threading import Lock
import time

import pandas as pd

from api.services.analysis_service import AnalysisService


class _ActiveTracker:
    def __init__(self):
        self._active = 0
        self.max_active = 0
        self._lock = Lock()

    def enter(self):
        with self._lock:
            self._active += 1
            if self._active > self.max_active:
                self.max_active = self._active

    def leave(self):
        with self._lock:
            self._active -= 1


def test_enrich_stock_runs_enrichers_in_parallel():
    service = AnalysisService()

    class FakeCache:
        def get(self, ticker: str, days: int = 250):
            return pd.DataFrame(
                {
                    "close": [100.0, 110.0, 120.0],
                    "open": [99.0, 109.0, 119.0],
                    "high": [101.0, 111.0, 121.0],
                    "low": [98.0, 108.0, 118.0],
                    "volume": [1000, 1100, 1200],
                }
            )

    tracker = _ActiveTracker()

    class FakeTechnicalEnricher:
        def enrich(self, ticker: str, data):
            tracker.enter()
            try:
                time.sleep(0.05)
                return {"rsi": 55.0}
            finally:
                tracker.leave()

    class FakeFundamentalEnricher:
        def enrich(self, ticker: str):
            tracker.enter()
            try:
                time.sleep(0.05)
                return {"name": "Apple Inc.", "pe_ratio": 25.0}
            finally:
                tracker.leave()

    class FakeNewsEnricher:
        def enrich(self, ticker: str, name=None):
            tracker.enter()
            try:
                time.sleep(0.05)
                return {"article_count": 1, "sentiment_summary": "neutral", "articles": []}
            finally:
                tracker.leave()

    service._cache = FakeCache()
    service._technical_enricher = FakeTechnicalEnricher()
    service._fundamental_enricher = FakeFundamentalEnricher()
    service._news_enricher = FakeNewsEnricher()

    result = service.enrich_stock("AAPL", include_news=True)

    assert tracker.max_active >= 2
    assert result.ticker == "AAPL"
    assert result.name == "Apple Inc."
    assert result.technical.get("rsi") == 55.0
    assert result.fundamental.get("pe_ratio") == 25.0
    assert result.news is not None
