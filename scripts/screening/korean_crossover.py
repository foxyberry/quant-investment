"""
한국 주식 골든크로스/데드크로스 스크리너
- 단기 이평선이 장기 이평선을 돌파하는 종목 탐색
- 추세 전환 시점 포착용

사용법:
    python scripts/screening/korean_crossover.py
    python scripts/screening/korean_crossover.py --short-ma 20 --long-ma 60
    python scripts/screening/korean_crossover.py --lookback 10
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
    CrossoverScreener,
    print_crossover_results,
    format_price
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run(
    short_ma: int = 20,
    long_ma: int = 60,
    lookback_days: int = 5,
    extra_ma: list = None,
    min_volume: int = 100000,
    min_price: float = 1000,
    limit: int = 30
) -> dict:
    """
    메인 실행 함수

    Args:
        short_ma: 단기 이동평균 기간
        long_ma: 장기 이동평균 기간
        lookback_days: 크로스 감지 기간 (최근 N일)
        extra_ma: 추가 분석할 장기 이평선 기간 (예: [240])
        min_volume: 최소 거래량
        min_price: 최소 주가
        limit: 출력 제한

    Returns:
        {'golden_cross': [...], 'dead_cross': [...], 'summary': {...}}
    """
    if extra_ma is None:
        extra_ma = [240]

    print("\n" + "="*70)
    print(" 한국 주식 골든크로스/데드크로스 스크리너")
    print(f" 설정: {short_ma}일선 vs {long_ma}일선 | 최근 {lookback_days}일 내 발생")
    if extra_ma:
        print(f" 추가 분석: {extra_ma}일선 터치 여부")
    print("="*70)

    # 1. 코스피 종목 리스트 가져오기
    logger.info("코스피 종목 리스트 수집 중...")
    fetcher = KospiListFetcher()
    kospi_list = fetcher.get_kospi_symbols()

    if not kospi_list:
        logger.error("종목 리스트를 가져올 수 없습니다.")
        return {}

    print(f"\n총 {len(kospi_list)}개 종목 대상")

    # 2. 크로스오버 스크리닝
    logger.info("크로스오버 분석 시작...")
    screener = CrossoverScreener(
        short_ma=short_ma,
        long_ma=long_ma,
        lookback_days=lookback_days,
        extra_ma_periods=extra_ma,
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
    print(f"  상승 추세 (단기 > 장기): {summary['bullish']}개")
    print(f"  하락 추세 (단기 < 장기): {summary['bearish']}개")
    print(f"  최근 {lookback_days}일 내 골든크로스: {summary['golden_cross']}개")
    print(f"  최근 {lookback_days}일 내 데드크로스: {summary['dead_cross']}개")
    for period in extra_ma:
        below = summary.get(f'ma_{period}_below', 0)
        touch = summary.get(f'ma_{period}_touch', 0)
        print(f"  {period}일선 터치: {touch}개 | 아래: {below}개")
    print("-" * 50)

    # 4. 골든크로스 종목 출력
    golden_cross = screener.filter_golden_cross(results)
    print_crossover_results(
        golden_cross,
        f"골든크로스 발생 종목 ({short_ma}일선이 {long_ma}일선 상향 돌파)",
        'golden',
        limit
    )

    # 5. 데드크로스 종목 출력
    dead_cross = screener.filter_dead_cross(results)
    print_crossover_results(
        dead_cross,
        f"데드크로스 발생 종목 ({short_ma}일선이 {long_ma}일선 하향 돌파)",
        'dead',
        limit
    )

    # 6. 장기 이평선 터치/아래 종목 출력
    for period in extra_ma:
        touch_list = screener.filter_ma_touch(results, period)
        if touch_list:
            print(f"\n{'='*70}")
            print(f" {period}일선 터치 종목 (±2% 이내)")
            print(f"{'='*70}")
            for i, r in enumerate(touch_list[:limit], 1):
                dist = r.get(f'dist_{period}', 0)
                ma_val = r.get(f'ma_{period}', 0)
                cross_info = ""
                if r.get('has_golden_cross'):
                    cross_info = " [골든크로스]"
                elif r.get('has_dead_cross'):
                    cross_info = " [데드크로스]"
                print(
                    f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
                    f"현재가 {format_price(r['current_price']):>12} | "
                    f"{period}일선 {format_price(ma_val):>12} | "
                    f"{dist:>+5.1f}%{cross_info}"
                )

        below_list = screener.filter_ma_below(results, period)
        if below_list:
            print(f"\n{'='*70}")
            print(f" {period}일선 아래 종목 (낙폭 큰 순)")
            print(f"{'='*70}")
            for i, r in enumerate(below_list[:limit], 1):
                dist = r.get(f'dist_{period}', 0)
                ma_val = r.get(f'ma_{period}', 0)
                cross_info = ""
                if r.get('has_golden_cross'):
                    cross_info = " [골든크로스]"
                elif r.get('has_dead_cross'):
                    cross_info = " [데드크로스]"
                print(
                    f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
                    f"현재가 {format_price(r['current_price']):>12} | "
                    f"{period}일선 {format_price(ma_val):>12} | "
                    f"{dist:>+5.1f}%{cross_info}"
                )

    # 7. 추세별 상위 종목
    print(f"\n{'='*70}")
    print(f" 상승 추세 강도 TOP 10 (단기 MA가 장기 MA 위)")
    print(f"{'='*70}")
    bullish = screener.filter_bullish(results)[:10]
    for i, r in enumerate(bullish, 1):
        ma_diff = r.get('ma_diff_pct', 0)
        print(
            f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
            f"현재가 {format_price(r['current_price']):>12} | "
            f"MA차이 {ma_diff:>+5.1f}%"
        )

    print(f"\n{'='*70}")
    print(f" 하락 추세 강도 TOP 10 (단기 MA가 장기 MA 아래)")
    print(f"{'='*70}")
    bearish = screener.filter_bearish(results)[:10]
    for i, r in enumerate(bearish, 1):
        ma_diff = r.get('ma_diff_pct', 0)
        print(
            f"{i:3}. {r['name'][:10]:<10} ({r['code']}) | "
            f"현재가 {format_price(r['current_price']):>12} | "
            f"MA차이 {ma_diff:>+5.1f}%"
        )

    return {
        'golden_cross': golden_cross,
        'dead_cross': dead_cross,
        'bullish': bullish,
        'bearish': bearish,
        'all_results': results,
        'summary': summary
    }


def main():
    parser = argparse.ArgumentParser(
        description='한국 주식 골든크로스/데드크로스 스크리너'
    )
    parser.add_argument(
        '--short-ma', type=int, default=20,
        help='단기 이동평균 기간 (기본: 20)'
    )
    parser.add_argument(
        '--long-ma', type=int, default=60,
        help='장기 이동평균 기간 (기본: 60)'
    )
    parser.add_argument(
        '--lookback', type=int, default=5,
        help='크로스 감지 기간 - 최근 N일 (기본: 5)'
    )
    parser.add_argument(
        '--extra-ma', type=int, nargs='+', default=[240],
        help='추가 분석할 장기 이평선 기간 (기본: 240)'
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
        '--limit', type=int, default=30,
        help='출력 제한 (기본: 30)'
    )

    args = parser.parse_args()

    run(
        short_ma=args.short_ma,
        long_ma=args.long_ma,
        lookback_days=args.lookback,
        extra_ma=args.extra_ma,
        min_volume=args.min_volume,
        min_price=args.min_price,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
