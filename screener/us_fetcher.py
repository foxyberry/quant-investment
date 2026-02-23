"""
US Stock List Fetcher Module
미국 주식 종목 리스트 수집 모듈

- Wikipedia에서 S&P 500 리스트 가져오기
- 또는 마스터 파일에서 로드
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class UsStockFetcher:
    """미국 주식 종목 리스트 수집기"""

    CACHE_FILE = "data/us/sp500_list.csv"
    NASDAQ100_CACHE_FILE = "data/us/nasdaq100_list.csv"
    MASTER_FILE = "data/us/us_master.csv"
    CACHE_DAYS = 7

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache

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
            if cached is not None:
                logger.info(f"캐시에서 {len(cached)}개 종목 로드")
                return cached

        # 새로 가져오기
        symbols = self._fetch_from_wikipedia()

        if symbols:
            self._save_cache(symbols)
            logger.info(f"S&P 500 {len(symbols)}개 종목 수집 완료")

        return symbols

    def _fetch_from_wikipedia(self) -> List[Dict]:
        """Wikipedia에서 S&P 500 종목 리스트 가져오기"""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            # User-Agent 헤더 추가 (403 방지)
            tables = pd.read_html(
                url,
                storage_options={'User-Agent': 'Mozilla/5.0 (compatible; QuantInvestment/1.0)'}
            )

            if not tables:
                logger.warning("Wikipedia에서 테이블을 찾지 못함")
                return self._fetch_fallback()

            df = tables[0]

            symbols = []
            for _, row in df.iterrows():
                symbol = row.get('Symbol', '')
                name = row.get('Security', '')
                sector = row.get('GICS Sector', '')

                # BRK.B -> BRK-B (yfinance 형식)
                symbol = symbol.replace('.', '-')

                if symbol and name:
                    symbols.append({
                        'symbol': symbol,
                        'name': name,
                        'sector': sector
                    })

            logger.info(f"Wikipedia에서 {len(symbols)}개 종목 수집")
            return symbols if symbols else self._fetch_fallback()

        except Exception as e:
            logger.warning(f"Wikipedia 조회 실패: {e}")
            return self._fetch_fallback()

    def _fetch_fallback(self) -> List[Dict]:
        """
        대체 방법: 마스터 파일 또는 주요 종목 하드코딩
        """
        master_path = Path(self.MASTER_FILE)

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
        cache_path = Path(self.CACHE_FILE)

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
            cache_path = Path(self.CACHE_FILE)
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
            if cached is not None:
                logger.info(f"캐시에서 NASDAQ100 {len(cached)}개 종목 로드")
                return cached

        symbols = self._fetch_nasdaq100_from_wikipedia()

        if symbols:
            self._save_nasdaq100_cache(symbols)
            logger.info(f"NASDAQ 100 {len(symbols)}개 종목 수집 완료")

        return symbols

    def _fetch_nasdaq100_from_wikipedia(self) -> List[Dict]:
        """Wikipedia에서 NASDAQ 100 종목 리스트 가져오기"""
        try:
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            tables = pd.read_html(url)

            for table in tables:
                if 'Ticker' in table.columns or 'Symbol' in table.columns:
                    symbol_col = 'Ticker' if 'Ticker' in table.columns else 'Symbol'
                    name_col = 'Company' if 'Company' in table.columns else 'Security'

                    symbols = []
                    for _, row in table.iterrows():
                        symbol = row.get(symbol_col, '')
                        name = row.get(name_col, '')

                        if symbol and name:
                            symbols.append({
                                'symbol': str(symbol).replace('.', '-'),
                                'name': name,
                                'sector': ''
                            })

                    if symbols:
                        logger.info(f"NASDAQ 100에서 {len(symbols)}개 종목 수집")
                        return symbols

            logger.warning("Wikipedia에서 NASDAQ 100 테이블을 찾지 못함")
            return self._fetch_nasdaq100_fallback()

        except Exception as e:
            logger.warning(f"NASDAQ 100 조회 실패: {e}")
            return self._fetch_nasdaq100_fallback()

    def _fetch_nasdaq100_fallback(self) -> List[Dict]:
        """NASDAQ 100 대체 방법: 마스터 파일 또는 주요 종목 하드코딩"""
        master_path = Path(self.MASTER_FILE)

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

                if symbols:
                    logger.info(f"마스터 파일에서 NASDAQ100 {len(symbols)}개 종목 로드")
                    return symbols

            except Exception as e:
                logger.warning(f"NASDAQ100 마스터 파일 로드 실패: {e}")

        logger.info("NASDAQ100 기본 주요 종목 리스트 사용")
        return self._get_major_stocks()

    def _load_nasdaq100_cache(self) -> Optional[List[Dict]]:
        """NASDAQ100 캐시 파일에서 로드"""
        cache_path = Path(self.NASDAQ100_CACHE_FILE)

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
            cache_path = Path(self.NASDAQ100_CACHE_FILE)
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
