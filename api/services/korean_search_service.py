"""
Korean stock search service.

Provides in-memory search for Korean stocks using local CSV data.
Supports name substring matching and code prefix matching.
"""

import csv
import logging
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "korean"

CSV_SOURCES = {
    "kospi": {
        "cache": "kospi_list.csv",
        "master": "kospi_master.csv",
        "suffix": ".KS",
    },
    "kosdaq": {
        "cache": "kosdaq_list.csv",
        "master": "kosdaq_master.csv",
        "suffix": ".KQ",
    },
}


@dataclass
class KoreanStockEntry:
    symbol: str  # e.g. "005930.KS"
    code: str  # e.g. "005930"
    name: str  # e.g. "삼성전자"
    sector: str  # e.g. "전기전자"


@dataclass
class _MarketData:
    entries: List[KoreanStockEntry] = field(default_factory=list)
    source_path: str = ""
    mtime: float = 0.0


class KoreanSearchService:
    """In-memory search service for Korean stocks loaded from CSV files."""

    def __init__(self) -> None:
        self._markets: Dict[str, _MarketData] = {}
        self._loaded = False
        self._lock = threading.Lock()

    def _pick_csv(self, market: str) -> Optional[Path]:
        """Pick best available CSV: cache first, then master fallback."""
        src = CSV_SOURCES[market]
        cache_path = DATA_DIR / src["cache"]
        master_path = DATA_DIR / src["master"]

        # Use cache if it exists and has more than just a header
        if cache_path.exists() and cache_path.stat().st_size > 50:
            return cache_path

        if master_path.exists():
            return master_path

        return None

    def _load_csv(self, market: str) -> List[KoreanStockEntry]:
        """Load entries from a single market CSV."""
        path = self._pick_csv(market)
        if path is None:
            logger.warning("No CSV found for market %s", market)
            return []

        suffix = CSV_SOURCES[market]["suffix"]
        entries: List[KoreanStockEntry] = []

        try:
            with open(path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("code", "").strip()
                    name = row.get("name", "").strip()
                    sector = row.get("sector", "").strip()
                    if not code or not name:
                        continue
                    entries.append(
                        KoreanStockEntry(
                            symbol=f"{code}{suffix}",
                            code=code,
                            name=name,
                            sector=sector,
                        )
                    )
        except Exception:
            logger.exception("Failed to load %s", path)
            return []

        mtime = path.stat().st_mtime
        self._markets[market] = _MarketData(
            entries=entries, source_path=str(path), mtime=mtime
        )
        logger.info("Loaded %d entries from %s", len(entries), path)
        return entries

    def _ensure_loaded(self) -> None:
        """Lazy-load all market CSVs on first access, reload if files changed."""
        with self._lock:
            if not self._loaded:
                for market in CSV_SOURCES:
                    self._load_csv(market)
                self._loaded = True
                return

            # Check for file changes
            for market in CSV_SOURCES:
                path = self._pick_csv(market)
                if path is None:
                    continue
                current_mtime = path.stat().st_mtime
                cached = self._markets.get(market)
                if cached is None or cached.mtime < current_mtime:
                    self._load_csv(market)

    def _all_entries(self) -> List[KoreanStockEntry]:
        """Return combined entries from all markets."""
        self._ensure_loaded()
        result: List[KoreanStockEntry] = []
        for data in self._markets.values():
            result.extend(data.entries)
        return result

    def search(self, query: str, limit: int = 20) -> List[KoreanStockEntry]:
        """
        Search Korean stocks by name or code.

        Name: substring match (case-insensitive for mixed queries).
        Code: prefix match on numeric code.

        Args:
            query: Search string (Korean name or numeric code).
            limit: Maximum results to return.

        Returns:
            Matching KoreanStockEntry list, in CSV order (KOSPI first, then KOSDAQ).
        """
        entries = self._all_entries()
        if not entries:
            return []

        query = query.strip()
        if not query:
            return []

        is_code_query = bool(re.match(r"^\d+$", query))
        results: List[KoreanStockEntry] = []
        query_lower = query.lower()

        for entry in entries:
            if is_code_query:
                if entry.code.startswith(query):
                    results.append(entry)
            else:
                if query_lower in entry.name.lower():
                    results.append(entry)

            if len(results) >= limit:
                break

        return results


_instance: Optional[KoreanSearchService] = None


def get_korean_search_service() -> KoreanSearchService:
    """Get or create the singleton KoreanSearchService instance."""
    global _instance
    if _instance is None:
        _instance = KoreanSearchService()
    return _instance
