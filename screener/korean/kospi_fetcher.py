"""
코스피 종목 리스트 수집 모듈
- pykrx 라이브러리 또는 KRX 웹에서 종목 리스트 가져오기
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class KospiListFetcher:
    """코스피 종목 리스트 수집기"""

    CACHE_FILE = "data/korean/kospi_list.csv"
    MASTER_FILE = "data/korean/kospi_master.csv"  # 수동 관리 종목 리스트
    CACHE_DAYS = 7  # 캐시 유효 기간 (일)

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache

    def get_kospi_symbols(self, refresh: bool = False) -> List[Dict]:
        """
        코스피 종목 리스트 반환

        Args:
            refresh: True면 캐시 무시하고 새로 가져옴

        Returns:
            [{'symbol': '005930.KS', 'code': '005930', 'name': '삼성전자', 'sector': '전기전자'}, ...]
        """
        # 캐시 확인
        if self.use_cache and not refresh:
            cached = self._load_cache()
            if cached is not None:
                logger.info(f"캐시에서 {len(cached)}개 종목 로드")
                return cached

        # 새로 가져오기
        symbols = self._fetch_from_pykrx()

        if symbols:
            self._save_cache(symbols)
            logger.info(f"코스피 {len(symbols)}개 종목 수집 완료")

        return symbols

    def _fetch_from_krx(self) -> List[Dict]:
        """KRX에서 코스피 종목 리스트 가져오기"""
        try:
            import requests

            # KRX 정보데이터시스템 API
            url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101'
            }
            params = {
                'bld': 'dbms/MDC/STAT/standard/MDCSTAT01901',
                'locale': 'ko_KR',
                'mktId': 'STK',  # STK=코스피, KSQ=코스닥
                'share': '1',
                'csvxls_is498': 'false',
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            items = data.get('OutBlock_1', [])

            if not items:
                logger.warning("KRX에서 데이터를 가져오지 못함")
                return self._fetch_fallback()

            symbols = []
            for item in items:
                code = item.get('ISU_SRT_CD', '')
                name = item.get('ISU_ABBRV', '')
                sector = item.get('IDX_IND_NM', '')

                if code and name:
                    symbols.append({
                        'symbol': f"{code}.KS",
                        'code': code,
                        'name': name,
                        'sector': sector
                    })

            logger.info(f"KRX에서 {len(symbols)}개 종목 수집")
            return symbols if symbols else self._fetch_fallback()

        except Exception as e:
            logger.warning(f"KRX 조회 실패: {e}")
            return self._fetch_fallback()

    def _fetch_from_pykrx(self) -> List[Dict]:
        """pykrx에서 코스피 종목 리스트 가져오기"""
        try:
            from pykrx import stock

            # 오늘 또는 최근 거래일 기준
            today = datetime.now().strftime("%Y%m%d")
            tickers = stock.get_market_ticker_list(today, market="KOSPI")

            if not tickers:
                logger.warning("pykrx에서 종목 리스트 가져오기 실패")
                return self._fetch_from_krx()

            symbols = []
            for ticker in tickers:
                name = stock.get_market_ticker_name(ticker)
                symbols.append({
                    'symbol': f"{ticker}.KS",
                    'code': ticker,
                    'name': name,
                    'sector': ''
                })

            return symbols if symbols else self._fetch_from_krx()

        except ImportError:
            logger.warning("pykrx가 설치되지 않음")
            return self._fetch_from_krx()
        except Exception as e:
            logger.warning(f"pykrx 조회 실패: {e}")
            return self._fetch_from_krx()

    def _fetch_fallback(self) -> List[Dict]:
        """
        대체 방법: 마스터 파일에서 종목 리스트 로드
        data/korean/kospi_master.csv 파일을 수정하여 종목 관리
        """
        master_path = Path(self.MASTER_FILE)

        if not master_path.exists():
            logger.error(f"마스터 파일이 없습니다: {master_path}")
            return []

        try:
            df = pd.read_csv(master_path, dtype={'code': str})
            symbols = []

            for _, row in df.iterrows():
                code = str(row['code']).zfill(6)  # 6자리로 패딩
                symbols.append({
                    'symbol': f"{code}.KS",
                    'code': code,
                    'name': row['name'],
                    'sector': row.get('sector', '')
                })

            logger.info(f"마스터 파일에서 {len(symbols)}개 종목 로드: {master_path}")
            return symbols

        except Exception as e:
            logger.error(f"마스터 파일 로드 실패: {e}")
            return []

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
            df.to_csv(cache_path, index=False, encoding='utf-8-sig')
            logger.info(f"캐시 저장: {cache_path}")
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {e}")

    def get_kosdaq_symbols(self, refresh: bool = False) -> List[Dict]:
        """코스닥 종목 리스트 (추후 구현)"""
        try:
            from pykrx import stock

            today = datetime.now().strftime("%Y%m%d")
            tickers = stock.get_market_ticker_list(today, market="KOSDAQ")

            symbols = []
            for ticker in tickers:
                name = stock.get_market_ticker_name(ticker)
                symbols.append({
                    'symbol': f"{ticker}.KQ",
                    'code': ticker,
                    'name': name,
                    'sector': ''
                })

            return symbols
        except ImportError:
            logger.warning("pykrx가 설치되지 않음")
            return []
        except Exception as e:
            logger.error(f"코스닥 조회 실패: {e}")
            return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    fetcher = KospiListFetcher()
    symbols = fetcher.get_kospi_symbols()

    print(f"\n총 {len(symbols)}개 종목")
    print("\n상위 10개:")
    for s in symbols[:10]:
        print(f"  {s['symbol']} - {s['name']} ({s['sector']})")
