"""
코스피/코스닥 종목 리스트 수집 모듈
- 마스터 CSV (KRX KIND 기반) 우선 사용
- 캐시 → 마스터 CSV → pykrx 순 폴백
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class KospiListFetcher:
    """코스피/코스닥 종목 리스트 수집기 (CSV 우선)"""

    MASTER_FILE = "data/korean/kospi_master.csv"
    CACHE_FILE = "data/korean/kospi_list.csv"
    KOSDAQ_MASTER_FILE = "data/korean/kosdaq_master.csv"
    KOSDAQ_CACHE_FILE = "data/korean/kosdaq_list.csv"
    CACHE_DAYS = 7

    # Minimum valid count: if fetched list is smaller, fall through to next source
    KOSPI_MIN_VALID_COUNT = 500
    KOSDAQ_MIN_VALID_COUNT = 1000

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache

    @staticmethod
    def _resolve_path(relative: str) -> Path:
        return Path(__file__).resolve().parent.parent / relative

    # ------------------------------------------------------------------
    # KOSPI
    # ------------------------------------------------------------------

    def get_kospi_symbols(self, refresh: bool = False) -> List[Dict]:
        """코스피 종목 리스트 반환 (cache → master CSV → pykrx)"""
        if self.use_cache and not refresh:
            cached = self._load_cache(self.CACHE_FILE)
            if cached is not None and len(cached) >= self.KOSPI_MIN_VALID_COUNT:
                return cached

        # Primary: master CSV (comprehensive, always available)
        symbols = self._load_master_csv(self.MASTER_FILE, suffix=".KS")
        if len(symbols) >= self.KOSPI_MIN_VALID_COUNT:
            self._save_cache(symbols, self.CACHE_FILE)
            return symbols

        # Secondary: pykrx (single attempt)
        pykrx_symbols = self._fetch_from_pykrx("KOSPI", ".KS")
        if len(pykrx_symbols) >= self.KOSPI_MIN_VALID_COUNT:
            self._save_cache(pykrx_symbols, self.CACHE_FILE)
            return pykrx_symbols

        # Return whatever we have (master CSV even if small)
        return symbols if symbols else pykrx_symbols

    # ------------------------------------------------------------------
    # KOSDAQ
    # ------------------------------------------------------------------

    def get_kosdaq_symbols(self, refresh: bool = False) -> List[Dict]:
        """코스닥 종목 리스트 반환 (cache → master CSV → pykrx)"""
        if self.use_cache and not refresh:
            cached = self._load_cache(self.KOSDAQ_CACHE_FILE)
            if cached is not None and len(cached) >= self.KOSDAQ_MIN_VALID_COUNT:
                return cached

        # Primary: master CSV
        symbols = self._load_master_csv(self.KOSDAQ_MASTER_FILE, suffix=".KQ")
        if len(symbols) >= self.KOSDAQ_MIN_VALID_COUNT:
            self._save_cache(symbols, self.KOSDAQ_CACHE_FILE)
            return symbols

        # Secondary: pykrx (single attempt)
        pykrx_symbols = self._fetch_from_pykrx("KOSDAQ", ".KQ")
        if len(pykrx_symbols) >= self.KOSDAQ_MIN_VALID_COUNT:
            self._save_cache(pykrx_symbols, self.KOSDAQ_CACHE_FILE)
            return pykrx_symbols

        return symbols if symbols else pykrx_symbols

    # ------------------------------------------------------------------
    # Fetchers
    # ------------------------------------------------------------------

    def _fetch_from_pykrx(self, market: str, suffix: str) -> List[Dict]:
        """pykrx에서 종목 리스트 가져오기 (1회만 시도)"""
        try:
            from pykrx import stock

            today = datetime.now().strftime("%Y%m%d")
            tickers = stock.get_market_ticker_list(today, market=market)
            if not tickers:
                logger.info(f"pykrx {market} 종목 리스트 비어있음 (CSV 사용)")
                return []

            symbols = []
            for ticker_code in tickers:
                try:
                    name = stock.get_market_ticker_name(ticker_code)
                except Exception:
                    name = ticker_code
                symbols.append({
                    "symbol": f"{ticker_code}{suffix}",
                    "code": ticker_code,
                    "name": name,
                    "sector": "",
                })

            logger.info(f"pykrx {market} {len(symbols)}개 종목 수집")
            return symbols
        except ImportError:
            return []
        except Exception as e:
            logger.info(f"pykrx {market} 조회 실패 (CSV 사용): {e}")
            return []

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _load_master_csv(self, relative_path: str, suffix: str) -> List[Dict]:
        master_path = self._resolve_path(relative_path)
        if not master_path.exists():
            logger.warning(f"마스터 파일 없음: {master_path}")
            return []

        try:
            df = pd.read_csv(master_path, dtype={"code": str})
            symbols = []
            for _, row in df.iterrows():
                code = str(row["code"]).zfill(6)
                symbols.append({
                    "symbol": f"{code}{suffix}",
                    "code": code,
                    "name": row["name"],
                    "sector": row.get("sector", ""),
                })
            logger.info(f"마스터 파일에서 {len(symbols)}개 종목 로드: {master_path}")
            return symbols
        except Exception as e:
            logger.error(f"마스터 파일 로드 실패: {e}")
            return []

    def _load_cache(self, relative_path: str) -> Optional[List[Dict]]:
        cache_path = self._resolve_path(relative_path)
        if not cache_path.exists():
            return None

        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if (datetime.now() - mtime).days > self.CACHE_DAYS:
            return None

        try:
            df = pd.read_csv(cache_path)
            return df.to_dict("records")
        except Exception as e:
            logger.warning(f"캐시 로드 실패: {e}")
            return None

    def _save_cache(self, symbols: List[Dict], relative_path: str) -> None:
        try:
            cache_path = self._resolve_path(relative_path)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(symbols)
            df.to_csv(cache_path, index=False, encoding="utf-8-sig")
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    fetcher = KospiListFetcher()

    symbols = fetcher.get_kospi_symbols()
    print(f"\n코스피 총 {len(symbols)}개 종목")
    print("\n상위 10개:")
    for s in symbols[:10]:
        print(f"  {s['symbol']} - {s['name']} ({s['sector']})")

    kosdaq = fetcher.get_kosdaq_symbols()
    print(f"\n코스닥 총 {len(kosdaq)}개 종목")
    print("\n상위 10개:")
    for s in kosdaq[:10]:
        print(f"  {s['symbol']} - {s['name']} ({s['sector']})")
