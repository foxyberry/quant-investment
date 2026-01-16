"""
한국 주식 장기 이동평균선 터치 스크리너
- 200일선, 240일선, 365일선에 터치하거나 아래에 있는 종목 탐색
- 장기 지지선 테스트 종목 발굴용

사용법:
    python my_strategies/screening/korean_ma_touch.py
    python my_strategies/screening/korean_ma_touch.py --periods 200 240 365
    python my_strategies/screening/korean_ma_touch.py --threshold 3.0
"""

import sys
import logging
import argparse
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from screener.korean.kospi_fetcher import KospiListFetcher
from screener.korean.ma_screener import MultiMAScreener, format_price

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_ma_results(results, ma_period, status_filter, limit=20):
    """특정 MA에 대한 결과 출력"""
    status_label = {
        'below': '아래',
        'touch': '터치',
        'both': '터치/아래'
    }

    print(f"\n{'='*70}")
    print(f" {ma_period}일선 {status_label.get(status_filter, status_filter)} 종목")
    print(f"{'='*70}")

    if not results:
        print("  해당 종목 없음")
        return

    for i, r in enumerate(results[:limit], 1):
        dist = r.get(f'dist_{ma_period}', 0)
        ma_val = r.get(f'ma_{ma_period}', 0)
        status = r.get(f'status_{ma_period}', '')

        status_mark = {'below': '[하]', 'touch': '[터]', 'above': '[상]'}.get(status, '')

        print(
            f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
            f"현재가 {format_price(r['current_price']):>12} | "
            f"{ma_period}일선 {format_price(ma_val):>12} | "
            f"{dist:>+6.1f}% {status_mark}"
        )

    if len(results) > limit:
        print(f"\n  ... 외 {len(results) - limit}개 종목")


def run(
    ma_periods: list = None,
    touch_threshold: float = 2.0,
    min_volume: int = 100000,
    min_price: float = 1000,
    limit: int = 20
) -> dict:
    """
    메인 실행 함수

    Args:
        ma_periods: 분석할 이동평균 기간 리스트
        touch_threshold: 터치 판정 기준 (±%)
        min_volume: 최소 거래량
        min_price: 최소 주가
        limit: 출력 제한

    Returns:
        분석 결과 딕셔너리
    """
    if ma_periods is None:
        ma_periods = [200, 240, 365]

    print("\n" + "="*70)
    print(" 한국 주식 장기 이동평균선 터치 스크리너")
    print(f" 분석 대상: {ma_periods}일선 | 터치 기준: ±{touch_threshold}%")
    print("="*70)

    # 1. 코스피 종목 리스트 가져오기
    logger.info("코스피 종목 리스트 수집 중...")
    fetcher = KospiListFetcher()
    kospi_list = fetcher.get_kospi_symbols()

    if not kospi_list:
        logger.error("종목 리스트를 가져올 수 없습니다.")
        return {}

    print(f"\n총 {len(kospi_list)}개 종목 대상")

    # 2. 멀티 MA 스크리닝
    logger.info("이동평균선 분석 시작...")
    screener = MultiMAScreener(
        ma_periods=ma_periods,
        touch_threshold=touch_threshold,
        min_volume=min_volume,
        min_price=min_price,
        max_workers=10
    )

    results = screener.batch_screen(kospi_list)

    if not results:
        logger.warning("분석 결과가 없습니다.")
        return {}

    # 3. 결과 요약
    summary = screener.get_summary(results)

    print(f"\n[요약] 분석 완료: {summary['total']}개")
    print("-" * 50)
    print(f"{'MA 기간':<10} | {'아래':>8} | {'터치':>8} | {'위':>8}")
    print("-" * 50)
    for period in ma_periods:
        below = summary.get(f'ma_{period}_below', 0)
        touch = summary.get(f'ma_{period}_touch', 0)
        above = summary.get(f'ma_{period}_above', 0)
        print(f"{period}일선{'':<5} | {below:>8} | {touch:>8} | {above:>8}")
    print("-" * 50)

    # 4. 각 MA별 터치/아래 종목 출력
    all_results = {}

    for period in ma_periods:
        # 터치 종목
        touch_list = screener.filter_by_status(results, period, 'touch')
        if touch_list:
            print_ma_results(touch_list, period, 'touch', limit)
            all_results[f'{period}_touch'] = touch_list

        # 아래 종목
        below_list = screener.filter_by_status(results, period, 'below')
        if below_list:
            print_ma_results(below_list, period, 'below', limit)
            all_results[f'{period}_below'] = below_list

    # 5. 여러 MA선 동시 터치/아래 종목
    print(f"\n{'='*70}")
    print(f" 여러 장기 MA선 동시 터치/아래 종목")
    print(f"{'='*70}")

    multi_touch = []
    for r in results:
        touch_count = sum(
            1 for p in ma_periods
            if r.get(f'status_{p}') in ['below', 'touch']
        )
        if touch_count >= 2:
            r['touch_count'] = touch_count
            multi_touch.append(r)

    multi_touch.sort(key=lambda x: -x['touch_count'])

    if multi_touch:
        for i, r in enumerate(multi_touch[:limit], 1):
            status_str = " | ".join([
                f"{p}일:{r.get(f'dist_{p}', 0):+.1f}%"
                for p in ma_periods
            ])
            print(
                f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
                f"현재가 {format_price(r['current_price']):>10} | "
                f"{status_str}"
            )
    else:
        print("  해당 종목 없음")

    all_results['multi_touch'] = multi_touch
    all_results['all_results'] = results
    all_results['summary'] = summary

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description='한국 주식 장기 이동평균선 터치 스크리너'
    )
    parser.add_argument(
        '--periods', type=int, nargs='+', default=[200, 240, 365],
        help='분석할 MA 기간들 (기본: 200 240 365)'
    )
    parser.add_argument(
        '--threshold', type=float, default=2.0,
        help='터치 판정 기준 ±%% (기본: 2.0)'
    )
    parser.add_argument(
        '--min-volume', type=int, default=100000,
        help='최소 거래량 (기본: 100,000)'
    )
    parser.add_argument(
        '--min-price', type=float, default=1000,
        help='최소 주가 (기본: 1,000원)'
    )
    parser.add_argument(
        '--limit', type=int, default=20,
        help='출력 제한 (기본: 20)'
    )

    args = parser.parse_args()

    run(
        ma_periods=args.periods,
        touch_threshold=args.threshold,
        min_volume=args.min_volume,
        min_price=args.min_price,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
