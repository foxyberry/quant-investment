"""
한국 주식 시장 업종 분류 수집 모듈
- pykrx를 이용해 코스피/코스닥 업종 정보를 조회
- pykrx 실패 시 마스터 CSV로 폴백
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class SectorFetcher:
    """한국 시장 업종 분류 수집기"""

    CACHE_TTL = timedelta(days=1)
    SUPPORTED_MARKETS = {"KOSPI": ".KS", "KOSDAQ": ".KQ"}
    MASTER_FILES = {
        "KOSPI": "data/korean/kospi_master.csv",
        "KOSDAQ": "data/korean/kosdaq_master.csv",
    }

    def __init__(self):
        # {market: (fetched_at, dataframe)}
        self._cache: Dict[str, Tuple[datetime, pd.DataFrame]] = {}

    def get_sectors(self, market: str = "KOSPI") -> List[str]:
        """
        시장의 업종명 목록을 정렬하여 반환

        Args:
            market: KOSPI 또는 KOSDAQ

        Returns:
            정렬된 업종명 리스트
        """
        normalized_market = self._normalize_market(market)
        df = self._get_market_classifications(normalized_market)
        if df.empty:
            return []

        sectors = sorted(df["업종명"].dropna().astype(str).unique().tolist())
        return sectors

    def get_sector_tickers(self, market: str, sector_name: str) -> List[str]:
        """
        특정 업종에 속한 티커 목록 반환

        Args:
            market: KOSPI 또는 KOSDAQ
            sector_name: 업종명

        Returns:
            접미사(.KS/.KQ)가 포함된 티커 목록
        """
        normalized_market = self._normalize_market(market)
        df = self._get_market_classifications(normalized_market)
        if df.empty or not sector_name:
            return []

        suffix = self.SUPPORTED_MARKETS[normalized_market]
        filtered = df[df["업종명"] == sector_name]
        tickers = sorted([f"{code}{suffix}" for code in filtered.index.tolist()])
        return tickers

    def get_sector_counts(self, market: str = "KOSPI") -> Dict[str, int]:
        """
        시장의 업종별 종목 수를 한 번에 계산하여 반환

        Args:
            market: KOSPI 또는 KOSDAQ

        Returns:
            {업종명: 종목수} 딕셔너리
        """
        normalized_market = self._normalize_market(market)
        df = self._get_market_classifications(normalized_market)
        if df.empty:
            return {}

        counts = df.groupby("업종명").size()
        return {str(name): int(count) for name, count in counts.items()}

    def get_all_sector_classifications(self, market: str = "KOSPI") -> Dict[str, str]:
        """
        시장 전체 종목의 업종 매핑 반환

        Args:
            market: KOSPI 또는 KOSDAQ

        Returns:
            {티커(.KS/.KQ 포함): 업종명} 딕셔너리
        """
        normalized_market = self._normalize_market(market)
        df = self._get_market_classifications(normalized_market)
        if df.empty:
            return {}

        suffix = self.SUPPORTED_MARKETS[normalized_market]
        result: Dict[str, str] = {}
        for code, row in df.iterrows():
            sector_name = row.get("업종명")
            if pd.notna(sector_name):
                result[f"{code}{suffix}"] = str(sector_name)

        return result

    def _get_market_classifications(self, market: str) -> pd.DataFrame:
        """캐시 확인 후 업종 데이터 반환 (pykrx → 마스터 CSV 폴백)"""
        cached = self._cache.get(market)
        if cached is not None:
            cached_at, cached_df = cached
            if datetime.now() - cached_at < self.CACHE_TTL:
                logger.info(f"{market} 업종 데이터 캐시 사용")
                return cached_df.copy()

            logger.info(f"{market} 업종 데이터 캐시 만료")

        df = self._fetch_from_pykrx(market)
        if df.empty:
            df = self._fetch_from_master_csv(market)

        if not df.empty:
            self._cache[market] = (datetime.now(), df.copy())
            logger.info(f"{market} 업종 데이터 {len(df)}건 캐시 저장")
        return df

    def _fetch_from_pykrx(self, market: str) -> pd.DataFrame:
        """
        pykrx에서 업종 분류 데이터 조회
        - 오늘부터 최대 11일 전까지 역순 조회 (휴장일 대응)
        """
        try:
            from pykrx import stock
        except ImportError:
            logger.warning("pykrx가 설치되지 않음")
            return pd.DataFrame()

        for days_ago in range(0, 12):
            target_date = datetime.now() - timedelta(days=days_ago)
            date_str = target_date.strftime("%Y%m%d")

            try:
                df = stock.get_market_sector_classifications(date_str, market=market)
                if df is None or df.empty:
                    continue

                normalized_df = df.copy()
                normalized_df.index = normalized_df.index.astype(str).str.zfill(6)
                logger.info(f"{market} 업종 데이터 조회 성공: {date_str}, {len(normalized_df)}건")
                return normalized_df
            except Exception as e:
                logger.warning(f"{market} 업종 조회 실패 ({date_str}): {e}")

        logger.error(f"{market} 업종 데이터를 최근 11일 내에서 찾지 못함")
        return pd.DataFrame()

    def _fetch_from_master_csv(self, market: str) -> pd.DataFrame:
        """마스터 CSV에서 업종 분류 데이터 로드 (pykrx 실패 시 폴백)"""
        relative_path = self.MASTER_FILES.get(market)
        if not relative_path:
            return pd.DataFrame()

        master_path = Path(__file__).resolve().parent.parent / relative_path
        if not master_path.exists():
            logger.warning(f"마스터 파일 없음: {master_path}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(master_path, dtype={"code": str})
            if df.empty or "sector" not in df.columns:
                return pd.DataFrame()

            df = df.dropna(subset=["code", "sector"])
            df = df[df["code"].str.match(r"^\d{6}$")]
            df = df.drop_duplicates(subset=["code"], keep="last")

            result = pd.DataFrame(
                {"업종명": df["sector"].values},
                index=df["code"].str.zfill(6),
            )
            result = result[result["업종명"].notna() & (result["업종명"] != "")]
            logger.info(f"{market} 마스터 CSV에서 {len(result)}건 업종 데이터 로드")
            return result
        except Exception as e:
            logger.warning(f"마스터 CSV 업종 로드 실패: {e}")
            return pd.DataFrame()

    def _normalize_market(self, market: str) -> str:
        """지원 시장명 검증 및 정규화"""
        normalized_market = (market or "").upper().strip()
        if normalized_market not in self.SUPPORTED_MARKETS:
            raise ValueError(f"지원하지 않는 시장입니다: {market}. KOSPI/KOSDAQ만 지원합니다.")
        return normalized_market


_sector_fetcher: Optional[SectorFetcher] = None


def get_sector_fetcher() -> SectorFetcher:
    """SectorFetcher 싱글턴 반환"""
    global _sector_fetcher
    if _sector_fetcher is None:
        _sector_fetcher = SectorFetcher()
    return _sector_fetcher


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    fetcher = get_sector_fetcher()

    for market_name in ["KOSPI", "KOSDAQ"]:
        try:
            sectors = fetcher.get_sectors(market_name)
            print(f"\n[{market_name}] 업종 수: {len(sectors)}")
            print(f"상위 10개 업종: {sectors[:10]}")

            if sectors:
                first_sector = sectors[0]
                tickers = fetcher.get_sector_tickers(market_name, first_sector)
                print(f"'{first_sector}' 종목 수: {len(tickers)}")
                print(f"샘플 10개: {tickers[:10]}")
        except Exception as e:
            logger.error(f"{market_name} 테스트 실패: {e}")
