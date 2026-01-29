"""
Korean Stock Golden/Dead Cross Screener
한국 주식 골든크로스/데드크로스 스크리너

Screens for stocks with recent MA crossover signals.

Usage:
    python scripts/screening/korean_crossover.py
    python scripts/screening/korean_crossover.py --short-ma 20 --long-ma 60
    python scripts/screening/korean_crossover.py --lookback 10
"""

import sys
import logging
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from screener.kospi_fetcher import KospiListFetcher
from screener import (
    StockScreener,
    MinPriceCondition,
    MinVolumeCondition,
    MACrossUpCondition,
    MACrossDownCondition,
    MATouchCondition,
    AboveMACondition,
    BelowMACondition,
)

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
    Main screening function.

    Args:
        short_ma: Short-term MA period
        long_ma: Long-term MA period
        lookback_days: Days to look back for crossover detection
        extra_ma: Additional MA periods for touch analysis
        min_volume: Minimum volume filter
        min_price: Minimum price filter
        limit: Output limit

    Returns:
        Screening results dict
    """
    if extra_ma is None:
        extra_ma = [240]

    print("\n" + "=" * 70)
    print(" Korean Stock Golden/Dead Cross Screener")
    print(f" Settings: {short_ma}d vs {long_ma}d MA | Lookback: {lookback_days} days")
    if extra_ma:
        print(f" Extra MA analysis: {extra_ma}")
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

    # 2. Screen for Golden Cross
    print(f"\n{'='*70}")
    print(f" Golden Cross ({short_ma}d crosses above {long_ma}d)")
    print(f"{'='*70}")

    screener_golden = StockScreener(max_workers=10)
    screener_golden.add_condition(MinPriceCondition(min_price))
    screener_golden.add_condition(MinVolumeCondition(min_volume))
    screener_golden.add_condition(MACrossUpCondition(
        short_period=short_ma,
        long_period=long_ma,
        lookback_days=lookback_days
    ))

    golden_results = screener_golden.run(tickers=tickers, show_progress=False)

    if golden_results:
        print(f"\nGolden Cross detected - {len(golden_results)} stocks:")
        for i, r in enumerate(golden_results[:limit], 1):
            name = ticker_info.get(r.ticker, r.name)[:10]
            cross_details = next(
                (cr.details for cr in r.condition_results
                 if f'ma_cross_up_{short_ma}_{long_ma}' in cr.condition_name),
                {}
            )
            cross_day = cross_details.get('cross_day', '?')
            short_val = cross_details.get('short_ma', 0)
            long_val = cross_details.get('long_ma', 0)
            print(
                f"  {i:3}. {name:<10} ({r.ticker}) | "
                f"Price: {r.current_price:>10,.0f} | "
                f"{short_ma}d: {short_val:>10,.0f} | "
                f"{long_ma}d: {long_val:>10,.0f} | "
                f"{cross_day}d ago"
            )
    else:
        print("  No golden cross detected")

    # 3. Screen for Dead Cross
    print(f"\n{'='*70}")
    print(f" Dead Cross ({short_ma}d crosses below {long_ma}d)")
    print(f"{'='*70}")

    screener_dead = StockScreener(max_workers=10)
    screener_dead.add_condition(MinPriceCondition(min_price))
    screener_dead.add_condition(MinVolumeCondition(min_volume))
    screener_dead.add_condition(MACrossDownCondition(
        short_period=short_ma,
        long_period=long_ma,
        lookback_days=lookback_days
    ))

    dead_results = screener_dead.run(tickers=tickers, show_progress=False)

    if dead_results:
        print(f"\nDead Cross detected - {len(dead_results)} stocks:")
        for i, r in enumerate(dead_results[:limit], 1):
            name = ticker_info.get(r.ticker, r.name)[:10]
            cross_details = next(
                (cr.details for cr in r.condition_results
                 if f'ma_cross_down_{short_ma}_{long_ma}' in cr.condition_name),
                {}
            )
            cross_day = cross_details.get('cross_day', '?')
            short_val = cross_details.get('short_ma', 0)
            long_val = cross_details.get('long_ma', 0)
            print(
                f"  {i:3}. {name:<10} ({r.ticker}) | "
                f"Price: {r.current_price:>10,.0f} | "
                f"{short_ma}d: {short_val:>10,.0f} | "
                f"{long_ma}d: {long_val:>10,.0f} | "
                f"{cross_day}d ago"
            )
    else:
        print("  No dead cross detected")

    # 4. Extra MA touch analysis
    extra_results = {}
    for period in extra_ma:
        print(f"\n{'='*70}")
        print(f" {period}-day MA Touch (±2%)")
        print(f"{'='*70}")

        screener_touch = StockScreener(max_workers=10)
        screener_touch.add_condition(MinPriceCondition(min_price))
        screener_touch.add_condition(MinVolumeCondition(min_volume))
        screener_touch.add_condition(MATouchCondition(period=period, threshold=0.02))

        touch_results = screener_touch.run(tickers=tickers, show_progress=False)

        if touch_results:
            print(f"\n{period}d MA touch - {len(touch_results)} stocks:")
            for i, r in enumerate(touch_results[:limit], 1):
                name = ticker_info.get(r.ticker, r.name)[:10]
                ma_details = next(
                    (cr.details for cr in r.condition_results
                     if f'ma_touch_{period}d' in cr.condition_name),
                    {}
                )
                distance = ma_details.get('distance_pct', 0) * 100
                print(
                    f"  {i:3}. {name:<10} ({r.ticker}) | "
                    f"Price: {r.current_price:>10,.0f} | "
                    f"Dist: {distance:>+6.1f}%"
                )
            extra_results[f'{period}_touch'] = touch_results

    # 5. Summary
    print(f"\n{'='*70}")
    print(" Summary")
    print(f"{'='*70}")
    print(f"  Golden Cross: {len(golden_results)} stocks")
    print(f"  Dead Cross: {len(dead_results)} stocks")
    for period in extra_ma:
        count = len(extra_results.get(f'{period}_touch', []))
        print(f"  {period}d MA Touch: {count} stocks")

    return {
        'golden_cross': golden_results,
        'dead_cross': dead_results,
        'extra_ma': extra_results,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Korean Stock Golden/Dead Cross Screener'
    )
    parser.add_argument(
        '--short-ma', type=int, default=20,
        help='Short-term MA period (default: 20)'
    )
    parser.add_argument(
        '--long-ma', type=int, default=60,
        help='Long-term MA period (default: 60)'
    )
    parser.add_argument(
        '--lookback', type=int, default=5,
        help='Lookback days for crossover detection (default: 5)'
    )
    parser.add_argument(
        '--extra-ma', type=int, nargs='+', default=[240],
        help='Extra MA periods for touch analysis (default: 240)'
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
        '--limit', type=int, default=30,
        help='Output limit (default: 30)'
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
