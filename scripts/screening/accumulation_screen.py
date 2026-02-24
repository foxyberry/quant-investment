#!/usr/bin/env python3
"""
Quiet Accumulation Zone Screening Script
조용한 매집 구간 탐지 스크리닝

프리셋별 차이점:
================

accumulation_basic (기본)
    조건: BB수축 + 거래량↓ + 가격횡보
    특징: 넓은 범위의 매집 후보, 결과 많음 (~200개)
    신뢰도: 낮음

accumulation_obv (OBV 다이버전스)
    조건: basic + OBV 상승 다이버전스
    특징: 가격은 횡보인데 OBV가 상승하는 종목만 필터
    신뢰도: 중간 (가장 추천)

accumulation_full (전체 다이버전스)
    조건: basic + (OBV or Stoch or VPCI 다이버전스 중 하나)
    특징: 3가지 다이버전스 신호 중 하나라도 충족
    신뢰도: 중간

조건 상세:
=========
- 가격 >= 5,000원 (저가주 제외)
- 볼린저밴드 폭 <= 15% (변동성 낮음, 수축 구간)
- 거래량 <= 평균의 1.0배 (조용한 거래)
- 20일 가격변동폭 <= 10% (횡보 구간)
- OBV 다이버전스: 가격 횡보 + OBV 상승 (매집 신호)

Usage:
    # 단일 종목 테스트
    python scripts/screening/accumulation_screen.py --ticker 005930.KS

    # 기본 프리셋 실행
    python scripts/screening/accumulation_screen.py --preset accumulation_basic

    # OBV 다이버전스 프리셋 (추천)
    python scripts/screening/accumulation_screen.py --preset accumulation_obv

    # 전체 프리셋 (다이버전스 OR 조건)
    python scripts/screening/accumulation_screen.py --preset accumulation_full

    # 커스텀 파라미터 (더 엄격한 조건)
    python scripts/screening/accumulation_screen.py --preset accumulation_basic --bb-width 8.0 --volume-mult 0.7

    # 유니버스 지정
    python scripts/screening/accumulation_screen.py --preset accumulation_basic --universe KOSDAQ

    # 다중 유니버스 지정
    python scripts/screening/accumulation_screen.py --preset accumulation_basic --universe KOSPI,KOSDAQ
    python scripts/screening/accumulation_screen.py --preset accumulation_basic --universes KOSPI --universes KOSDAQ

커스텀 파라미터:
    --bb-width 8.0     볼린저밴드 폭 8% 이하 (더 수축된 종목)
    --volume-mult 0.7  평균의 70% 이하 거래량 (더 조용한 종목)
    --min-price 10000  최소가 1만원 이상
    --price-range 5.0  20일 가격변동 5% 이하 (더 좁은 횡보)
"""

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
from typing import List
from screener import (
    StockScreener,
    get_preset,
    list_presets,
    # Accumulation conditions
    MinPriceCondition,
    BollingerWidthCondition,
    VolumeBelowAvgCondition,
    PriceFlatCondition,
    OBVTrendCondition,
    OBVDivergenceCondition,
    StochasticDivergenceCondition,
    VPCIDivergenceCondition,
    OrCondition,
)


def parse_universe_inputs(universe: str, universes: List[str] | None = None) -> List[str]:
    """Parse single/csv/repeated universe inputs with stable dedupe."""
    tokens: List[str] = []
    values = list(universes or [])
    if universe:
        values.append(universe)
    for value in values:
        for item in value.split(","):
            token = item.strip().upper()
            if token:
                tokens.append(token)

    resolved: List[str] = []
    seen = set()
    for token in tokens or ["KOSPI"]:
        if token not in seen:
            resolved.append(token)
            seen.add(token)
    return resolved


def run_preset(
    preset_name: str,
    universe: str = "KOSPI",
    universes: List[str] | None = None,
    **kwargs
):
    """프리셋으로 스크리닝 실행"""
    resolved_universes = parse_universe_inputs(universe, universes)
    print(f"\n{'='*60}")
    print(f"  Quiet Accumulation Zone Screening")
    print(f"  Preset: {preset_name}")
    print(f"  Universe: {', '.join(resolved_universes)}")
    print(f"{'='*60}\n")

    conditions = get_preset(preset_name, **kwargs)

    print("Conditions:")
    for c in conditions:
        print(f"  - {c}")
    print()

    merged = []
    seen_tickers = set()
    for selected_universe in resolved_universes:
        screener = StockScreener(conditions=conditions)
        results = screener.run(universe=selected_universe)
        for result in results:
            if result.ticker in seen_tickers:
                continue
            seen_tickers.add(result.ticker)
            merged.append(result)
    results = merged

    if results:
        print(f"\nMatched Stocks ({len(results)}):\n")
        for r in results:
            print(f"  {r.ticker} ({r.name})")
            print(f"    Price: {r.current_price:,.0f}")
            for cr in r.condition_results:
                status = "PASS" if cr.matched else "FAIL"
                print(f"    [{status}] {cr.condition_name}")
            print()

        # DataFrame 출력
        df = screener.to_dataframe(results)
        print("\nResult DataFrame:")
        print(df[['ticker', 'name', 'current_price', 'matched']].to_string(index=False))
    else:
        print("\nNo matching stocks found.")

    return results


