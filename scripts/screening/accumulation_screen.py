#!/usr/bin/env python3
"""
Quiet Accumulation Zone Screening Script
조용한 매집 구간 탐지 스크리닝

Usage:
    # 단일 종목 테스트
    python scripts/screening/accumulation_screen.py --ticker 005930.KS

    # 기본 프리셋 실행
    python scripts/screening/accumulation_screen.py --preset accumulation_basic

    # OBV 다이버전스 프리셋
    python scripts/screening/accumulation_screen.py --preset accumulation_obv

    # 전체 프리셋 (다이버전스 OR 조건)
    python scripts/screening/accumulation_screen.py --preset accumulation_full

    # 커스텀 파라미터
    python scripts/screening/accumulation_screen.py --preset accumulation_basic --bb-width 8.0 --volume-mult 0.7

    # 유니버스 지정
    python scripts/screening/accumulation_screen.py --preset accumulation_basic --universe KOSDAQ
"""

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
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


def run_preset(
    preset_name: str,
    universe: str = "KOSPI",
    **kwargs
):
    """프리셋으로 스크리닝 실행"""
    print(f"\n{'='*60}")
    print(f"  Quiet Accumulation Zone Screening")
    print(f"  Preset: {preset_name}")
    print(f"  Universe: {universe}")
    print(f"{'='*60}\n")

    conditions = get_preset(preset_name, **kwargs)

    print("Conditions:")
    for c in conditions:
        print(f"  - {c}")
    print()

    screener = StockScreener(conditions=conditions)
    results = screener.run(universe=universe)

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
        help="Universe (KOSPI/KOSDAQ/ALL, default: KOSPI)"
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
        run_preset(args.preset, args.universe, **preset_kwargs)


if __name__ == "__main__":
    main()
