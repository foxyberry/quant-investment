"""
이동평균선 기반 스크리너
- 60일선, 120일선 아래 종목 탐색
"""

import pandas as pd
import yfinance as yf
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class MovingAverageScreener:
    """이동평균선 기반 스크리너"""

    def __init__(
        self,
        short_ma: int = 60,
        long_ma: int = 120,
        min_volume: int = 100000,
        min_price: float = 1000,
        max_workers: int = 10,
        request_delay: float = 0.1
    ):
        """
        Args:
            short_ma: 단기 이동평균 기간 (기본 60일)
            long_ma: 장기 이동평균 기간 (기본 120일)
            min_volume: 최소 거래량 필터
            min_price: 최소 주가 필터
            max_workers: 병렬 처리 스레드 수
            request_delay: API 요청 간 대기 시간
        """
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.min_volume = min_volume
        self.min_price = min_price
        self.max_workers = max_workers
        self.request_delay = request_delay

    def analyze_symbol(self, symbol: str, name: str = "") -> Optional[Dict]:
        """
        단일 종목의 이동평균선 분석

        Args:
            symbol: 종목 심볼 (예: '005930.KS')
            name: 종목명

        Returns:
            분석 결과 딕셔너리 또는 None
        """
        try:
            # yf.Ticker 사용 (더 안정적인 API)
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1y", auto_adjust=True)

            if data.empty or len(data) < self.long_ma:
                logger.debug(f"{symbol}: 데이터 부족 ({len(data)}일)")
                return None

            # 현재가
            current_price = float(data['Close'].iloc[-1])

            # 최소 주가 필터
            if current_price < self.min_price:
                return None

            # 평균 거래량 (20일)
            avg_volume = float(data['Volume'].iloc[-20:].mean())
            if avg_volume < self.min_volume:
                return None

            # 이동평균 계산
            ma_short = float(data['Close'].iloc[-self.short_ma:].mean())
            ma_long = float(data['Close'].iloc[-self.long_ma:].mean())

            # 이동평균 대비 위치
            below_short = current_price < ma_short
            below_long = current_price < ma_long

            # 이동평균 대비 거리 (%)
            distance_short = ((current_price - ma_short) / ma_short) * 100
            distance_long = ((current_price - ma_long) / ma_long) * 100

            # 추가 지표
            # 52주 고가/저가
            high_52w = float(data['High'].max())
            low_52w = float(data['Low'].min())
            from_high_52w = ((current_price - high_52w) / high_52w) * 100
            from_low_52w = ((current_price - low_52w) / low_52w) * 100

            result = {
                'symbol': symbol,
                'code': symbol.replace('.KS', '').replace('.KQ', ''),
                'name': name,
                'current_price': current_price,
                f'ma_{self.short_ma}': ma_short,
                f'ma_{self.long_ma}': ma_long,
                f'below_{self.short_ma}': below_short,
                f'below_{self.long_ma}': below_long,
                f'distance_from_{self.short_ma}_pct': round(distance_short, 2),
                f'distance_from_{self.long_ma}_pct': round(distance_long, 2),
                'avg_volume_20d': int(avg_volume),
                'high_52w': high_52w,
                'low_52w': low_52w,
                'from_high_52w_pct': round(from_high_52w, 2),
                'from_low_52w_pct': round(from_low_52w, 2),
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
            }

            return result

        except Exception as e:
            logger.warning(f"{symbol} 분석 실패: {e}")
            return None

    def batch_screen(
        self,
        symbols: List[Dict],
        show_progress: bool = True
    ) -> List[Dict]:
        """
        여러 종목 일괄 스크리닝

        Args:
            symbols: [{'symbol': '005930.KS', 'name': '삼성전자'}, ...]
            show_progress: 진행상황 표시 여부

        Returns:
            분석 결과 리스트
        """
        results = []
        total = len(symbols)
        processed = 0

        logger.info(f"스크리닝 시작: {total}개 종목")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.analyze_symbol,
                    s['symbol'],
                    s.get('name', '')
                ): s for s in symbols
            }

            for future in as_completed(futures):
                processed += 1
                result = future.result()

                if result:
                    results.append(result)

                if show_progress and processed % 10 == 0:
                    logger.info(f"진행: {processed}/{total} ({len(results)}개 통과)")

                # API 부하 방지
                time.sleep(self.request_delay)

        logger.info(f"스크리닝 완료: {len(results)}/{total}개 종목 분석됨")
        return results

    def filter_below_ma(
        self,
        results: List[Dict],
        ma_type: str = 'short',
        sort_by_distance: bool = True
    ) -> List[Dict]:
        """
        이동평균선 아래 종목 필터링

        Args:
            results: batch_screen 결과
            ma_type: 'short' (60일), 'long' (120일), 'both' (둘 다)
            sort_by_distance: 거리순 정렬 여부

        Returns:
            필터링된 결과 리스트
        """
        if ma_type == 'short':
            key = f'below_{self.short_ma}'
            distance_key = f'distance_from_{self.short_ma}_pct'
        elif ma_type == 'long':
            key = f'below_{self.long_ma}'
            distance_key = f'distance_from_{self.long_ma}_pct'
        else:  # both
            filtered = [
                r for r in results
                if r.get(f'below_{self.short_ma}') or r.get(f'below_{self.long_ma}')
            ]
            if sort_by_distance:
                filtered.sort(key=lambda x: x.get(f'distance_from_{self.short_ma}_pct', 0))
            return filtered

        filtered = [r for r in results if r.get(key)]

        if sort_by_distance:
            filtered.sort(key=lambda x: x.get(distance_key, 0))

        return filtered

    def get_summary(self, results: List[Dict]) -> Dict:
        """
        스크리닝 결과 요약

        Args:
            results: batch_screen 결과

        Returns:
            요약 통계
        """
        if not results:
            return {'total': 0}

        below_short = sum(1 for r in results if r.get(f'below_{self.short_ma}'))
        below_long = sum(1 for r in results if r.get(f'below_{self.long_ma}'))
        below_both = sum(
            1 for r in results
            if r.get(f'below_{self.short_ma}') and r.get(f'below_{self.long_ma}')
        )

        return {
            'total': len(results),
            f'below_{self.short_ma}': below_short,
            f'below_{self.long_ma}': below_long,
            'below_both': below_both,
            f'above_{self.short_ma}': len(results) - below_short,
            f'above_{self.long_ma}': len(results) - below_long,
        }


