"""
Stock Screener
조건 기반 종목 스크리닝

Usage:
    from screener.stock_screener import StockScreener
    from screener.conditions import (
        MinPriceCondition, MATouchCondition, RSIOversoldCondition, AndCondition
    )

    # 기본 사용
    screener = StockScreener()
    screener.add_condition(MinPriceCondition(5000))
    screener.add_condition(MATouchCondition(160))
    results = screener.run(universe="KOSPI")

    # 복합 조건
    condition = AndCondition([
        MinPriceCondition(5000),
        MATouchCondition(160),
        RSIOversoldCondition(30)
    ])
    screener = StockScreener(conditions=[condition])
    results = screener.run(universe="KOSPI")
"""

from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import time
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from pykrx import stock as pykrx_stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

from .conditions.base import BaseCondition, ConditionResult, PairsCondition
from data_sources.market.kr_market import KospiListFetcher

try:
    from utils.data_cache import OHLCVCache, get_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


@dataclass
class ScreeningResult:
    """스크리닝 결과"""
    ticker: str
    name: str
    matched: bool
    condition_results: List[ConditionResult]
    current_price: Optional[float] = None
    volume: Optional[int] = None
    change_pct: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def all_conditions_matched(self) -> bool:
        """모든 조건 충족 여부"""
        return all(r.matched for r in self.condition_results)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "matched": self.matched,
            "current_price": self.current_price,
            "volume": self.volume,
            "change_pct": self.change_pct,
            "conditions": [
                {
                    "name": r.condition_name,
                    "matched": r.matched,
                    "details": r.details
                }
                for r in self.condition_results
            ],
            "timestamp": self.timestamp.isoformat()
        }


