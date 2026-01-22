"""
한국 주식 일일 종합 스크리닝 리포트
- 골든크로스/데드크로스 발생
- 장기 이평선(240일) 터치/아래
- 중기 이평선(60/120일) 아래
- 추세 강도 분석

하루 한 번 실행하여 시장 전체 상황을 파악

사용법:
    python scripts/screening/korean_daily_report.py
    python scripts/screening/korean_daily_report.py --output report.txt
    python scripts/screening/korean_daily_report.py --lookback 10
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from screener.korean.kospi_fetcher import KospiListFetcher
from screener.korean.ma_screener import (
    CrossoverScreener,
    format_price
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str, width: int = 70):
    """섹션 헤더 출력"""
    print(f"\n{'='*width}")
    print(f" {title}")
    print(f"{'='*width}")


def run(
    lookback_days: int = 7,
    output_file: str = None
) -> dict:
    """
    일일 종합 리포트 생성

    Args:
        lookback_days: 크로스 감지 기간 (최근 N일)
        output_file: 결과 저장 파일 경로

    Returns:
        종합 분석 결과
    """
    report_date = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 출력 리다이렉션 설정
    original_stdout = sys.stdout
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        file_handle = open(output_path, 'w', encoding='utf-8')
        sys.stdout = file_handle

    try:
        print("\n" + "#"*70)
        print("#" + " "*68 + "#")
        print("#" + "한국 주식 일일 종합 스크리닝 리포트".center(60) + "    #")
        print("#" + " "*68 + "#")
        print("#"*70)
        print(f"\n리포트 생성: {report_date}")
        print(f"분석 설정: 크로스오버 {lookback_days}일 내 | 터치 기준 ±2%")

        # 1. 종목 리스트 가져오기
        logger.info("코스피 종목 리스트 수집 중...")
        fetcher = KospiListFetcher()
        kospi_list = fetcher.get_kospi_symbols()

        if not kospi_list:
            logger.error("종목 리스트를 가져올 수 없습니다.")
            return {}

        print(f"분석 대상: 코스피 {len(kospi_list)}개 종목")

        # 2. 종합 스크리닝 실행
        logger.info("종합 스크리닝 시작...")
        screener = CrossoverScreener(
            short_ma=20,
            long_ma=60,
            lookback_days=lookback_days,
            extra_ma_periods=[60, 120, 240],
            touch_threshold=2.0,
            min_volume=100000,
            min_price=1000,
            max_workers=10
        )

        results = screener.batch_screen(kospi_list)

        if not results:
            logger.warning("분석 결과가 없습니다.")
            return {}

        summary = screener.get_summary(results)

        # ===== 요약 섹션 =====
        print_section("시장 요약")
        print(f"""
  분석 완료: {summary['total']}개 종목

  [추세]
  - 상승 추세 (20일 > 60일): {summary['bullish']}개 ({summary['bullish']/summary['total']*100:.1f}%)
  - 하락 추세 (20일 < 60일): {summary['bearish']}개 ({summary['bearish']/summary['total']*100:.1f}%)

  [크로스오버] (최근 {lookback_days}일)
  - 골든크로스 발생: {summary['golden_cross']}개
  - 데드크로스 발생: {summary['dead_cross']}개

  [장기 이평선 - 240일]
  - 터치 (±2%): {summary.get('ma_240_touch', 0)}개
  - 아래: {summary.get('ma_240_below', 0)}개

  [중기 이평선 - 60일/120일]
  - 60일선 아래: {summary.get('ma_60_below', 0)}개
  - 120일선 아래: {summary.get('ma_120_below', 0)}개