class MultiMAScreener:
    """여러 이동평균선 기반 스크리너 (200일, 240일, 365일 등)"""

    def __init__(
        self,
        ma_periods: List[int] = None,
        touch_threshold: float = 2.0,
        min_volume: int = 100000,
        min_price: float = 1000,
        max_workers: int = 10,
        request_delay: float = 0.1
    ):
        """
        Args:
            ma_periods: 이동평균 기간 리스트 (기본: [60, 120, 200, 240, 365])
            touch_threshold: 터치 판정 기준 (±%, 기본 2%)
            min_volume: 최소 거래량 필터
            min_price: 최소 주가 필터
            max_workers: 병렬 처리 스레드 수
            request_delay: API 요청 간 대기 시간
        """
        self.ma_periods = ma_periods or [60, 120, 200, 240, 365]
        self.touch_threshold = touch_threshold
        self.min_volume = min_volume
        self.min_price = min_price
        self.max_workers = max_workers
        self.request_delay = request_delay
        self.max_period = max(self.ma_periods)

    def analyze_symbol(self, symbol: str, name: str = "") -> Optional[Dict]:
        """
        단일 종목의 여러 이동평균선 분석

        Args:
            symbol: 종목 심볼
            name: 종목명

        Returns:
            분석 결과 딕셔너리 또는 None
        """
        try:
            ticker = yf.Ticker(symbol)
            # 최대 기간 + 여유분 데이터 조회
            data = ticker.history(period="2y", auto_adjust=True)

            if data.empty or len(data) < self.max_period:
                logger.debug(f"{symbol}: 데이터 부족 ({len(data)}일, 필요: {self.max_period}일)")
                return None

            current_price = float(data['Close'].iloc[-1])

            if current_price < self.min_price:
                return None

            avg_volume = float(data['Volume'].iloc[-20:].mean())
            if avg_volume < self.min_volume:
                return None

            result = {
                'symbol': symbol,
                'code': symbol.replace('.KS', '').replace('.KQ', ''),
                'name': name,
                'current_price': current_price,
                'avg_volume_20d': int(avg_volume),
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
            }

            # 각 이동평균 기간에 대해 분석
            for period in self.ma_periods:
                if len(data) >= period:
                    ma_value = float(data['Close'].iloc[-period:].mean())
                    distance_pct = ((current_price - ma_value) / ma_value) * 100

                    # 상태 판정
                    if distance_pct < -self.touch_threshold:
                        status = 'below'  # 아래
                    elif abs(distance_pct) <= self.touch_threshold:
                        status = 'touch'  # 터치 (근처)
                    else:
                        status = 'above'  # 위

                    result[f'ma_{period}'] = ma_value
                    result[f'dist_{period}'] = round(distance_pct, 2)
                    result[f'status_{period}'] = status
                else:
                    result[f'ma_{period}'] = None
                    result[f'dist_{period}'] = None
                    result[f'status_{period}'] = 'no_data'

            return result

        except Exception as e:
            logger.warning(f"{symbol} 분석 실패: {e}")
            return None

    def batch_screen(
        self,
        symbols: List[Dict],
        show_progress: bool = True
    ) -> List[Dict]:
        """여러 종목 일괄 스크리닝"""
        results = []
        total = len(symbols)
        processed = 0

        logger.info(f"스크리닝 시작: {total}개 종목 (MA: {self.ma_periods})")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.analyze_symbol,
                    s['symbol'],
                    s.get('name', '')
                ): s for s in symbols
            }

            for future in as_completed(futures):
                processed += 1
                result = future.result()

                if result:
                    results.append(result)

                if show_progress and processed % 10 == 0:
                    logger.info(f"진행: {processed}/{total} ({len(results)}개 통과)")

                time.sleep(self.request_delay)

        logger.info(f"스크리닝 완료: {len(results)}/{total}개 종목 분석됨")
        return results

    def filter_by_status(
        self,
        results: List[Dict],
        ma_period: int,
        status: str = 'below',
        sort_by_distance: bool = True
    ) -> List[Dict]:
        """
        특정 MA 기간에 대해 상태별 필터링

        Args:
            results: batch_screen 결과
            ma_period: 이동평균 기간
            status: 'below', 'touch', 'above'
            sort_by_distance: 거리순 정렬

        Returns:
            필터링된 결과 리스트
        """
        filtered = [r for r in results if r.get(f'status_{ma_period}') == status]

        if sort_by_distance:
            filtered.sort(key=lambda x: x.get(f'dist_{ma_period}', 0))

        return filtered

    def filter_touch_or_below(
        self,
        results: List[Dict],
        ma_period: int,
        sort_by_distance: bool = True
    ) -> List[Dict]:
        """터치 또는 아래인 종목 필터링"""
        filtered = [
            r for r in results
            if r.get(f'status_{ma_period}') in ['below', 'touch']
        ]

        if sort_by_distance:
            filtered.sort(key=lambda x: x.get(f'dist_{ma_period}', 0))

        return filtered

    def get_summary(self, results: List[Dict]) -> Dict:
        """스크리닝 결과 요약"""
        if not results:
            return {'total': 0}

        summary = {'total': len(results)}

        for period in self.ma_periods:
            below = sum(1 for r in results if r.get(f'status_{period}') == 'below')
            touch = sum(1 for r in results if r.get(f'status_{period}') == 'touch')
            above = sum(1 for r in results if r.get(f'status_{period}') == 'above')

            summary[f'ma_{period}_below'] = below
            summary[f'ma_{period}_touch'] = touch
            summary[f'ma_{period}_above'] = above

        return summary