def run_single_stock(ticker: str, preset_name: str = "accumulation_basic", **kwargs):
    """단일 종목 검사"""
    print(f"\n{'='*60}")
    print(f"  Single Stock Analysis: {ticker}")
    print(f"  Preset: {preset_name}")
    print(f"{'='*60}\n")

    conditions = get_preset(preset_name, **kwargs)

    print("Conditions:")
    for c in conditions:
        print(f"  - {c}")
    print()

    screener = StockScreener(conditions=conditions)
    result = screener.run_single(ticker)

    print(f"Result: {'MATCHED' if result.matched else 'NOT MATCHED'}")
    print(f"Stock: {result.name}")
    print(f"Price: {result.current_price:,.0f}")
    print(f"\nCondition Details:")

    for cr in result.condition_results:
        status = "PASS" if cr.matched else "FAIL"
        print(f"\n  [{status}] {cr.condition_name}")
        for k, v in cr.details.items():
            if isinstance(v, float):
                print(f"      {k}: {v:.4f}")
            else:
                print(f"      {k}: {v}")

    return result


def run_custom_example():
    """커스텀 조건 예제"""
    print(f"\n{'='*60}")
    print(f"  Custom Accumulation Screen Example")
    print(f"{'='*60}\n")

    # 커스텀 조건 조합
    conditions = [
        MinPriceCondition(5000),
        BollingerWidthCondition(max_width_pct=8.0),
        VolumeBelowAvgCondition(multiplier=0.7),
        OBVTrendCondition(direction="up", lookback=20),
    ]

    print("Custom Conditions:")
    for c in conditions:
        print(f"  - {c}")
    print()

    screener = StockScreener(conditions=conditions)
    results = screener.run(universe="KOSPI")

    if results:
        print(f"\nMatched Stocks ({len(results)}):")
        for r in results:
            print(f"  - {r.ticker} ({r.name}) - {r.current_price:,.0f}")
    else:
        print("\nNo matching stocks found.")


def main():
    parser = argparse.ArgumentParser(
        description="Quiet Accumulation Zone Screening",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single stock test
  python accumulation_screen.py --ticker 005930.KS

  # Run with preset
  python accumulation_screen.py --preset accumulation_basic

  # Custom parameters
  python accumulation_screen.py --preset accumulation_obv --bb-width 8.0

  # Different universe
  python accumulation_screen.py --preset accumulation_full --universe KOSDAQ
        """
    )

    parser.add_argument(
        "--ticker", type=str,
        help="Single stock ticker (e.g., 005930.KS)"
    )
    parser.add_argument(
        "--preset", type=str,
        choices=["accumulation_basic", "accumulation_obv", "accumulation_full"],
        default="accumulation_basic",
        help="Preset to use (default: accumulation_basic)"
    )
    parser.add_argument(
        "--universe", type=str, default="KOSPI",
        help="Universe single/CSV (default: KOSPI, example: KOSPI,KOSDAQ)"
    )
    parser.add_argument(
        "--universes", action="append", default=[],
        help="Universe repeated flags (example: --universes KOSPI --universes KOSDAQ)"
    )
    parser.add_argument(
        "--custom", action="store_true",
        help="Run custom example"
    )
    parser.add_argument(
        "--list-presets", action="store_true",
        help="List all available presets"
    )

    # Accumulation parameters
    parser.add_argument(
        "--min-price", type=int, default=5000,
        help="Minimum price (default: 5000)"
    )
    parser.add_argument(
        "--bb-width", type=float, default=15.0,
        help="Max Bollinger Band width %% (default: 15.0)"
    )
    parser.add_argument(
        "--volume-mult", type=float, default=1.0,
        help="Volume below average multiplier (default: 1.0)"
    )
    parser.add_argument(
        "--price-range", type=float, default=10.0,
        help="Max price range %% for flat detection (default: 10.0)"
    )

    args = parser.parse_args()

    if args.list_presets:
        print("\nAvailable Presets:")
        for name in list_presets():
            print(f"  - {name}")
        print("\nAccumulation Presets:")
        print("  - accumulation_basic: BB squeeze + Low volume + Price flat")
        print("  - accumulation_obv: Basic + OBV divergence")
        print("  - accumulation_full: Basic + Any divergence (OBV/Stoch/VPCI)")
        return

    # 프리셋 파라미터
    preset_kwargs = {
        "min_price": args.min_price,
        "bb_max_width": args.bb_width,
        "volume_multiplier": args.volume_mult,
        "price_max_range": args.price_range,
    }

    if args.custom:
        run_custom_example()
    elif args.ticker:
        run_single_stock(args.ticker, args.preset, **preset_kwargs)
    else:
        run_preset(args.preset, args.universe, args.universes, **preset_kwargs)


if __name__ == "__main__":
    main()
