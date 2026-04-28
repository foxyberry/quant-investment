"""
Canonical location. Moved from screener/sector_fetcher.py.

한국 주식 시장 업종 분류 수집 모듈
- 마스터 CSV (KRX KIND 기반) 우선 사용
- pykrx를 보조 소스로 1회만 시도 (fail-fast)
- KRX KIND 직접 다운로드로 마스터 CSV 갱신 지원
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# KRX KIND KSIC → KRX market sector mapping
_KSIC_TO_KRX: Dict[str, str] = {
    "전자부품 제조업": "전기전자", "반도체 제조업": "전기전자",
    "컴퓨터 및 주변장치 제조업": "전기전자", "통신 및 방송 장비 제조업": "전기전자",
    "영상 및 음향기기 제조업": "전기전자", "절연선 및 케이블 제조업": "전기전자",
    "전구 및 조명장치 제조업": "전기전자", "가전제품 제조업": "전기전자",
    "가정용 기기 제조업": "전기전자", "전지 제조업": "전기전자",
    "기타 전기장비 제조업": "전기전자",
    "전동기, 발전기 및 전기 변환·공급·제어 장치 제조업": "전기전자",
    "전동기, 발전기 및 전기 변환 · 공급 · 제어 장치 제조업": "전기전자",
    "마그네틱 및 광학 매체 제조업": "전기전자",
    "일차전지 및 축전지 제조업": "전기전자",
    "일차전지 및 이차전지 제조업": "전기전자",
    "의약품 제조업": "의약품", "기초 의약물질 제조업": "의약품",
    "기초 의약물질 및 생물학적 제제 제조업": "의약품",
    "의료용품 및 기타 의약 관련제품 제조업": "의약품",
    "의료용 기기 제조업": "의약품",
    "사진장비 및 광학기기 제조업": "의약품",
    "측정, 시험, 항해, 제어 및 기타 정밀기기 제조업; 광학기기 제외": "의약품",
    "기초 화학물질 제조업": "화학", "합성고무 및 플라스틱 물질 제조업": "화학",
    "기타 화학제품 제조업": "화학", "합성수지 및 기타 플라스틱물질 제조업": "화학",
    "플라스틱제품 제조업": "화학", "화학섬유 제조업": "화학",
    "비누, 세정제, 광택제 및 향료 제조업": "화학",
    "도료, 인쇄잉크 및 유사제품 제조업": "화학",
    "석유 정제품 제조업": "화학", "코크스 및 연탄 제조업": "화학",
    "비료, 농약 및 살균, 살충제 제조업": "화학",
    "비료 및 질소화합물 제조업": "화학", "농약 제조업": "화학",
    "일반 목적용 기계 제조업": "기계", "특수 목적용 기계 제조업": "기계",
    "무기 및 총포탄 제조업": "기계",
    "1차 철강 제조업": "철강금속", "1차 비철금속 제조업": "철강금속",
    "금속 주조업": "철강금속", "철강 원료 재생업": "철강금속",
    "구조용 금속제품, 탱크 및 증기발생기 제조업": "철강금속",
    "기타 금속 가공제품 제조업": "철강금속",
    "건물 건설업": "건설업", "토목 건설업": "건설업",
    "건물설비 설치 공사업": "건설업",
    "기반조성 및 시설물 축조관련 전문공사업": "건설업",
    "실내건축 및 건축마무리 공사업": "건설업", "전기 및 통신 공사업": "건설업",
    "도로 화물 운송업": "운수창고", "해상 운송업": "운수창고",
    "항공 여객 운송업": "운수창고",
    "항공 화물 운송업 및 우주 운송업": "운수창고",
    "기타 운송관련 서비스업": "운수창고", "창고 및 운송관련 서비스업": "운수창고",
    "육상 여객 운송업": "운수창고", "수상 운송업": "운수창고",
    "항공 운송업": "운수창고", "파이프라인 운송업": "운수창고",
    "보관 및 창고업": "운수창고",
    "종합 소매업": "유통업", "상품 종합 도매업": "유통업",
    "기타 전문 도매업": "유통업", "생활용품 도매업": "유통업",
    "기계장비 및 관련 물품 도매업": "유통업",
    "산업용 농·축산물 및 섬유원료 도매업": "유통업",
    "산업용 농·축산물 및 동·식물 도매업": "유통업",
    "건축자재, 철물 및 난방장치 도매업": "유통업",
    "음·식료품 및 담배 도매업": "유통업",
    "가전제품 및 정보통신장비 소매업": "유통업", "연료 소매업": "유통업",
    "통신 판매업": "유통업", "전자상거래 소매업": "유통업",
    "무점포 소매업": "유통업", "섬유, 의복, 신발 및 가죽제품 소매업": "유통업",
    "기타 상품 전문 소매업": "유통업", "기타 생활용품 소매업": "유통업",
    "음·식료품 및 담배 소매업": "유통업", "상품 중개업": "유통업",
    "자동차 부품 및 내장품 판매업": "유통업", "자동차 판매업": "유통업",
    "봉제의복 제조업": "섬유의복", "편조원단 및 편조제품 제조업": "섬유의복",
    "편조원단 제조업": "섬유의복", "편조의복 제조업": "섬유의복",
    "방적 및 가공사 제조업": "섬유의복", "직물직조 및 직물제품 제조업": "섬유의복",
    "섬유제품 염색, 정리 및 마무리 가공업": "섬유의복",
    "기타 섬유제품 제조업": "섬유의복",
    "가죽, 가방 및 유사제품 제조업": "섬유의복",
    "신발 및 신발 부분품 제조업": "섬유의복",
    "모피가공 및 모피제품 제조업": "섬유의복", "의복 액세서리 제조업": "섬유의복",
    "도축, 육류 가공 및 저장 처리업": "음식료품",
    "수산물 가공 및 저장 처리업": "음식료품",
    "과실, 채소 가공 및 저장 처리업": "음식료품",
    "동물성 및 식물성 유지 제조업": "음식료품",
    "동·식물성 유지 및 낙농제품 제조업": "음식료품",
    "낙농제품 및 식용빙과류 제조업": "음식료품",
    "곡물가공품, 전분 및 전분제품 제조업": "음식료품",
    "기타 식품 제조업": "음식료품", "사료 및 조제식품 제조업": "음식료품",
    "동물용 사료 및 조제식품 제조업": "음식료품",
    "설탕 및 과자류 제조업": "음식료품", "떡, 빵 및 과자류 제조업": "음식료품",
    "도시락 및 식사용 조리식품 제조업": "음식료품",
    "알코올음료 제조업": "음식료품", "비알코올음료 및 얼음 제조업": "음식료품",
    "담배 제조업": "음식료품",
    "펄프, 종이 및 판지 제조업": "종이목재",
    "골판지, 종이 상자 및 종이용기 제조업": "종이목재",
    "기타 종이 및 판지 제품 제조업": "종이목재",
    "제재 및 목재 가공업": "종이목재", "나무제품 제조업": "종이목재",
    "유리 및 유리제품 제조업": "비금속광물",
    "내화, 비내화 요업제품 제조업": "비금속광물",
    "시멘트, 석회, 플라스터 및 그 제품 제조업": "비금속광물",
    "기타 비금속 광물제품 제조업": "비금속광물",
    "석재, 점토 및 유사 비금속광물 광업": "비금속광물",
    "소프트웨어 개발 및 공급업": "서비스업",
    "컴퓨터 프로그래밍, 시스템 통합 및 관리업": "서비스업",
    "정보서비스업": "서비스업", "기타 정보 서비스업": "서비스업",
    "자료처리, 호스팅, 포털 및 기타 인터넷 정보매개 서비스업": "서비스업",
    "영화, 비디오물, 방송프로그램 제작 및 배급업": "서비스업",
    "영상·오디오물 제공 서비스업": "서비스업",
    "오디오물 출판 및 원판 녹음업": "서비스업",
    "오락, 문화 및 운동관련 서비스업": "서비스업",
    "전문 서비스업": "서비스업", "기타 전문 서비스업": "서비스업",
    "건축기술, 엔지니어링 및 관련 기술 서비스업": "서비스업",
    "자연과학 및 공학 연구개발업": "서비스업", "연구개발업": "서비스업",
    "기타 전문, 과학 및 기술 서비스업": "서비스업",
    "그외 기타 전문, 과학 및 기술 서비스업": "서비스업",
    "기타 과학기술 서비스업": "서비스업",
    "광고업": "서비스업", "전문디자인업": "서비스업",
    "시장조사 및 여론조사업": "서비스업",
    "사업지원 서비스업": "서비스업", "기타 사업지원 서비스업": "서비스업",
    "사업시설 관리 및 조경 서비스업": "서비스업",
    "사업시설 유지·관리 서비스업": "서비스업",
    "인력공급 및 고용알선업": "서비스업", "경비, 경호 및 탐정업": "서비스업",
    "여행사 및 기타 여행보조 서비스업": "서비스업",
    "교육 서비스업": "서비스업", "교육지원 서비스업": "서비스업",
    "기타 교육기관": "서비스업", "일반 교습 학원": "서비스업",
    "초등 교육기관": "서비스업",
    "수리업": "서비스업", "개인 및 가정용품 수리업": "서비스업",
    "그외 기타 개인 서비스업": "서비스업",
    "음식점업": "서비스업", "숙박업": "서비스업",
    "일반 및 생활 숙박시설 운영업": "서비스업",
    "출판업": "서비스업", "서적, 잡지 및 기타 인쇄물 출판업": "서비스업",
    "인쇄 및 기록매체 복제업": "서비스업", "인쇄 및 인쇄관련 산업": "서비스업",
    "기록매체 복제업": "서비스업", "수의업": "서비스업",
    "폐기물 수집, 운반, 처리 및 원료 재생업": "서비스업",
    "폐기물 처리업": "서비스업", "해체, 선별 및 원료 재생업": "서비스업",
    "환경 정화 및 복원업": "서비스업",
    "임대업": "서비스업", "개인 및 가정용품 임대업": "서비스업",
    "산업용 기계 및 장비 임대업": "서비스업", "운송장비 임대업": "서비스업",
    "부동산업": "서비스업", "부동산 임대 및 공급업": "서비스업",
    "부동산 관련 서비스업": "서비스업", "스포츠 서비스업": "서비스업",
    "창작 및 예술관련 서비스업": "서비스업",
    "유원지 및 기타 오락관련 서비스업": "서비스업",
    "텔레비전 방송업": "서비스업",
    "회사 본부 및 경영 컨설팅 서비스업": "서비스업",
    "전기 통신업": "통신업", "기타 정보 통신업": "통신업",
    "전기업": "전기가스업", "가스 제조 및 배관공급업": "전기가스업",
    "증기, 냉·온수 및 공기 조절 공급업": "전기가스업",
    "증기, 냉·온수 및 공기조절 공급업": "전기가스업",
    "연료용 가스 제조 및 배관공급업": "전기가스업", "수도사업": "전기가스업",
    "은행 및 저축기관": "은행", "은행업": "은행",
    "투자기관": "증권", "금융 지원 서비스업": "증권",
    "보험 및 연금관련 서비스업": "보험", "보험업": "보험",
    "재 보험업": "보험",
    "기타 금융업": "기타금융", "여신금융업": "기타금융",
    "신탁업 및 집합투자업": "기타금융",
    "보험 및 연금 관련 서비스업": "기타금융",
    "자동차용 엔진 및 자동차 제조업": "운수장비",
    "자동차 신품 부품 제조업": "운수장비",
    "자동차 재제조 부품 제조업": "운수장비",
    "자동차 차체나 트레일러 제조업": "운수장비",
    "선박 및 보트 건조업": "운수장비",
    "항공기, 우주선 및 부품 제조업": "운수장비",
    "항공기,우주선 및 부품 제조업": "운수장비",
    "그외 기타 운송장비 제조업": "운수장비", "철도장비 제조업": "운수장비",
    "가구 제조업": "기타제조", "귀금속 및 장신용품 제조업": "기타제조",
    "악기 제조업": "기타제조", "운동 및 경기용구 제조업": "기타제조",
    "기타 제품 제조업": "기타제조", "그외 기타 제품 제조업": "기타제조",
    "고무제품 제조업": "기타제조",
    "금속 광업": "광업", "비금속광물 광업": "광업",
    "작물 재배업": "농업", "어로 어업": "농업",
}


class SectorFetcher:
    """한국 시장 업종 분류 수집기 (CSV 우선, pykrx 보조)"""

    CACHE_TTL = timedelta(days=7)
    SUPPORTED_MARKETS = {"KOSPI": ".KS", "KOSDAQ": ".KQ"}
    MASTER_FILES = {
        "KOSPI": "data/korean/kospi_master.csv",
        "KOSDAQ": "data/korean/kosdaq_master.csv",
    }
    KRX_KIND_MARKET_TYPES = {
        "KOSPI": "stockMkt",
        "KOSDAQ": "kosdaqMkt",
    }

    def __init__(self):
        self._cache: Dict[str, Tuple[datetime, pd.DataFrame]] = {}

    def get_sectors(self, market: str = "KOSPI") -> List[str]:
        normalized_market = self._normalize_market(market)
        df = self._get_market_classifications(normalized_market)
        if df.empty:
            return []
        return sorted(df["업종명"].dropna().astype(str).unique().tolist())

    def get_sector_tickers(self, market: str, sector_name: str) -> List[str]:
        normalized_market = self._normalize_market(market)
        df = self._get_market_classifications(normalized_market)
        if df.empty or not sector_name:
            return []
        suffix = self.SUPPORTED_MARKETS[normalized_market]
        filtered = df[df["업종명"] == sector_name]
        return sorted([f"{code}{suffix}" for code in filtered.index.tolist()])

    def get_sector_counts(self, market: str = "KOSPI") -> Dict[str, int]:
        normalized_market = self._normalize_market(market)
        df = self._get_market_classifications(normalized_market)
        if df.empty:
            return {}
        counts = df.groupby("업종명").size()
        return {str(name): int(count) for name, count in counts.items()}

    def get_all_sector_classifications(self, market: str = "KOSPI") -> Dict[str, str]:
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
        """캐시 확인 후 업종 데이터 반환 (CSV 우선 → pykrx 보조)"""
        cached = self._cache.get(market)
        if cached is not None:
            cached_at, cached_df = cached
            if datetime.now() - cached_at < self.CACHE_TTL:
                return cached_df.copy()

        # 1) Master CSV (primary — always available offline)
        df = self._fetch_from_master_csv(market)

        # 2) pykrx (secondary — single attempt, fail-fast)
        if df.empty:
            df = self._fetch_from_pykrx(market)

        if not df.empty:
            self._cache[market] = (datetime.now(), df.copy())
            logger.info(f"{market} 업종 데이터 {len(df)}건 캐시 저장 (TTL {self.CACHE_TTL})")
        return df

    def _fetch_from_pykrx(self, market: str) -> pd.DataFrame:
        """pykrx에서 업종 분류 데이터 조회 (1회만 시도, fail-fast)"""
        try:
            from pykrx import stock
        except ImportError:
            return pd.DataFrame()

        # Try today only; if KRX API is broken this avoids 12 noisy retries
        date_str = datetime.now().strftime("%Y%m%d")
        try:
            df = stock.get_market_sector_classifications(date_str, market=market)
            if df is None or df.empty:
                return pd.DataFrame()
            normalized_df = df.copy()
            normalized_df.index = normalized_df.index.astype(str).str.zfill(6)
            logger.info(f"{market} pykrx 업종 데이터 조회 성공: {date_str}, {len(normalized_df)}건")
            return normalized_df
        except Exception as e:
            logger.info(f"{market} pykrx 업종 조회 실패 (CSV 사용): {e}")
            return pd.DataFrame()

    def _fetch_from_master_csv(self, market: str) -> pd.DataFrame:
        """마스터 CSV에서 업종 분류 데이터 로드"""
        relative_path = self.MASTER_FILES.get(market)
        if not relative_path:
            return pd.DataFrame()

        master_path = Path(__file__).resolve().parent.parent.parent / relative_path
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
        normalized_market = (market or "").upper().strip()
        if normalized_market not in self.SUPPORTED_MARKETS:
            raise ValueError(f"지원하지 않는 시장입니다: {market}. KOSPI/KOSDAQ만 지원합니다.")
        return normalized_market

    @classmethod
    def refresh_master_csvs(cls) -> Dict[str, int]:
        """KRX KIND에서 최신 상장법인 목록을 다운로드하여 마스터 CSV 갱신"""
        try:
            import requests
            from io import BytesIO
        except ImportError:
            logger.error("requests 라이브러리가 필요합니다")
            return {}

        headers = {"User-Agent": "Mozilla/5.0"}
        counts: Dict[str, int] = {}

        for market, market_type in cls.KRX_KIND_MARKET_TYPES.items():
            try:
                url = (
                    "https://kind.krx.co.kr/corpgeneral/corpList.do"
                    f"?method=download&searchType=13&marketType={market_type}"
                )
                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()

                raw_df = pd.read_html(BytesIO(resp.content), encoding="euc-kr")[0]
                result = pd.DataFrame({
                    "code": raw_df["종목코드"].astype(str).str.zfill(6),
                    "name": raw_df["회사명"],
                    "sector": raw_df["업종"].map(
                        lambda x: _KSIC_TO_KRX.get(str(x), "기타")
                    ),
                })
                result = result[result["code"].str.match(r"^\d{6}$")]
                result = result.drop_duplicates(subset=["code"], keep="first")
                result = result.sort_values("code").reset_index(drop=True)

                csv_path = Path(__file__).resolve().parent.parent.parent / cls.MASTER_FILES[market]
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                result.to_csv(csv_path, index=False, encoding="utf-8")

                counts[market] = len(result)
                logger.info(f"{market} 마스터 CSV 갱신 완료: {len(result)}건")
            except Exception as e:
                logger.error(f"{market} 마스터 CSV 갱신 실패: {e}")

        return counts


_sector_fetcher: Optional[SectorFetcher] = None


def get_sector_fetcher() -> SectorFetcher:
    """SectorFetcher 싱글턴 반환"""
    global _sector_fetcher
    if _sector_fetcher is None:
        _sector_fetcher = SectorFetcher()
    return _sector_fetcher


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # --refresh flag: update master CSVs from KRX KIND
    import sys
    if "--refresh" in sys.argv:
        print("Refreshing master CSVs from KRX KIND...")
        counts = SectorFetcher.refresh_master_csvs()
        for m, c in counts.items():
            print(f"  {m}: {c} entries")
        print("Done.")
        sys.exit(0)

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