def format_price(price: float) -> str:
    """가격 포맷팅 (원화)"""
    return f"{int(price):,}원"


def print_results(results: List[Dict], title: str, ma_period: int, limit: int = 20):
    """결과 출력"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

    if not results:
        print("  해당 종목 없음")
        return

    for i, r in enumerate(results[:limit], 1):
        distance = r.get(f'distance_from_{ma_period}_pct', 0)
        ma_value = r.get(f'ma_{ma_period}', 0)
        print(
            f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
            f"현재가 {format_price(r['current_price']):>12} | "
            f"{ma_period}일선 {format_price(ma_value):>12} | "
            f"{distance:>+6.1f}%"
        )

    if len(results) > limit:
        print(f"\n  ... 외 {len(results) - limit}개 종목")


class CrossoverScreener:
    """골든크로스/데드크로스 감지 스크리너"""

    def __init__(
        self,
        short_ma: int = 20,
        long_ma: int = 60,
        lookback_days: int = 5,
        extra_ma_periods: List[int] = None,
        touch_threshold: float = 2.0,
        min_volume: int = 100000,
        min_price: float = 1000,
        max_workers: int = 10,
        request_delay: float = 0.1
    ):
        """
        Args:
            short_ma: 단기 이동평균 기간 (기본 20일)
            long_ma: 장기 이동평균 기간 (기본 60일)
            lookback_days: 크로스 감지 기간 (최근 N일 내)
            extra_ma_periods: 추가 분석할 장기 이평선 기간 (예: [240])
            touch_threshold: 터치 판정 기준 (±%, 기본 2%)
            min_volume: 최소 거래량 필터
            min_price: 최소 주가 필터
            max_workers: 병렬 처리 스레드 수
            request_delay: API 요청 간 대기 시간
        """
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.lookback_days = lookback_days
        self.extra_ma_periods = extra_ma_periods or []
        self.touch_threshold = touch_threshold
        self.min_volume = min_volume
        self.min_price = min_price
        self.max_workers = max_workers
        self.request_delay = request_delay

    def analyze_symbol(self, symbol: str, name: str = "") -> Optional[Dict]:
        """
        단일 종목의 골든크로스/데드크로스 분석

        Args:
            symbol: 종목 심볼
            name: 종목명

        Returns:
            분석 결과 딕셔너리 또는 None
        """
        try:
            ticker = yf.Ticker(symbol)
            # 장기 이평선 분석을 위해 2년 데이터 조회
            data = ticker.history(period="2y", auto_adjust=True)

            if data.empty or len(data) < self.long_ma + self.lookback_days:
                logger.debug(f"{symbol}: 데이터 부족")
                return None

            current_price = float(data['Close'].iloc[-1])

            if current_price < self.min_price:
                return None

            avg_volume = float(data['Volume'].iloc[-20:].mean())
            if avg_volume < self.min_volume:
                return None

            # 이동평균 시계열 계산
            data['ma_short'] = data['Close'].rolling(window=self.short_ma).mean()
            data['ma_long'] = data['Close'].rolling(window=self.long_ma).mean()

            # 크로스오버 감지 (단기 - 장기)
            data['ma_diff'] = data['ma_short'] - data['ma_long']
            data['ma_diff_prev'] = data['ma_diff'].shift(1)

            # 골든크로스: 이전에 음수 → 현재 양수
            data['golden_cross'] = (data['ma_diff_prev'] < 0) & (data['ma_diff'] >= 0)
            # 데드크로스: 이전에 양수 → 현재 음수
            data['dead_cross'] = (data['ma_diff_prev'] > 0) & (data['ma_diff'] <= 0)

            # 최근 N일 내 크로스 확인
            recent_data = data.iloc[-(self.lookback_days + 1):]

            golden_cross_dates = recent_data[recent_data['golden_cross']].index.tolist()
            dead_cross_dates = recent_data[recent_data['dead_cross']].index.tolist()

            # 현재 상태 (단기 MA가 장기 MA 위인지)
            current_ma_short = float(data['ma_short'].iloc[-1])
            current_ma_long = float(data['ma_long'].iloc[-1])
            is_bullish = current_ma_short > current_ma_long

            # 크로스 발생 여부 및 날짜
            has_golden_cross = len(golden_cross_dates) > 0
            has_dead_cross = len(dead_cross_dates) > 0

            golden_cross_date = None
            dead_cross_date = None
            days_since_golden = None
            days_since_dead = None

            if has_golden_cross:
                golden_cross_date = golden_cross_dates[-1]
                days_since_golden = (data.index[-1] - golden_cross_date).days

            if has_dead_cross:
                dead_cross_date = dead_cross_dates[-1]
                days_since_dead = (data.index[-1] - dead_cross_date).days

            result = {
                'symbol': symbol,
                'code': symbol.replace('.KS', '').replace('.KQ', ''),
                'name': name,
                'current_price': current_price,
                f'ma_{self.short_ma}': round(current_ma_short, 2),
                f'ma_{self.long_ma}': round(current_ma_long, 2),
                'is_bullish': is_bullish,
                'has_golden_cross': has_golden_cross,
                'has_dead_cross': has_dead_cross,
                'golden_cross_date': golden_cross_date.strftime('%Y-%m-%d') if golden_cross_date else None,
                'dead_cross_date': dead_cross_date.strftime('%Y-%m-%d') if dead_cross_date else None,
                'days_since_golden': days_since_golden,
                'days_since_dead': days_since_dead,
                'ma_diff_pct': round(((current_ma_short - current_ma_long) / current_ma_long) * 100, 2),
                'avg_volume_20d': int(avg_volume),
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
            }

            # 추가 장기 이평선 분석 (240일 등)
            for period in self.extra_ma_periods:
                if len(data) >= period:
                    ma_value = float(data['Close'].iloc[-period:].mean())
                    distance_pct = ((current_price - ma_value) / ma_value) * 100

                    # 상태 판정: 아래/터치/위
                    if distance_pct < -self.touch_threshold:
                        status = 'below'
                    elif abs(distance_pct) <= self.touch_threshold:
                        status = 'touch'
                    else:
                        status = 'above'

                    result[f'ma_{period}'] = round(ma_value, 2)
                    result[f'dist_{period}'] = round(distance_pct, 2)
                    result[f'status_{period}'] = status
                else:
                    result[f'ma_{period}'] = None
                    result[f'dist_{period}'] = None
                    result[f'status_{period}'] = 'no_data'

            return result

        except Exception as e:
            logger.warning(f"{symbol} 분석 실패: {e}")
            return None

    def batch_screen(
        self,
        symbols: List[Dict],
        show_progress: bool = True
    ) -> List[Dict]:
        """여러 종목 일괄 스크리닝"""
        results = []
        total = len(symbols)
        processed = 0

        logger.info(f"크로스오버 스크리닝 시작: {total}개 종목 (MA: {self.short_ma}/{self.long_ma}, 최근 {self.lookback_days}일)")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.analyze_symbol,
                    s['symbol'],
                    s.get('name', '')
                ): s for s in symbols
            }

            for future in as_completed(futures):
                processed += 1
                result = future.result()

                if result:
                    results.append(result)

                if show_progress and processed % 10 == 0:
                    logger.info(f"진행: {processed}/{total} ({len(results)}개 통과)")

                time.sleep(self.request_delay)

        logger.info(f"스크리닝 완료: {len(results)}/{total}개 종목 분석됨")
        return results

    def filter_golden_cross(self, results: List[Dict]) -> List[Dict]:
        """골든크로스 발생 종목 필터링"""
        filtered = [r for r in results if r.get('has_golden_cross')]
        filtered.sort(key=lambda x: x.get('days_since_golden') or 999)
        return filtered

    def filter_dead_cross(self, results: List[Dict]) -> List[Dict]:
        """데드크로스 발생 종목 필터링"""
        filtered = [r for r in results if r.get('has_dead_cross')]
        filtered.sort(key=lambda x: x.get('days_since_dead') or 999)
        return filtered

    def filter_bullish(self, results: List[Dict]) -> List[Dict]:
        """상승 추세 (단기 MA > 장기 MA) 종목 필터링"""
        filtered = [r for r in results if r.get('is_bullish')]
        filtered.sort(key=lambda x: -x.get('ma_diff_pct', 0))
        return filtered

    def filter_bearish(self, results: List[Dict]) -> List[Dict]:
        """하락 추세 (단기 MA < 장기 MA) 종목 필터링"""
        filtered = [r for r in results if not r.get('is_bullish')]
        filtered.sort(key=lambda x: x.get('ma_diff_pct', 0))
        return filtered

    def filter_ma_touch(self, results: List[Dict], ma_period: int) -> List[Dict]:
        """특정 이평선 터치 종목 필터링 (±threshold% 이내)"""
        filtered = [r for r in results if r.get(f'status_{ma_period}') == 'touch']
        filtered.sort(key=lambda x: abs(x.get(f'dist_{ma_period}', 999)))
        return filtered

    def filter_ma_below(self, results: List[Dict], ma_period: int) -> List[Dict]:
        """특정 이평선 아래 종목 필터링"""
        filtered = [r for r in results if r.get(f'status_{ma_period}') == 'below']
        filtered.sort(key=lambda x: x.get(f'dist_{ma_period}', 0))
        return filtered

    def filter_ma_touch_or_below(self, results: List[Dict], ma_period: int) -> List[Dict]:
        """특정 이평선 터치 또는 아래 종목 필터링"""
        filtered = [r for r in results if r.get(f'status_{ma_period}') in ['touch', 'below']]
        filtered.sort(key=lambda x: x.get(f'dist_{ma_period}', 0))
        return filtered

    def get_summary(self, results: List[Dict]) -> Dict:
        """스크리닝 결과 요약"""
        if not results:
            return {'total': 0}

        golden_cross = sum(1 for r in results if r.get('has_golden_cross'))
        dead_cross = sum(1 for r in results if r.get('has_dead_cross'))
        bullish = sum(1 for r in results if r.get('is_bullish'))
        bearish = len(results) - bullish

        summary = {
            'total': len(results),
            'golden_cross': golden_cross,
            'dead_cross': dead_cross,
            'bullish': bullish,
            'bearish': bearish,
            'lookback_days': self.lookback_days
        }

        # 추가 장기 이평선 요약
        for period in self.extra_ma_periods:
            below = sum(1 for r in results if r.get(f'status_{period}') == 'below')
            touch = sum(1 for r in results if r.get(f'status_{period}') == 'touch')
            above = sum(1 for r in results if r.get(f'status_{period}') == 'above')
            summary[f'ma_{period}_below'] = below
            summary[f'ma_{period}_touch'] = touch
            summary[f'ma_{period}_above'] = above

        return summary


def print_crossover_results(results: List[Dict], title: str, cross_type: str, limit: int = 20):
    """크로스오버 결과 출력"""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")

    if not results:
        print("  해당 종목 없음")
        return

    for i, r in enumerate(results[:limit], 1):
        if cross_type == 'golden':
            days = r.get('days_since_golden', '?')
            date = r.get('golden_cross_date', '')
            signal = "🔺 골든크로스"
        else:
            days = r.get('days_since_dead', '?')
            date = r.get('dead_cross_date', '')
            signal = "🔻 데드크로스"

        ma_diff = r.get('ma_diff_pct', 0)
        print(
            f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
            f"현재가 {format_price(r['current_price']):>12} | "
            f"{signal} {days}일전 ({date}) | "
            f"MA차이 {ma_diff:>+5.1f}%"
        )

    if len(results) > limit:
        print(f"\n  ... 외 {len(results) - limit}개 종목")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

    # 테스트: 삼성전자
    screener = MovingAverageScreener()
    result = screener.analyze_symbol('005930.KS', '삼성전자')

    if result:
        print("\n[삼성전자 분석 결과]")
        for k, v in result.items():
            print(f"  {k}: {v}")
