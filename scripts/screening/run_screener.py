#!/usr/bin/env python3
"""
종목 스크리닝 실행 스크립트

Usage:
    # 프리셋 사용
    python scripts/screening/run_screener.py --preset ma_touch_160

    # 프리셋 목록 보기
    python scripts/screening/run_screener.py --list-presets

    # 커스텀 조건 (코드로)
    python scripts/screening/run_screener.py --custom

    # 다중 유니버스
    python scripts/screening/run_screener.py --preset ma_touch_160 --universe KOSPI,KOSDAQ
    python scripts/screening/run_screener.py --preset ma_touch_160 --universes KOSPI --universes KOSDAQ
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
    # Conditions
    MinPriceCondition,
    MATouchCondition,
    RSIOversoldCondition,
    VolumeAboveAvgCondition,
    AndCondition,
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


def run_preset(preset_name: str, universe: str = "KOSPI", universes: List[str] | None = None):
    """프리셋으로 스크리닝 실행"""
    resolved_universes = parse_universe_inputs(universe, universes)
    print(f"\n🎯 프리셋 '{preset_name}' 실행")
    print(f"   Universes: {', '.join(resolved_universes)}")

    conditions = get_preset(preset_name)
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
        print(f"\n📋 매칭 종목 ({len(results)}개):")
        for r in results:
            print(f"  • {r.ticker} ({r.name})")
            print(f"    가격: {r.current_price:,.0f}원")
            for cr in r.condition_results:
                status = "✓" if cr.matched else "✗"
                print(f"    {status} {cr.condition_name}")

        # DataFrame으로 변환
        df = screener.to_dataframe(results)
        print(f"\n📊 결과 DataFrame:")
        print(df[['ticker', 'name', 'current_price', 'matched']].to_string(index=False))
    else:
        print("\n❌ 매칭된 종목이 없습니다.")


def run_custom_example():
    """커스텀 조건 예제"""
    print("\n🔧 커스텀 조건 예제")

    # 방법 1: add_condition() 체이닝
    screener = StockScreener()
    screener.add_condition(MinPriceCondition(5000))
    screener.add_condition(MATouchCondition(period=120, threshold=0.03))

    # 방법 2: AndCondition으로 묶기
    # condition = AndCondition([
    #     MinPriceCondition(5000),
    #     MATouchCondition(period=120, threshold=0.03),
    #     RSIOversoldCondition(threshold=40)
    # ])
    # screener = StockScreener(conditions=[condition])

    results = screener.run(universe="KOSPI")

    if results:
        print(f"\n📋 매칭 종목 ({len(results)}개):")
        for r in results:
            print(f"  • {r.ticker} ({r.name}) - {r.current_price:,.0f}원")
    else:
        print("\n❌ 매칭된 종목이 없습니다.")


def run_single_stock(ticker: str):
    """단일 종목 검사"""
    print(f"\n🔍 단일 종목 검사: {ticker}")

    screener = StockScreener()
    screener.add_condition(MinPriceCondition(1000))
    screener.add_condition(MATouchCondition(period=160, threshold=0.05))
    screener.add_condition(RSIOversoldCondition(threshold=50))

    result = screener.run_single(ticker)

    print(f"\n결과: {'✅ 매칭' if result.matched else '❌ 미매칭'}")
    print(f"종목: {result.name}")
    print(f"가격: {result.current_price:,.0f}원")
    print(f"\n조건별 결과:")
    for cr in result.condition_results:
        status = "✓" if cr.matched else "✗"
        print(f"  {status} {cr.condition_name}")
        for k, v in cr.details.items():
            if isinstance(v, float):
                print(f"      {k}: {v:.4f}")
            else:
                print(f"      {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="종목 스크리닝")
    parser.add_argument("--preset", type=str, help="사용할 프리셋 이름")
    parser.add_argument("--list-presets", action="store_true", help="프리셋 목록 표시")
    parser.add_argument("--custom", action="store_true", help="커스텀 조건 예제 실행")
    parser.add_argument("--ticker", type=str, help="단일 종목 검사 (예: 035420.KS)")
    parser.add_argument("--universe", type=str, default="KOSPI", help="유니버스 단일/CSV (예: KOSPI,KOSDAQ)")
    parser.add_argument("--universes", action="append", default=[], help="유니버스 반복 지정 (예: --universes KOSPI --universes KOSDAQ)")

    args = parser.parse_args()

    if args.list_presets:
        print("\n📚 사용 가능한 프리셋:")
        for name in list_presets():
            print(f"  • {name}")
        return

    if args.preset:
        run_preset(args.preset, args.universe, args.universes)
    elif args.custom:
        run_custom_example()
    elif args.ticker:
        run_single_stock(args.ticker)
    else:
        # 기본: 160일선 터치 프리셋
        run_preset("ma_touch_160", args.universe, args.universes)


if __name__ == "__main__":
    main()
