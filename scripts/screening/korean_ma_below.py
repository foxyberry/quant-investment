"""
한국 주식 이동평균선 하향 스크리너
- 코스피 종목 중 60일선/120일선 아래 종목 탐색
- 역발상 투자 또는 저점 매수 기회 탐색용

사용법:
    python my_strategies/screening/korean_ma_below.py
    python my_strategies/screening/korean_ma_below.py --ma 60
    python my_strategies/screening/korean_ma_below.py --ma 120
    python my_strategies/screening/korean_ma_below.py --limit 30
"""

import sys
import logging
import argparse
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from screener.korean.kospi_fetcher import KospiListFetcher
from screener.korean.ma_screener import (
    MovingAverageScreener,
    print_results,
    format_price
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run(
    short_ma: int = 60,
    long_ma: int = 120,
    min_volume: int = 100000,
    min_price: float = 1000,
    limit: int = 50,
    show_all: bool = False
) -> dict:
    """
    메인 실행 함수

    Args:
        short_ma: 단기 이동평균 기간
        long_ma: 장기 이동평균 기간
        min_volume: 최소 거래량
        min_price: 최소 주가
        limit: 출력 제한
        show_all: 모든 결과 표시

    Returns:
        {'below_short': [...], 'below_long': [...], 'summary': {...}}
    """
    print("\n" + "="*60)
    print(" 한국 주식 이동평균선 스크리너")
    print(f" 설정: {short_ma}일선 / {long_ma}일선")
    print("="*60)

    # 1. 코스피 종목 리스트 가져오기
    logger.info("코스피 종목 리스트 수집 중...")
    fetcher = KospiListFetcher()
    kospi_list = fetcher.get_kospi_symbols()

    if not kospi_list:
        logger.error("종목 리스트를 가져올 수 없습니다.")
        return {}

    print(f"\n총 {len(kospi_list)}개 종목 대상")

    # 2. 이동평균선 스크리닝
    logger.info("이동평균선 분석 시작...")
    screener = MovingAverageScreener(
        short_ma=short_ma,
        long_ma=long_ma,
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
    print(f"\n[요약]")
    print(f"  분석 완료: {summary['total']}개")
    print(f"  {short_ma}일선 아래: {summary.get(f'below_{short_ma}', 0)}개")
    print(f"  {long_ma}일선 아래: {summary.get(f'below_{long_ma}', 0)}개")
    print(f"  둘 다 아래: {summary.get('below_both', 0)}개")

    # 4. 필터링 및 출력
    below_short = screener.filter_below_ma(results, 'short')
    below_long = screener.filter_below_ma(results, 'long')

    print_results(
        below_short,
        f"{short_ma}일선 아래 종목 (낙폭 큰 순)",
        short_ma,
        limit
    )

    print_results(
        below_long,
        f"{long_ma}일선 아래 종목 (낙폭 큰 순)",
        long_ma,
        limit
    )

    # 5. 둘 다 아래인 종목 (심각한 하락)
    below_both = [
        r for r in results
        if r.get(f'below_{short_ma}') and r.get(f'below_{long_ma}')
    ]
    below_both.sort(key=lambda x: x.get(f'distance_from_{long_ma}_pct', 0))

    if below_both:
        print(f"\n{'='*60}")
        print(f" {short_ma}일선 & {long_ma}일선 모두 아래 (심각한 하락)")
        print(f"{'='*60}")
        for i, r in enumerate(below_both[:limit], 1):
            dist_short = r.get(f'distance_from_{short_ma}_pct', 0)
            dist_long = r.get(f'distance_from_{long_ma}_pct', 0)
            print(
                f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
                f"현재가 {format_price(r['current_price']):>12} | "
                f"{short_ma}일선 {dist_short:>+6.1f}% | "
                f"{long_ma}일선 {dist_long:>+6.1f}%"
            )

    return {
        'below_short': below_short,
        'below_long': below_long,
        'below_both': below_both,
        'all_results': results,
        'summary': summary
    }


def main():
    parser = argparse.ArgumentParser(
        description='한국 주식 이동평균선 하향 스크리너'
    )
    parser.add_argument(
        '--short-ma', type=int, default=60,
        help='단기 이동평균 기간 (기본: 60)'
    )
    parser.add_argument(
        '--long-ma', type=int, default=120,
        help='장기 이동평균 기간 (기본: 120)'
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
        '--limit', type=int, default=50,
        help='출력 제한 (기본: 50)'
    )

    args = parser.parse_args()

    run(
        short_ma=args.short_ma,
        long_ma=args.long_ma,
        min_volume=args.min_volume,
        min_price=args.min_price,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
