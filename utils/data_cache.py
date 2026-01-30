"""
OHLCV Data Cache Module
주가 데이터 캐싱 모듈

Usage:
    from utils.data_cache import OHLCVCache

    cache = OHLCVCache()

    # 데이터 가져오기 (캐시 자동 사용)
    data = cache.get('005930.KS', days=100)

    # 캐시 상태 확인
    cache.status()

    # 캐시 갱신
    cache.refresh('005930.KS')

    # 전체 캐시 삭제
    cache.clear()
"""

import os
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd

try:
    from pykrx import stock as pykrx_stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class OHLCVCache:
    """OHLCV 데이터 캐시 관리자"""

    DEFAULT_CACHE_DIR = "data/cache/ohlcv"
    DEFAULT_CACHE_DAYS = 730  # 2년치 데이터 유지
    STALE_HOURS = 18  # 18시간 이후 데이터는 갱신 필요 (장 마감 후)

    def __init__(
        self,
        cache_dir: str = None,
        cache_days: int = None,
        auto_refresh: bool = True
    ):
        """
        Args:
            cache_dir: 캐시 디렉토리 경로
            cache_days: 캐시할 데이터 기간 (일)
            auto_refresh: 오래된 캐시 자동 갱신 여부
        """
        self.cache_dir = Path(cache_dir or self.DEFAULT_CACHE_DIR)
        self.cache_days = cache_days or self.DEFAULT_CACHE_DAYS
        self.auto_refresh = auto_refresh

        # 캐시 디렉토리 생성
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 통계
        self._hits = 0
        self._misses = 0

    def _get_cache_path(self, ticker: str) -> Path:
        """캐시 파일 경로 반환"""
        # 티커에서 특수문자 제거
        safe_ticker = ticker.replace('.', '_').replace('/', '_')
        return self.cache_dir / f"{safe_ticker}.parquet"

    def _is_korean_stock(self, ticker: str) -> bool:
        """한국 주식인지 확인"""
        return ticker.endswith('.KS') or ticker.endswith('.KQ')

    def _get_latest_trading_date(self) -> date:
        """
        최신 거래일 반환
        시스템 날짜가 미래인 경우 고정된 날짜 반환
        """
        today = date.today()

        # 시스템 날짜가 2025년 이후면 고정 날짜 사용
        if today.year > 2025:
            return date(2025, 1, 24)

        # 주말이면 금요일로
        if today.weekday() == 5:  # Saturday
            return today - timedelta(days=1)
        elif today.weekday() == 6:  # Sunday
            return today - timedelta(days=2)

        return today

    def _is_cache_fresh(self, cache_path: Path, required_days: int) -> bool:
        """캐시가 신선한지 확인"""
        if not cache_path.exists():
            return False

        try:
            # 캐시 파일의 마지막 수정 시간
            mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            hours_old = (datetime.now() - mtime).total_seconds() / 3600

            # STALE_HOURS 이상 지났으면 갱신 필요
            if hours_old > self.STALE_HOURS:
                return False

            # 데이터 내용 확인
            data = pd.read_parquet(cache_path)
            if len(data) < required_days * 0.7:  # 70% 이상 데이터 필요
                return False

            return True

        except Exception as e:
            logger.warning(f"캐시 확인 실패: {e}")
            return False

    def _fetch_from_pykrx(self, ticker: str, days: int) -> Optional[pd.DataFrame]:
        """pykrx로 한국 주식 데이터 가져오기"""
        if not PYKRX_AVAILABLE:
            return None

        try:
            code = ticker.split('.')[0]
            end_date = self._get_latest_trading_date()
            start_date = end_date - timedelta(days=days)

            data = pykrx_stock.get_market_ohlcv_by_date(
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                code
            )

            if data.empty:
                return None

            # 컬럼명 영어로 변환
            data.columns = ['open', 'high', 'low', 'close', 'volume', 'change_pct']

            # 인덱스 정리
            data.index.name = 'date'
            data = data.reset_index()
            data['date'] = pd.to_datetime(data['date'])
            data = data.set_index('date')

            # 티커 컬럼 추가
            data['ticker'] = ticker

            return data

        except Exception as e:
            logger.warning(f"pykrx 데이터 로드 실패 ({ticker}): {e}")
            return None

    def _fetch_from_yfinance(self, ticker: str, days: int) -> Optional[pd.DataFrame]:
        """yfinance로 데이터 가져오기"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=f"{days}d")

            if data.empty:
                return None

            # 컬럼명 소문자로 통일
            data.columns = [c.lower() for c in data.columns]

            # 필요한 컬럼만 선택
            cols = ['open', 'high', 'low', 'close', 'volume']
            data = data[[c for c in cols if c in data.columns]]

            # 티커 컬럼 추가
            data['ticker'] = ticker

            return data

        except Exception as e:
            logger.warning(f"yfinance 데이터 로드 실패 ({ticker}): {e}")
            return None

    def _fetch_data(self, ticker: str, days: int) -> Optional[pd.DataFrame]:
        """데이터 가져오기 (pykrx 우선, yfinance 폴백)"""
        data = None

        # 한국 주식이면 pykrx 먼저
        if self._is_korean_stock(ticker) and PYKRX_AVAILABLE:
            data = self._fetch_from_pykrx(ticker, days)

        # pykrx 실패 또는 해외 주식이면 yfinance
        if data is None and YFINANCE_AVAILABLE:
            data = self._fetch_from_yfinance(ticker, days)

        return data

    def get(
        self,
        ticker: str,
        days: int = 100,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        OHLCV 데이터 가져오기 (캐시 사용)

        Args:
            ticker: 종목 코드 (예: '005930.KS', 'AAPL')
            days: 필요한 데이터 일수
            force_refresh: 캐시 무시하고 새로 가져오기

        Returns:
            OHLCV DataFrame 또는 None
        """
        cache_path = self._get_cache_path(ticker)

        # 캐시 확인 (강제 갱신 아닐 때)
        if not force_refresh and self._is_cache_fresh(cache_path, days):
            try:
                data = pd.read_parquet(cache_path)
                self._hits += 1
                logger.debug(f"캐시 히트: {ticker}")

                # 요청된 일수만큼만 반환
                if len(data) > days:
                    return data.tail(days)
                return data

            except Exception as e:
                logger.warning(f"캐시 읽기 실패 ({ticker}): {e}")

        # 캐시 미스 - 새로 가져오기
        self._misses += 1
        logger.debug(f"캐시 미스: {ticker}")

        # 캐시 기간만큼 데이터 가져오기
        fetch_days = max(days, self.cache_days)
        data = self._fetch_data(ticker, fetch_days)

        if data is not None and not data.empty:
            # 캐시 저장
            try:
                data.to_parquet(cache_path)
                logger.info(f"캐시 저장: {ticker} ({len(data)}행)")
            except Exception as e:
                logger.warning(f"캐시 저장 실패 ({ticker}): {e}")

            # 요청된 일수만큼만 반환
            if len(data) > days:
                return data.tail(days)

        return data

    def refresh(self, ticker: str) -> bool:
        """특정 종목 캐시 갱신"""
        cache_path = self._get_cache_path(ticker)

        # 기존 캐시 삭제
        if cache_path.exists():
            cache_path.unlink()

        # 새로 가져오기
        data = self.get(ticker, days=self.cache_days, force_refresh=True)
        return data is not None

    def refresh_all(self, tickers: List[str], show_progress: bool = True) -> Dict[str, bool]:
        """여러 종목 캐시 갱신"""
        results = {}
        total = len(tickers)

        for i, ticker in enumerate(tickers, 1):
            if show_progress:
                print(f"  갱신 중: {ticker} ({i}/{total})")

            results[ticker] = self.refresh(ticker)

        return results

    def prefetch(
        self,
        tickers: List[str],
        days: int = None,
        show_progress: bool = True
    ) -> Dict[str, bool]:
        """
        여러 종목 데이터 미리 가져오기
        이미 캐시된 종목은 건너뜀
        """
        days = days or self.cache_days
        results = {}
        total = len(tickers)
        cached = 0
        fetched = 0

        for i, ticker in enumerate(tickers, 1):
            cache_path = self._get_cache_path(ticker)

            if self._is_cache_fresh(cache_path, days):
                results[ticker] = True
                cached += 1
            else:
                if show_progress:
                    print(f"  가져오는 중: {ticker} ({i}/{total})")

                data = self.get(ticker, days=days)
                results[ticker] = data is not None
                if results[ticker]:
                    fetched += 1

        if show_progress:
            print(f"\n  완료: 캐시됨 {cached}, 새로 가져옴 {fetched}, 실패 {total - cached - fetched}")

        return results

    def clear(self, ticker: str = None) -> int:
        """
        캐시 삭제

        Args:
            ticker: 특정 종목만 삭제 (None이면 전체)

        Returns:
            삭제된 파일 수
        """
        if ticker:
            cache_path = self._get_cache_path(ticker)
            if cache_path.exists():
                cache_path.unlink()
                return 1
            return 0

        # 전체 삭제
        count = 0
        for f in self.cache_dir.glob("*.parquet"):
            f.unlink()
            count += 1

        return count

    def status(self) -> Dict[str, Any]:
        """캐시 상태 반환"""
        files = list(self.cache_dir.glob("*.parquet"))
        total_size = sum(f.stat().st_size for f in files)

        # 각 파일 정보
        file_info = []
        for f in files:
            stat = f.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime)
            hours_old = (datetime.now() - mtime).total_seconds() / 3600

            file_info.append({
                'ticker': f.stem.replace('_', '.'),
                'size_kb': stat.st_size / 1024,
                'modified': mtime.strftime('%Y-%m-%d %H:%M'),
                'hours_old': round(hours_old, 1),
                'fresh': hours_old < self.STALE_HOURS
            })

        return {
            'cache_dir': str(self.cache_dir),
            'total_files': len(files),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(self._hits / (self._hits + self._misses) * 100, 1) if (self._hits + self._misses) > 0 else 0,
            'files': sorted(file_info, key=lambda x: x['ticker'])
        }

    def print_status(self):
        """캐시 상태 출력"""
        status = self.status()

        print(f"\n{'='*60}")
        print(f"  OHLCV Cache Status")
        print(f"{'='*60}")
        print(f"  디렉토리: {status['cache_dir']}")
        print(f"  파일 수: {status['total_files']}")
        print(f"  총 크기: {status['total_size_mb']} MB")
        print(f"  히트율: {status['hit_rate']}% ({status['hits']} hits, {status['misses']} misses)")
        print(f"{'='*60}")

        if status['files']:
            print(f"\n  {'종목':<15} {'크기(KB)':<10} {'수정일시':<18} {'상태':<8}")
            print(f"  {'-'*55}")
            for f in status['files'][:20]:  # 최대 20개만 표시
                fresh_str = "Fresh" if f['fresh'] else f"Stale ({f['hours_old']}h)"
                print(f"  {f['ticker']:<15} {f['size_kb']:<10.1f} {f['modified']:<18} {fresh_str:<8}")

            if len(status['files']) > 20:
                print(f"  ... 외 {len(status['files']) - 20}개")

        print()


# 싱글톤 인스턴스
_default_cache = None


def get_cache() -> OHLCVCache:
    """기본 캐시 인스턴스 반환"""
    global _default_cache
    if _default_cache is None:
        _default_cache = OHLCVCache()
    return _default_cache