""")

        # ===== 골든크로스 섹션 =====
        golden_cross = screener.filter_golden_cross(results)
        if golden_cross:
            print_section(f"골든크로스 발생 ({len(golden_cross)}개) - 상승 추세 전환")
            for i, r in enumerate(golden_cross[:15], 1):
                days = r.get('days_since_golden', '?')
                date = r.get('golden_cross_date', '')
                ma_diff = r.get('ma_diff_pct', 0)
                ma240_status = r.get('status_240', '')
                ma240_note = ""
                if ma240_status == 'touch':
                    ma240_note = " | 240일 터치"
                elif ma240_status == 'below':
                    ma240_note = f" | 240일 아래({r.get('dist_240', 0):+.1f}%)"
                print(
                    f"  {i:2}. {r['name'][:10]:<10} ({r['code']}) | "
                    f"{format_price(r['current_price']):>12} | "
                    f"{days}일전 ({date}) | MA차이 {ma_diff:>+5.1f}%{ma240_note}"
                )

        # ===== 데드크로스 섹션 =====
        dead_cross = screener.filter_dead_cross(results)
        if dead_cross:
            print_section(f"데드크로스 발생 ({len(dead_cross)}개) - 하락 추세 전환")
            for i, r in enumerate(dead_cross[:15], 1):
                days = r.get('days_since_dead', '?')
                date = r.get('dead_cross_date', '')
                ma_diff = r.get('ma_diff_pct', 0)
                ma240_status = r.get('status_240', '')
                ma240_note = ""
                if ma240_status == 'touch':
                    ma240_note = " | 240일 터치"
                elif ma240_status == 'below':
                    ma240_note = f" | 240일 아래({r.get('dist_240', 0):+.1f}%)"
                print(
                    f"  {i:2}. {r['name'][:10]:<10} ({r['code']}) | "
                    f"{format_price(r['current_price']):>12} | "
                    f"{days}일전 ({date}) | MA차이 {ma_diff:>+5.1f}%{ma240_note}"
                )

        # ===== 240일선 터치 섹션 =====
        ma240_touch = screener.filter_ma_touch(results, 240)
        if ma240_touch:
            print_section(f"240일선 터치 ({len(ma240_touch)}개) - 장기 지지선 테스트")
            for i, r in enumerate(ma240_touch[:15], 1):
                dist = r.get('dist_240', 0)
                cross_info = ""
                if r.get('has_golden_cross'):
                    cross_info = " [골든]"
                elif r.get('has_dead_cross'):
                    cross_info = " [데드]"
                trend = "상승" if r.get('is_bullish') else "하락"
                print(
                    f"  {i:2}. {r['name'][:10]:<10} ({r['code']}) | "
                    f"{format_price(r['current_price']):>12} | "
                    f"240일선 {dist:>+5.1f}% | {trend}추세{cross_info}"
                )

        # ===== 240일선 아래 섹션 =====
        ma240_below = screener.filter_ma_below(results, 240)
        if ma240_below:
            print_section(f"240일선 아래 ({len(ma240_below)}개) - 장기 하락")
            for i, r in enumerate(ma240_below[:15], 1):
                dist = r.get('dist_240', 0)
                cross_info = ""
                if r.get('has_golden_cross'):
                    cross_info = " [골든]"
                elif r.get('has_dead_cross'):
                    cross_info = " [데드]"
                print(
                    f"  {i:2}. {r['name'][:10]:<10} ({r['code']}) | "
                    f"{format_price(r['current_price']):>12} | "
                    f"240일선 {dist:>+5.1f}%{cross_info}"
                )

        # ===== 60일/120일선 동시 아래 =====
        both_below = [
            r for r in results
            if r.get('status_60') == 'below' and r.get('status_120') == 'below'
        ]
        both_below.sort(key=lambda x: x.get('dist_120', 0))

        if both_below:
            print_section(f"60일 & 120일선 모두 아래 ({len(both_below)}개) - 중기 약세")
            for i, r in enumerate(both_below[:15], 1):
                dist_60 = r.get('dist_60', 0)
                dist_120 = r.get('dist_120', 0)
                dist_240 = r.get('dist_240', 0)
                ma240_status = r.get('status_240', '')
                note_240 = ""
                if ma240_status in ['touch', 'below']:
                    note_240 = f" | 240일 {dist_240:+.1f}%"
                print(
                    f"  {i:2}. {r['name'][:10]:<10} ({r['code']}) | "
                    f"{format_price(r['current_price']):>12} | "
                    f"60일 {dist_60:>+5.1f}% | 120일 {dist_120:>+5.1f}%{note_240}"
                )

        # ===== 추세 강도 TOP 10 =====
        print_section("상승 추세 강도 TOP 10")
        bullish = screener.filter_bullish(results)[:10]
        for i, r in enumerate(bullish, 1):
            ma_diff = r.get('ma_diff_pct', 0)
            print(
                f"  {i:2}. {r['name'][:10]:<10} ({r['code']}) | "
                f"{format_price(r['current_price']):>12} | MA차이 {ma_diff:>+5.1f}%"
            )

        print_section("하락 추세 강도 TOP 10")
        bearish = screener.filter_bearish(results)[:10]
        for i, r in enumerate(bearish, 1):
            ma_diff = r.get('ma_diff_pct', 0)
            print(
                f"  {i:2}. {r['name'][:10]:<10} ({r['code']}) | "
                f"{format_price(r['current_price']):>12} | MA차이 {ma_diff:>+5.1f}%"
            )

        # ===== 주목 종목 (골든크로스 + 240일선 터치/아래) =====
        notable = [
            r for r in results
            if r.get('has_golden_cross') and r.get('status_240') in ['touch', 'below']
        ]
        if notable:
            print_section("주목 종목: 골든크로스 + 240일선 근처")
            print("  (상승 전환 신호 + 장기 저점 → 반등 가능성)")
            for i, r in enumerate(notable, 1):
                days = r.get('days_since_golden', '?')
                dist_240 = r.get('dist_240', 0)
                print(
                    f"  {i:2}. {r['name'][:10]:<10} ({r['code']}) | "
                    f"{format_price(r['current_price']):>12} | "
                    f"골든 {days}일전 | 240일선 {dist_240:>+5.1f}%"
                )

        # ===== 마무리 =====
        print("\n" + "="*70)
        print(f" 리포트 생성 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")

        return {
            'summary': summary,
            'golden_cross': golden_cross,
            'dead_cross': dead_cross,
            'ma240_touch': ma240_touch,
            'ma240_below': ma240_below,
            'both_below_60_120': both_below,
            'notable': notable,
            'all_results': results
        }

    finally:
        if output_file:
            sys.stdout = original_stdout
            file_handle.close()
            print(f"리포트 저장 완료: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='한국 주식 일일 종합 스크리닝 리포트'
    )
    parser.add_argument(
        '--lookback', type=int, default=7,
        help='크로스 감지 기간 - 최근 N일 (기본: 7)'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='결과 저장 파일 경로 (예: reports/daily_2024-01-22.txt)'
    )

    args = parser.parse_args()

    run(
        lookback_days=args.lookback,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
