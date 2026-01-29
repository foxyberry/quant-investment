"""
Korean Stock Long-term MA Touch Screener
한국 주식 장기 이동평균선 터치 스크리너

Screens for stocks touching/below 120, 160, 200 day moving averages.

Usage:
    python scripts/screening/korean_ma_touch.py
    python scripts/screening/korean_ma_touch.py --periods 120 160 200
    python scripts/screening/korean_ma_touch.py --threshold 3.0
"""

import sys
import logging
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from screener.korean.kospi_fetcher import KospiListFetcher
from screener import (
    StockScreener,
    MinPriceCondition,
    MinVolumeCondition,
    MATouchCondition,
    BelowMACondition,
    OrCondition,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run(
    ma_periods: list = None,
    touch_threshold: float = 0.02,
    min_volume: int = 100000,
    min_price: float = 1000,
    limit: int = 20
) -> dict:
    """
    Main screening function.

    Args:
        ma_periods: MA periods to analyze (default: [120, 160, 200])
        touch_threshold: Touch threshold as decimal (default: 0.02 = 2%)
        min_volume: Minimum volume filter
        min_price: Minimum price filter
        limit: Output limit per category

    Returns:
        Screening results dict
    """
    if ma_periods is None:
        ma_periods = [120, 160, 200]

    print("\n" + "=" * 70)
    print(" Korean Stock Long-term MA Touch Screener")
    print(f" MA Periods: {ma_periods} | Touch Threshold: ±{touch_threshold*100:.1f}%")
    print("=" * 70)

    # 1. Fetch KOSPI stock list
    logger.info("Fetching KOSPI stock list...")
    fetcher = KospiListFetcher()
    kospi_list = fetcher.get_kospi_symbols()

    if not kospi_list:
        logger.error("Failed to fetch stock list")
        return {}

    tickers = [s['symbol'] for s in kospi_list]
    ticker_info = {s['symbol']: s['name'] for s in kospi_list}
    print(f"\nTotal stocks: {len(tickers)}")

    # 2. Screen for each MA period
    all_results = {}

    for period in ma_periods:
        print(f"\n{'='*70}")
        print(f" Screening: {period}-day MA Touch/Below")
        print(f"{'='*70}")

        # Build conditions for this period
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))

        # Touch condition: within threshold of MA
        screener.add_condition(MATouchCondition(period=period, threshold=touch_threshold))

        results = screener.run(tickers=tickers, show_progress=False)

        # Print results
        if results:
            print(f"\n{period}-day MA Touch (±{touch_threshold*100:.0f}%) - {len(results)} stocks:")
            for i, r in enumerate(results[:limit], 1):
                name = ticker_info.get(r.ticker, r.name)[:10]
                # Get MA details from condition results
                ma_details = next(
                    (cr.details for cr in r.condition_results if f'ma_touch_{period}d' in cr.condition_name),
                    {}
                )
                distance = ma_details.get('distance_pct', 0) * 100
                ma_value = ma_details.get('ma_value', 0)
                print(
                    f"  {i:3}. {name:<10} ({r.ticker}) | "
                    f"Price: {r.current_price:>10,.0f} | "
                    f"MA: {ma_value:>10,.0f} | "
                    f"Dist: {distance:>+6.1f}%"
                )
            all_results[f'{period}_touch'] = results
        else:
            print(f"  No stocks found")

        # Also check for stocks below MA
        screener_below = StockScreener(max_workers=10)
        screener_below.add_condition(MinPriceCondition(min_price))
        screener_below.add_condition(MinVolumeCondition(min_volume))
        screener_below.add_condition(BelowMACondition(period=period, max_distance_pct=-touch_threshold))

        below_results = screener_below.run(tickers=tickers, show_progress=False)

        if below_results:
            print(f"\n{period}-day MA Below (>{touch_threshold*100:.0f}% below) - {len(below_results)} stocks:")
            for i, r in enumerate(below_results[:limit], 1):
                name = ticker_info.get(r.ticker, r.name)[:10]
                ma_details = next(
                    (cr.details for cr in r.condition_results if f'below_ma_{period}d' in cr.condition_name),
                    {}
                )
                distance = ma_details.get('distance_pct', 0) * 100
                print(
                    f"  {i:3}. {name:<10} ({r.ticker}) | "
                    f"Price: {r.current_price:>10,.0f} | "
                    f"Dist: {distance:>+6.1f}%"
                )
            all_results[f'{period}_below'] = below_results

    # 3. Summary
    print(f"\n{'='*70}")
    print(" Summary")
    print(f"{'='*70}")
    for period in ma_periods:
        touch_count = len(all_results.get(f'{period}_touch', []))
        below_count = len(all_results.get(f'{period}_below', []))
        print(f"  {period}-day MA: {touch_count} touch, {below_count} below")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description='Korean Stock Long-term MA Touch Screener'
    )
    parser.add_argument(
        '--periods', type=int, nargs='+', default=[120, 160, 200],
        help='MA periods to analyze (default: 120 160 200)'
    )
    parser.add_argument(
        '--threshold', type=float, default=2.0,
        help='Touch threshold %% (default: 2.0)'
    )
    parser.add_argument(
        '--min-volume', type=int, default=100000,
        help='Minimum volume (default: 100,000)'
    )
    parser.add_argument(
        '--min-price', type=float, default=1000,
        help='Minimum price (default: 1,000 KRW)'
    )
    parser.add_argument(
        '--limit', type=int, default=20,
        help='Output limit (default: 20)'
    )

    args = parser.parse_args()

    run(
        ma_periods=args.periods,
        touch_threshold=args.threshold / 100,  # Convert to decimal
        min_volume=args.min_volume,
        min_price=args.min_price,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
