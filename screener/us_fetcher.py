"""
US Stock List Fetcher Module
미국 주식 종목 리스트 수집 모듈

- Wikipedia에서 S&P 500 리스트 가져오기
- 또는 마스터 파일에서 로드
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

import pandas as pd

logger = logging.getLogger(__name__)


class UsStockFetcher:
    """미국 주식 종목 리스트 수집기"""

    CACHE_FILE = "data/us/sp500_list.csv"
    NASDAQ100_CACHE_FILE = "data/us/nasdaq100_list.csv"
    MASTER_FILE = "data/us/us_master.csv"
    CACHE_DAYS = 7
    SP500_MIN_VALID_COUNT = 400
    NASDAQ100_MIN_VALID_COUNT = 90
    SP500_DATASET_URL = (
        "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
    )
    NASDAQ100_API_URL = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self._repo_root = Path(__file__).resolve().parents[1]

    def _resolve_path(self, relative_path: str) -> Path:
        """작업 디렉토리와 무관하게 저장 경로를 리포지토리 루트 기준으로 고정."""
        return self._repo_root / relative_path

    def get_sp500_symbols(self, refresh: bool = False) -> List[Dict]:
        """
        S&P 500 종목 리스트 반환

        Args:
            refresh: True면 캐시 무시하고 새로 가져옴

        Returns:
            [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'}, ...]
        """
        # 캐시 확인
        if self.use_cache and not refresh:
            cached = self._load_cache()
            if cached is not None and self._is_valid_count("SP500", len(cached)):
                logger.info(f"캐시에서 {len(cached)}개 종목 로드")
                return cached
            if cached is not None:
                logger.warning(
                    "SP500 캐시 종목 수가 비정상(%d)이라 캐시를 무시하고 재수집합니다.",
                    len(cached),
                )

        # 새로 가져오기
        symbols = self._fetch_sp500_from_remote()

        if symbols and self._is_valid_count("SP500", len(symbols)):
            self._save_cache(symbols)
            logger.info(f"S&P 500 {len(symbols)}개 종목 수집 완료")
        elif symbols:
            logger.warning("SP500 수집 결과(%d개)가 비정상이라 캐시 저장을 건너뜁니다.", len(symbols))

        return symbols

    def _fetch_sp500_from_remote(self) -> List[Dict]:
        """원격 CSV 소스에서 S&P 500 종목 리스트 가져오기."""
        try:
            request = Request(
                self.SP500_DATASET_URL,
                headers={"User-Agent": "Mozilla/5.0 (compatible; QuantInvestment/1.0)"},
            )
            with urlopen(request, timeout=20) as response:
                csv_text = response.read().decode("utf-8", errors="replace")

            reader = csv.DictReader(csv_text.splitlines())
            symbols = []
            for row in reader:
                symbol = (row.get("Symbol") or "").strip()
                name = (row.get("Name") or row.get("Security") or "").strip()
                sector = (row.get("Sector") or row.get("GICS Sector") or "").strip()

                # BRK.B -> BRK-B (yfinance 형식)
                symbol = symbol.replace(".", "-")

                if symbol and name:
                    symbols.append(
                        {
                            "symbol": symbol,
                            "name": name,
                            "sector": sector,
                        }
                    )

            logger.info("원격 CSV에서 SP500 %d개 종목 수집", len(symbols))
            return symbols if symbols else self._fetch_fallback()

        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as e:
            logger.warning(f"SP500 원격 소스 조회 실패: {e}")
            return self._fetch_fallback()

    def _fetch_fallback(self) -> List[Dict]:
        """
        대체 방법: 마스터 파일 또는 주요 종목 하드코딩
        """
        master_path = self._resolve_path(self.MASTER_FILE)

        if master_path.exists():
            try:
                df = pd.read_csv(master_path)
                symbols = []

                for _, row in df.iterrows():
                    symbols.append({
                        'symbol': row['symbol'],
                        'name': row.get('name', row['symbol']),
                        'sector': row.get('sector', '')
                    })

                logger.info(f"마스터 파일에서 {len(symbols)}개 종목 로드")
                return symbols

            except Exception as e:
                logger.warning(f"마스터 파일 로드 실패: {e}")

        # 최후의 대안: 주요 종목 하드코딩
        logger.info("기본 주요 종목 리스트 사용")
        return self._get_major_stocks()

    def _get_major_stocks(self) -> List[Dict]:
        """주요 미국 주식 (fallback)"""
        return [
            # Technology
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'sector': 'Technology'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corp.', 'sector': 'Technology'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Technology'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'AMD', 'name': 'AMD Inc.', 'sector': 'Technology'},
            {'symbol': 'INTC', 'name': 'Intel Corp.', 'sector': 'Technology'},
            {'symbol': 'CRM', 'name': 'Salesforce Inc.', 'sector': 'Technology'},
            {'symbol': 'ORCL', 'name': 'Oracle Corp.', 'sector': 'Technology'},
            {'symbol': 'ADBE', 'name': 'Adobe Inc.', 'sector': 'Technology'},
            {'symbol': 'CSCO', 'name': 'Cisco Systems', 'sector': 'Technology'},
            {'symbol': 'AVGO', 'name': 'Broadcom Inc.', 'sector': 'Technology'},
            {'symbol': 'QCOM', 'name': 'Qualcomm Inc.', 'sector': 'Technology'},
            # Finance
            {'symbol': 'JPM', 'name': 'JPMorgan Chase', 'sector': 'Financials'},
            {'symbol': 'V', 'name': 'Visa Inc.', 'sector': 'Financials'},
            {'symbol': 'MA', 'name': 'Mastercard Inc.', 'sector': 'Financials'},
            {'symbol': 'BAC', 'name': 'Bank of America', 'sector': 'Financials'},
            {'symbol': 'WFC', 'name': 'Wells Fargo', 'sector': 'Financials'},
            {'symbol': 'GS', 'name': 'Goldman Sachs', 'sector': 'Financials'},
            {'symbol': 'MS', 'name': 'Morgan Stanley', 'sector': 'Financials'},
            {'symbol': 'BLK', 'name': 'BlackRock Inc.', 'sector': 'Financials'},
            # Healthcare
            {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare'},
            {'symbol': 'UNH', 'name': 'UnitedHealth Group', 'sector': 'Healthcare'},
            {'symbol': 'PFE', 'name': 'Pfizer Inc.', 'sector': 'Healthcare'},
            {'symbol': 'MRK', 'name': 'Merck & Co.', 'sector': 'Healthcare'},
            {'symbol': 'ABBV', 'name': 'AbbVie Inc.', 'sector': 'Healthcare'},
            {'symbol': 'LLY', 'name': 'Eli Lilly', 'sector': 'Healthcare'},
            # Consumer
            {'symbol': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Consumer Staples'},
            {'symbol': 'PG', 'name': 'Procter & Gamble', 'sector': 'Consumer Staples'},
            {'symbol': 'KO', 'name': 'Coca-Cola Co.', 'sector': 'Consumer Staples'},
            {'symbol': 'PEP', 'name': 'PepsiCo Inc.', 'sector': 'Consumer Staples'},
            {'symbol': 'COST', 'name': 'Costco Wholesale', 'sector': 'Consumer Staples'},
            {'symbol': 'MCD', 'name': "McDonald's Corp.", 'sector': 'Consumer Discretionary'},
            {'symbol': 'NKE', 'name': 'Nike Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'SBUX', 'name': 'Starbucks Corp.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'HD', 'name': 'Home Depot', 'sector': 'Consumer Discretionary'},
            {'symbol': 'LOW', 'name': "Lowe's Companies", 'sector': 'Consumer Discretionary'},
            # Energy
            {'symbol': 'XOM', 'name': 'Exxon Mobil', 'sector': 'Energy'},
            {'symbol': 'CVX', 'name': 'Chevron Corp.', 'sector': 'Energy'},
            {'symbol': 'COP', 'name': 'ConocoPhillips', 'sector': 'Energy'},
            # Industrial
            {'symbol': 'CAT', 'name': 'Caterpillar Inc.', 'sector': 'Industrials'},
            {'symbol': 'BA', 'name': 'Boeing Co.', 'sector': 'Industrials'},
            {'symbol': 'HON', 'name': 'Honeywell', 'sector': 'Industrials'},
            {'symbol': 'UPS', 'name': 'United Parcel Service', 'sector': 'Industrials'},
            {'symbol': 'GE', 'name': 'General Electric', 'sector': 'Industrials'},
            # Communication
            {'symbol': 'DIS', 'name': 'Walt Disney Co.', 'sector': 'Communication Services'},
            {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Communication Services'},
            {'symbol': 'CMCSA', 'name': 'Comcast Corp.', 'sector': 'Communication Services'},
            {'symbol': 'T', 'name': 'AT&T Inc.', 'sector': 'Communication Services'},
            {'symbol': 'VZ', 'name': 'Verizon', 'sector': 'Communication Services'},
        ]

    def _load_cache(self) -> Optional[List[Dict]]:
        """캐시 파일에서 로드"""
        cache_path = self._resolve_path(self.CACHE_FILE)

        if not cache_path.exists():
            return None

        # 캐시 유효성 확인
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if (datetime.now() - mtime).days > self.CACHE_DAYS:
            logger.info("캐시 만료됨")
            return None

        try:
            df = pd.read_csv(cache_path)
            return df.to_dict('records')
        except Exception as e:
            logger.warning(f"캐시 로드 실패: {e}")
            return None

    def _save_cache(self, symbols: List[Dict]) -> None:
        """캐시 파일에 저장"""
        try:
            cache_path = self._resolve_path(self.CACHE_FILE)
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            df = pd.DataFrame(symbols)
            df.to_csv(cache_path, index=False, encoding='utf-8')
            logger.info(f"캐시 저장: {cache_path}")
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {e}")

    def get_nasdaq100_symbols(self, refresh: bool = False) -> List[Dict]:
        """
        NASDAQ 100 종목 리스트 반환

        Args:
            refresh: True면 캐시 무시하고 새로 가져옴

        Returns:
            [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': ''}, ...]
        """
        if self.use_cache and not refresh:
            cached = self._load_nasdaq100_cache()
            if cached is not None and self._is_valid_count("NASDAQ100", len(cached)):
                logger.info(f"캐시에서 NASDAQ100 {len(cached)}개 종목 로드")
                return cached
            if cached is not None:
                logger.warning(
                    "NASDAQ100 캐시 종목 수가 비정상(%d)이라 캐시를 무시하고 재수집합니다.",
                    len(cached),
                )

        symbols = self._fetch_nasdaq100_from_remote()

        if symbols and self._is_valid_count("NASDAQ100", len(symbols)):
            self._save_nasdaq100_cache(symbols)
            logger.info(f"NASDAQ 100 {len(symbols)}개 종목 수집 완료")
        elif symbols:
            logger.warning("NASDAQ100 수집 결과(%d개)가 비정상이라 캐시 저장을 건너뜁니다.", len(symbols))

        return symbols

    def _fetch_nasdaq100_from_remote(self) -> List[Dict]:
        """NASDAQ API에서 NASDAQ 100 종목 리스트 가져오기."""
        try:
            request = Request(
                self.NASDAQ100_API_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; QuantInvestment/1.0)",
                    "Accept": "application/json",
                },
            )
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))

            rows = (
                payload.get("data", {})
                .get("data", {})
                .get("rows", [])
            )
            symbols = []
            for row in rows:
                symbol = str(row.get("symbol", "")).strip().replace(".", "-")
                name = str(row.get("companyName", "")).strip()
                sector = str(row.get("sector", "")).strip()
                if symbol and name:
                    symbols.append(
                        {
                            "symbol": symbol,
                            "name": name,
                            "sector": sector,
                        }
                    )

            logger.info("NASDAQ API에서 NASDAQ100 %d개 종목 수집", len(symbols))
            return symbols if symbols else self._fetch_nasdaq100_fallback()
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as e:
            logger.warning(f"NASDAQ100 원격 소스 조회 실패: {e}")
            return self._fetch_nasdaq100_fallback()

    def _fetch_nasdaq100_fallback(self) -> List[Dict]:
        """NASDAQ 100 대체 방법: 주요 종목 하드코딩.

        Unlike SP500 fallback, we skip us_master.csv because it may contain
        a broad universe that doesn't represent NASDAQ 100 specifically.
        """
        logger.info("NASDAQ100 기본 주요 종목 리스트 사용 (fallback)")
        return self._get_major_stocks()

    def _is_valid_count(self, universe: str, count: int) -> bool:
        """비정상적으로 작은 종목 수인지 판정."""
        if universe == "SP500":
            return count >= self.SP500_MIN_VALID_COUNT
        if universe == "NASDAQ100":
            return count >= self.NASDAQ100_MIN_VALID_COUNT
        return count > 0

    def _load_nasdaq100_cache(self) -> Optional[List[Dict]]:
        """NASDAQ100 캐시 파일에서 로드"""
        cache_path = self._resolve_path(self.NASDAQ100_CACHE_FILE)

        if not cache_path.exists():
            return None

        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if (datetime.now() - mtime).days > self.CACHE_DAYS:
            logger.info("NASDAQ100 캐시 만료됨")
            return None

        try:
            df = pd.read_csv(cache_path)
            return df.to_dict('records')
        except Exception as e:
            logger.warning(f"NASDAQ100 캐시 로드 실패: {e}")
            return None

    def _save_nasdaq100_cache(self, symbols: List[Dict]) -> None:
        """NASDAQ100 캐시 파일에 저장"""
        try:
            cache_path = self._resolve_path(self.NASDAQ100_CACHE_FILE)
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            df = pd.DataFrame(symbols)
            df.to_csv(cache_path, index=False, encoding='utf-8')
            logger.info(f"NASDAQ100 캐시 저장: {cache_path}")
        except Exception as e:
            logger.warning(f"NASDAQ100 캐시 저장 실패: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    fetcher = UsStockFetcher()
    symbols = fetcher.get_sp500_symbols()

    print(f"\n총 {len(symbols)}개 종목")
    print("\n상위 10개:")
    for s in symbols[:10]:
        print(f"  {s['symbol']} - {s['name']} ({s['sector']})")