class StockScreener:
    """조건 기반 종목 스크리너"""

    # KOSPI/KOSDAQ 대표 종목 (확장 가능)
    UNIVERSE_KOSPI = [
        # 대형주
        "005930.KS",  # 삼성전자
        "000660.KS",  # SK하이닉스
        "035420.KS",  # NAVER
        "005380.KS",  # 현대차
        "051910.KS",  # LG화학
        "006400.KS",  # 삼성SDI
        "035720.KS",  # 카카오
        "000270.KS",  # 기아
        "105560.KS",  # KB금융
        "055550.KS",  # 신한지주
        # 중형주
        "034730.KS",  # SK
        "003550.KS",  # LG
        "066570.KS",  # LG전자
        "012330.KS",  # 현대모비스
        "096770.KS",  # SK이노베이션
        "017670.KS",  # SK텔레콤
        "032830.KS",  # 삼성생명
        "086790.KS",  # 하나금융지주
        "138040.KS",  # 메리츠금융지주
        "030200.KS",  # KT
        # 추가
        "207940.KS",  # 삼성바이오로직스
        "068270.KS",  # 셀트리온
        "028260.KS",  # 삼성물산
        "036570.KS",  # NCsoft
        "003670.KS",  # 포스코퓨처엠
        "009150.KS",  # 삼성전기
        "018260.KS",  # 삼성에스디에스
        "010130.KS",  # 고려아연
        "024110.KS",  # 기업은행
        "011200.KS",  # HMM
        "047050.KS",  # 포스코인터내셔널
        "064350.KS",  # 현대로템
        "079550.KS",  # LIG넥스원
        "009540.KS",  # HD한국조선해양
        "329180.KS",  # HD현대중공업
    ]

    UNIVERSE_KOSDAQ = [
        "247540.KQ",  # 에코프로비엠
        "086520.KQ",  # 에코프로
        "091990.KQ",  # 셀트리온헬스케어
        "196170.KQ",  # 알테오젠
        "039030.KQ",  # 이오테크닉스
        "403870.KQ",  # HPSP
        "357780.KQ",  # 솔브레인
        "145020.KQ",  # 휴젤
        "005290.KQ",  # 동진쎄미켐
        "067160.KQ",  # 아프리카TV
        "293490.KQ",  # 카카오게임즈
        "214150.KQ",  # 클래시스
        "263750.KQ",  # 펄어비스
        "035900.KQ",  # JYP Ent.
        "352820.KQ",  # 하이브
    ]

    def __init__(
        self,
        conditions: Optional[List[BaseCondition]] = None,
        max_workers: int = 5,
        use_full_universe: bool = True,
        request_delay: float = 0.2,
        use_cache: bool = True,
        stock_names: Optional[Dict[str, str]] = None,
        reference_date: Optional[date] = None,
    ):
        """
        Args:
            conditions: 초기 조건 목록
            max_workers: 병렬 처리 워커 수 (yfinance rate limit 고려해 기본 5)
            use_full_universe: True면 pykrx로 전체 종목 가져옴, False면 하드코딩 목록 사용
            request_delay: API 요청 간 딜레이 (초)
            use_cache: 데이터 캐시 사용 여부 (기본 True)
            stock_names: Pre-fetched {ticker: name} mapping to avoid
                         per-stock yfinance info calls (N+1 problem).
            reference_date: Reference date for screening (defaults to today).
                            Data is truncated at this date.
        """
        self.conditions: List[BaseCondition] = conditions or []
        self.max_workers = max_workers
        self.use_full_universe = use_full_universe
        self.request_delay = request_delay
        self.use_cache = use_cache and CACHE_AVAILABLE
        self._kospi_fetcher = KospiListFetcher() if use_full_universe else None
        self._cache = get_cache() if self.use_cache else None
        self._stock_names: Dict[str, str] = stock_names or {}
        self._korean_names: Optional[Dict[str, str]] = None  # 한국어 종목명 캐시
        self.reference_date: Optional[date] = reference_date

    def add_condition(self, condition: BaseCondition) -> "StockScreener":
        """조건 추가 (체이닝 지원)"""
        self.conditions.append(condition)
        return self

    def clear_conditions(self) -> "StockScreener":
        """조건 초기화"""
        self.conditions = []
        return self

    def get_universe(self, universe: str) -> List[str]:
        """유니버스 종목 목록 반환"""
        universe_upper = universe.upper()

        # 전체 유니버스 모드 (pykrx 사용)
        if self.use_full_universe and self._kospi_fetcher:
            if universe_upper == "KOSPI":
                symbols = self._kospi_fetcher.get_kospi_symbols()
                return [s['symbol'] for s in symbols]
            elif universe_upper == "KOSDAQ":
                symbols = self._kospi_fetcher.get_kosdaq_symbols()
                return [s['symbol'] for s in symbols]
            elif universe_upper == "ALL":
                kospi = self._kospi_fetcher.get_kospi_symbols()
                kosdaq = self._kospi_fetcher.get_kosdaq_symbols()
                return [s['symbol'] for s in kospi] + [s['symbol'] for s in kosdaq]

        # 하드코딩 목록 사용 (fallback)
        if universe_upper == "KOSPI":
            return self.UNIVERSE_KOSPI
        elif universe_upper == "KOSDAQ":
            return self.UNIVERSE_KOSDAQ
        elif universe_upper == "ALL":
            return self.UNIVERSE_KOSPI + self.UNIVERSE_KOSDAQ
        else:
            raise ValueError(f"Unknown universe: {universe}. Use 'KOSPI', 'KOSDAQ', or 'ALL'")

    def _get_required_days(self) -> int:
        """필요한 데이터 일수 계산"""
        if not self.conditions:
            return 1
        return max(c.required_days for c in self.conditions)

    def _is_korean_stock(self, ticker: str) -> bool:
        """한국 주식인지 확인"""
        return ticker.endswith('.KS') or ticker.endswith('.KQ')

    def _fetch_data_pykrx(self, ticker: str, days: int) -> Optional[pd.DataFrame]:
        """pykrx로 한국 주식 데이터 가져오기"""
        if not PYKRX_AVAILABLE:
            return None

        try:
            # 티커에서 종목코드 추출 (005930.KS -> 005930)
            code = ticker.split('.')[0]

            # 최근 거래일 찾기
            end_date = self.reference_date or date.today()

            start_date = end_date - timedelta(days=days * 2)

            # pykrx로 데이터 가져오기
            data = pykrx_stock.get_market_ohlcv_by_date(
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                code
            )

            if data.empty:
                return None

            # 컬럼명 영어로 변환
            data.columns = ['open', 'high', 'low', 'close', 'volume']
            return data

        except Exception as e:
            # pykrx 실패 시 yfinance로 폴백
            return None

    def _fetch_data(self, ticker: str, days: int) -> Optional[pd.DataFrame]:
        """종목 데이터 가져오기 (캐시 사용)"""
        # 캐시 사용 가능하면 캐시에서 가져오기
        if self._cache is not None:
            data = self._cache.get(ticker, days=days)
            if data is not None and not data.empty:
                # 캐시 데이터 컬럼 확인 및 정리
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                if all(col in data.columns for col in required_cols):
                    return data[required_cols]

        # 캐시 없거나 실패 시 직접 가져오기
        # 한국 주식이면 pykrx 먼저 시도
        if self._is_korean_stock(ticker) and PYKRX_AVAILABLE:
            data = self._fetch_data_pykrx(ticker, days)
            if data is not None and not data.empty:
                return data

        # pykrx 실패 또는 해외 주식이면 yfinance 사용
        try:
            # Rate limit 방지를 위한 딜레이
            time.sleep(self.request_delay)

            stock = yf.Ticker(ticker)
            # 여유있게 데이터 가져오기 (주말/휴장일 고려)
            if self.reference_date:
                end_dt = self.reference_date
                start_dt = end_dt - timedelta(days=days * 2)
                # yfinance `end` is exclusive, so add 1 day to include the reference date
                data = stock.history(
                    start=start_dt.isoformat(),
                    end=(end_dt + timedelta(days=1)).isoformat(),
                )
            else:
                data = stock.history(period=f"{days * 2}d")
            if data.empty:
                return None

            # 컬럼명 소문자로 통일
            data.columns = [c.lower() for c in data.columns]
            return data
        except Exception as e:
            print(f"  ⚠️ {ticker} 데이터 로드 실패: {e}")
            return None

    def _load_korean_names(self) -> Dict[str, str]:
        """한국어 종목명 로드 (캐시)"""
        if self._korean_names is not None:
            return self._korean_names

        self._korean_names = {}
        from pathlib import Path

        # KOSPI/KOSDAQ CSV 파일 경로
        csv_files = [
            Path(__file__).parent.parent / "data" / "korean" / "kospi_list.csv",
            Path(__file__).parent.parent / "data" / "korean" / "kosdaq_list.csv",
        ]

        for csv_path in csv_files:
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path)
                    # symbol -> name 매핑 (예: 005930.KS -> 삼성전자)
                    if 'symbol' in df.columns and 'name' in df.columns:
                        for _, row in df.iterrows():
                            self._korean_names[row['symbol']] = row['name']
                except Exception:
                    pass

        return self._korean_names

    def _get_stock_name(self, ticker: str) -> str:
        """Get stock name with priority: injected > CSV > yfinance.

        Resolution order:
            1. self._stock_names (injected at construction time)
            2. Korean CSV names for .KS/.KQ tickers
            3. yf.Ticker().info as LAST RESORT
        """
        # 1. Injected names (highest priority)
        if ticker in self._stock_names:
            return self._stock_names[ticker]

        # 2. Korean CSV names for .KS/.KQ stocks
        if self._is_korean_stock(ticker):
            korean_names = self._load_korean_names()
            if ticker in korean_names:
                return korean_names[ticker]

        # 3. yfinance as last resort
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info.get("shortName", info.get("longName", ticker))
        except Exception:
            return ticker

    def _fetch_companion_data(self, ticker2: str, days: int) -> Optional[pd.DataFrame]:
        """Fetch companion ticker data for pairs conditions (with caching)."""
        if not hasattr(self, '_companion_cache'):
            self._companion_cache: Dict[tuple, Optional[pd.DataFrame]] = {}
        cache_key = (ticker2, days)
        if cache_key not in self._companion_cache:
            self._companion_cache[cache_key] = self._fetch_data(ticker2, days)
        return self._companion_cache[cache_key]

    def _evaluate_stock(self, ticker: str, data: pd.DataFrame) -> ScreeningResult:
        """단일 종목 평가 (pairs 조건 포함)"""
        results = []
        all_matched = True
        required_days = self._get_required_days()

        for condition in self.conditions:
            if isinstance(condition, PairsCondition):
                ticker2 = condition.ticker2
                if not ticker2:
                    result = ConditionResult(
                        matched=False,
                        condition_name=condition.name,
                        details={"error": "ticker2 not specified"},
                    )
                else:
                    data2 = self._fetch_companion_data(ticker2, required_days)
                    if data2 is None or data2.empty:
                        result = ConditionResult(
                            matched=False,
                            condition_name=condition.name,
                            details={"error": f"Failed to fetch data for {ticker2}"},
                        )
                    else:
                        result = condition.evaluate_pair(ticker, data, ticker2, data2)
            else:
                result = condition.evaluate(ticker, data)
            results.append(result)
            if not result.matched:
                all_matched = False

        current_price = float(data['close'].iloc[-1]) if not data.empty else None
        volume = int(data['volume'].iloc[-1]) if not data.empty else None

        change_pct: Optional[float] = None
        if len(data) >= 2:
            prev_close = float(data['close'].iloc[-2])
            if prev_close > 0:
                change_pct = ((current_price - prev_close) / prev_close) * 100

        name = self._get_stock_name(ticker)

        return ScreeningResult(
            ticker=ticker,
            name=name,
            matched=all_matched,
            condition_results=results,
            current_price=current_price,
            volume=volume,
            change_pct=change_pct,
        )

    def run(
        self,
        universe: str = "KOSPI",
        tickers: Optional[List[str]] = None,
        show_progress: bool = True,
        return_all: bool = False,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> List[ScreeningResult]:
        """
        스크리닝 실행

        Args:
            universe: 유니버스 ('KOSPI', 'KOSDAQ', 'ALL')
            tickers: 직접 지정한 종목 목록 (universe 대신 사용)
            show_progress: 진행상황 표시
            return_all: True면 모든 결과 반환, False면 매칭된 결과만 반환

        Returns:
            매칭된 종목의 ScreeningResult 목록 (return_all=True면 전체)
        """
        if not self.conditions:
            raise ValueError("조건이 설정되지 않았습니다. add_condition()으로 조건을 추가하세요.")

        # Reset companion data cache for fresh run
        self._companion_cache: Dict[tuple, Optional[pd.DataFrame]] = {}

        # 종목 목록 결정
        if tickers:
            target_tickers = tickers
        else:
            target_tickers = self.get_universe(universe)

        if show_progress:
            print(f"\n{'='*60}")
            print(f"📊 스크리닝 시작")
            print(f"{'='*60}")
            print(f"종목 수: {len(target_tickers)}")
            print(f"조건 수: {len(self.conditions)}")
            for c in self.conditions:
                print(f"  - {c.name}")
            print(f"{'='*60}\n")

        required_days = self._get_required_days()
        results: List[ScreeningResult] = []
        matched_count = 0

        def process_ticker(ticker: str) -> Optional[ScreeningResult]:
            data = self._fetch_data(ticker, required_days)
            if data is None or len(data) < required_days // 2:
                return None
            return self._evaluate_stock(ticker, data)

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_ticker, t): t for t in target_tickers}

            for i, future in enumerate(as_completed(futures), 1):
                ticker = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        if result.matched:
                            matched_count += 1
                            if show_progress:
                                print(f"  ✅ {ticker} ({result.name}) - 매칭!")
                except Exception as e:
                    if show_progress:
                        print(f"  ❌ {ticker} 처리 오류: {e}")

                if show_progress and i % 10 == 0:
                    print(f"  진행: {i}/{len(target_tickers)}")

                if progress_callback is not None:
                    try:
                        progress_callback(i, len(target_tickers), matched_count)
                    except Exception:
                        pass

        if show_progress:
            print(f"\n{'='*60}")
            print(f"📊 스크리닝 완료")
            print(f"{'='*60}")
            print(f"총 종목: {len(target_tickers)}")
            print(f"처리 완료: {len(results)}")
            print(f"매칭: {matched_count}")
            print(f"{'='*60}\n")

        # return_all이면 전체, 아니면 매칭된 결과만 반환
        return results if return_all else [r for r in results if r.matched]

    def run_single(self, ticker: str) -> ScreeningResult:
        """단일 종목 스크리닝"""
        if not self.conditions:
            raise ValueError("조건이 설정되지 않았습니다.")

        required_days = self._get_required_days()
        data = self._fetch_data(ticker, required_days)

        if data is None:
            raise ValueError(f"{ticker} 데이터를 가져올 수 없습니다.")

        return self._evaluate_stock(ticker, data)

    def to_dataframe(self, results: List[ScreeningResult]) -> pd.DataFrame:
        """결과를 DataFrame으로 변환"""
        rows = []
        for r in results:
            row = {
                "ticker": r.ticker,
                "name": r.name,
                "matched": r.matched,
                "current_price": r.current_price,
                "volume": r.volume,
            }
            # 각 조건 결과 추가
            for cr in r.condition_results:
                row[f"{cr.condition_name}_matched"] = cr.matched
                # 주요 세부 정보 추가
                for k, v in cr.details.items():
                    if k != "error":
                        row[f"{cr.condition_name}_{k}"] = v
            rows.append(row)

        return pd.DataFrame(rows)
