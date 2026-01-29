"""
Korean Stock Below MA Screener
한국 주식 이동평균선 하향 스크리너

Screens for stocks trading below their moving averages.

Usage:
    python scripts/screening/korean_ma_below.py
    python scripts/screening/korean_ma_below.py --short-ma 60 --long-ma 120
    python scripts/screening/korean_ma_below.py --limit 30
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
    BelowMACondition,
    AndCondition,
)

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
) -> dict:
    """
    Main screening function.

    Args:
        short_ma: Short-term MA period
        long_ma: Long-term MA period
        min_volume: Minimum volume filter
        min_price: Minimum price filter
        limit: Output limit

    Returns:
        Screening results dict
    """
    print("\n" + "=" * 60)
    print(" Korean Stock Below MA Screener")
    print(f" MA Periods: {short_ma}d / {long_ma}d")
    print("=" * 60)

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

    # 2. Screen for stocks below short-term MA
    print(f"\n{'='*60}")
    print(f" Below {short_ma}-day MA")
    print(f"{'='*60}")

    screener_short = StockScreener(max_workers=10)
    screener_short.add_condition(MinPriceCondition(min_price))
    screener_short.add_condition(MinVolumeCondition(min_volume))
    screener_short.add_condition(BelowMACondition(period=short_ma))

    below_short = screener_short.run(tickers=tickers, show_progress=False)

    # Sort by distance (most below first)
    below_short_sorted = sorted(
        below_short,
        key=lambda r: next(
            (cr.details.get('distance_pct', 0) for cr in r.condition_results
             if f'below_ma_{short_ma}d' in cr.condition_name),
            0
        )
    )

    if below_short_sorted:
        print(f"\nBelow {short_ma}d MA - {len(below_short_sorted)} stocks (sorted by distance):")
        for i, r in enumerate(below_short_sorted[:limit], 1):
            name = ticker_info.get(r.ticker, r.name)[:10]
            ma_details = next(
                (cr.details for cr in r.condition_results
                 if f'below_ma_{short_ma}d' in cr.condition_name),
                {}
            )
            distance = ma_details.get('distance_pct', 0) * 100
            ma_value = ma_details.get('ma_value', 0)
            print(
                f"  {i:3}. {name:<10} ({r.ticker}) | "
                f"Price: {r.current_price:>10,.0f} | "
                f"{short_ma}d MA: {ma_value:>10,.0f} | "
                f"Dist: {distance:>+6.1f}%"
            )
    else:
        print("  No stocks found")

    # 3. Screen for stocks below long-term MA
    print(f"\n{'='*60}")
    print(f" Below {long_ma}-day MA")
    print(f"{'='*60}")

    screener_long = StockScreener(max_workers=10)
    screener_long.add_condition(MinPriceCondition(min_price))
    screener_long.add_condition(MinVolumeCondition(min_volume))
    screener_long.add_condition(BelowMACondition(period=long_ma))

    below_long = screener_long.run(tickers=tickers, show_progress=False)

    below_long_sorted = sorted(
        below_long,
        key=lambda r: next(
            (cr.details.get('distance_pct', 0) for cr in r.condition_results
             if f'below_ma_{long_ma}d' in cr.condition_name),
            0
        )
    )

    if below_long_sorted:
        print(f"\nBelow {long_ma}d MA - {len(below_long_sorted)} stocks (sorted by distance):")
        for i, r in enumerate(below_long_sorted[:limit], 1):
            name = ticker_info.get(r.ticker, r.name)[:10]
            ma_details = next(
                (cr.details for cr in r.condition_results
                 if f'below_ma_{long_ma}d' in cr.condition_name),
                {}
            )
            distance = ma_details.get('distance_pct', 0) * 100
            ma_value = ma_details.get('ma_value', 0)
            print(
                f"  {i:3}. {name:<10} ({r.ticker}) | "
                f"Price: {r.current_price:>10,.0f} | "
                f"{long_ma}d MA: {ma_value:>10,.0f} | "
                f"Dist: {distance:>+6.1f}%"
            )
    else:
        print("  No stocks found")

    # 4. Screen for stocks below BOTH MAs
    print(f"\n{'='*60}")
    print(f" Below BOTH {short_ma}d & {long_ma}d MA (Severe Decline)")
    print(f"{'='*60}")

    screener_both = StockScreener(max_workers=10)
    screener_both.add_condition(MinPriceCondition(min_price))
    screener_both.add_condition(MinVolumeCondition(min_volume))
    screener_both.add_condition(BelowMACondition(period=short_ma))
    screener_both.add_condition(BelowMACondition(period=long_ma))

    below_both = screener_both.run(tickers=tickers, show_progress=False)

    below_both_sorted = sorted(
        below_both,
        key=lambda r: next(
            (cr.details.get('distance_pct', 0) for cr in r.condition_results
             if f'below_ma_{long_ma}d' in cr.condition_name),
            0
        )
    )

    if below_both_sorted:
        print(f"\nBelow both MAs - {len(below_both_sorted)} stocks:")
        for i, r in enumerate(below_both_sorted[:limit], 1):
            name = ticker_info.get(r.ticker, r.name)[:10]
            short_details = next(
                (cr.details for cr in r.condition_results
                 if f'below_ma_{short_ma}d' in cr.condition_name),
                {}
            )
            long_details = next(
                (cr.details for cr in r.condition_results
                 if f'below_ma_{long_ma}d' in cr.condition_name),
                {}
            )
            dist_short = short_details.get('distance_pct', 0) * 100
            dist_long = long_details.get('distance_pct', 0) * 100
            print(
                f"  {i:3}. {name:<10} ({r.ticker}) | "
                f"Price: {r.current_price:>10,.0f} | "
                f"{short_ma}d: {dist_short:>+6.1f}% | "
                f"{long_ma}d: {dist_long:>+6.1f}%"
            )
    else:
        print("  No stocks found")

    # 5. Summary
    print(f"\n{'='*60}")
    print(" Summary")
    print(f"{'='*60}")
    print(f"  Analyzed: {len(tickers)} stocks")
    print(f"  Below {short_ma}d MA: {len(below_short_sorted)}")
    print(f"  Below {long_ma}d MA: {len(below_long_sorted)}")
    print(f"  Below both: {len(below_both_sorted)}")

    return {
        'below_short': below_short_sorted,
        'below_long': below_long_sorted,
        'below_both': below_both_sorted,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Korean Stock Below MA Screener'
    )
    parser.add_argument(
        '--short-ma', type=int, default=60,
        help='Short-term MA period (default: 60)'
    )
    parser.add_argument(
        '--long-ma', type=int, default=120,
        help='Long-term MA period (default: 120)'
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
        '--limit', type=int, default=50,
        help='Output limit (default: 50)'
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
