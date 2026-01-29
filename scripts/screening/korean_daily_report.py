"""
Korean Stock Daily Comprehensive Screening Report
한국 주식 일일 종합 스크리닝 리포트

Generates a comprehensive daily screening report including:
- Golden/Dead cross signals
- Long-term MA touch/below
- Trend strength analysis

Usage:
    python scripts/screening/korean_daily_report.py
    python scripts/screening/korean_daily_report.py --output report.txt
    python scripts/screening/korean_daily_report.py --lookback 10
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

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
    BelowMACondition,
    AboveMACondition,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TeeOutput:
    """Output to both terminal and file."""
    def __init__(self, file_handle, terminal):
        self.file = file_handle
        self.terminal = terminal

    def write(self, message):
        self.terminal.write(message)
        self.file.write(message)

    def flush(self):
        self.terminal.flush()
        self.file.flush()


def print_section(title: str, width: int = 70):
    """Print section header."""
    print(f"\n{'='*width}")
    print(f" {title}")
    print(f"{'='*width}")


def run(
    lookback_days: int = 7,
    output_file: str = None,
    auto_save: bool = True
) -> dict:
    """
    Generate daily comprehensive report.

    Args:
        lookback_days: Days to look back for crossover detection
        output_file: Output file path
        auto_save: Auto-save to reports/ folder

    Returns:
        Comprehensive analysis results
    """
    report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    today_str = datetime.now().strftime('%Y-%m-%d')

    # Auto-save path
    if auto_save and output_file is None:
        output_file = f"reports/daily_{today_str}.txt"

    # Setup output redirection
    original_stdout = sys.stdout
    file_handle = None
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        file_handle = open(output_path, 'w', encoding='utf-8')
        sys.stdout = TeeOutput(file_handle, original_stdout)

    try:
        print("\n" + "#" * 70)
        print("#" + " " * 68 + "#")
        print("#" + "Korean Stock Daily Screening Report".center(60) + "      #")
        print("#" + " " * 68 + "#")
        print("#" * 70)
        print(f"\nReport Date: {report_date}")
        print(f"Settings: Crossover lookback {lookback_days}d | Touch threshold ±2%")

        # 1. Fetch KOSPI stock list
        logger.info("Fetching KOSPI stock list...")
        fetcher = KospiListFetcher()
        kospi_list = fetcher.get_kospi_symbols()

        if not kospi_list:
            logger.error("Failed to fetch stock list")
            return {}

        tickers = [s['symbol'] for s in kospi_list]
        ticker_info = {s['symbol']: s['name'] for s in kospi_list}
        print(f"Universe: KOSPI {len(tickers)} stocks")

        # Common conditions
        min_price = 1000
        min_volume = 100000

        # 2. Golden Cross
        print_section(f"Golden Cross (20d crosses above 60d)")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(MACrossUpCondition(20, 60, lookback_days))

        golden_cross = screener.run(tickers=tickers, show_progress=False)
        if golden_cross:
            print(f"\nGolden Cross - {len(golden_cross)} stocks:")
            for i, r in enumerate(golden_cross[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:10]
                details = next((cr.details for cr in r.condition_results
                               if 'ma_cross_up' in cr.condition_name), {})
                cross_day = details.get('cross_day', '?')
                print(f"  {i:2}. {name:<10} ({r.ticker}) | {r.current_price:>10,.0f} | {cross_day}d ago")
        else:
            print("  No golden cross detected")

        # 3. Dead Cross
        print_section(f"Dead Cross (20d crosses below 60d)")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(MACrossDownCondition(20, 60, lookback_days))

        dead_cross = screener.run(tickers=tickers, show_progress=False)
        if dead_cross:
            print(f"\nDead Cross - {len(dead_cross)} stocks:")
            for i, r in enumerate(dead_cross[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:10]
                details = next((cr.details for cr in r.condition_results
                               if 'ma_cross_down' in cr.condition_name), {})
                cross_day = details.get('cross_day', '?')
                print(f"  {i:2}. {name:<10} ({r.ticker}) | {r.current_price:>10,.0f} | {cross_day}d ago")
        else:
            print("  No dead cross detected")

        # 4. 240-day MA Touch
        print_section("240-day MA Touch (±2%) - Long-term Support Test")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(MATouchCondition(period=240, threshold=0.02))

        ma240_touch = screener.run(tickers=tickers, show_progress=False)
        if ma240_touch:
            print(f"\n240d MA Touch - {len(ma240_touch)} stocks:")
            for i, r in enumerate(ma240_touch[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:10]
                details = next((cr.details for cr in r.condition_results
                               if 'ma_touch_240d' in cr.condition_name), {})
                dist = details.get('distance_pct', 0) * 100
                print(f"  {i:2}. {name:<10} ({r.ticker}) | {r.current_price:>10,.0f} | {dist:>+5.1f}%")
        else:
            print("  No stocks touching 240d MA")

        # 5. 240-day MA Below
        print_section("240-day MA Below - Long-term Decline")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(BelowMACondition(period=240, max_distance_pct=-0.02))

        ma240_below = screener.run(tickers=tickers, show_progress=False)
        ma240_below_sorted = sorted(
            ma240_below,
            key=lambda r: next((cr.details.get('distance_pct', 0) for cr in r.condition_results
                               if 'below_ma_240d' in cr.condition_name), 0)
        )
        if ma240_below_sorted:
            print(f"\n240d MA Below - {len(ma240_below_sorted)} stocks:")
            for i, r in enumerate(ma240_below_sorted[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:10]
                details = next((cr.details for cr in r.condition_results
                               if 'below_ma_240d' in cr.condition_name), {})
                dist = details.get('distance_pct', 0) * 100
                print(f"  {i:2}. {name:<10} ({r.ticker}) | {r.current_price:>10,.0f} | {dist:>+5.1f}%")
        else:
            print("  No stocks below 240d MA")

        # 6. 60d & 120d Both Below
        print_section("60d & 120d MA Both Below - Medium-term Weakness")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(BelowMACondition(period=60))
        screener.add_condition(BelowMACondition(period=120))

        both_below = screener.run(tickers=tickers, show_progress=False)
        both_below_sorted = sorted(
            both_below,
            key=lambda r: next((cr.details.get('distance_pct', 0) for cr in r.condition_results
                               if 'below_ma_120d' in cr.condition_name), 0)
        )
        if both_below_sorted:
            print(f"\nBelow both 60d & 120d MA - {len(both_below_sorted)} stocks:")
            for i, r in enumerate(both_below_sorted[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:10]
                d60 = next((cr.details for cr in r.condition_results
                           if 'below_ma_60d' in cr.condition_name), {})
                d120 = next((cr.details for cr in r.condition_results
                            if 'below_ma_120d' in cr.condition_name), {})
                dist60 = d60.get('distance_pct', 0) * 100
                dist120 = d120.get('distance_pct', 0) * 100
                print(f"  {i:2}. {name:<10} ({r.ticker}) | {r.current_price:>10,.0f} | 60d: {dist60:>+5.1f}% | 120d: {dist120:>+5.1f}%")
        else:
            print("  No stocks below both MAs")

        # 7. Summary
        print_section("Summary")
        print(f"""
  Golden Cross: {len(golden_cross)} stocks
  Dead Cross: {len(dead_cross)} stocks
  240d MA Touch: {len(ma240_touch)} stocks
  240d MA Below: {len(ma240_below_sorted)} stocks
  60d & 120d Both Below: {len(both_below_sorted)} stocks
""")

        print("\n" + "=" * 70)
        print(f" Report Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")

        return {
            'golden_cross': golden_cross,
            'dead_cross': dead_cross,
            'ma240_touch': ma240_touch,
            'ma240_below': ma240_below_sorted,
            'both_below': both_below_sorted,
        }

    finally:
        if file_handle:
            sys.stdout = original_stdout
            file_handle.close()
            print(f"\nReport saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Korean Stock Daily Comprehensive Screening Report'
    )
    parser.add_argument(
        '--lookback', type=int, default=7,
        help='Lookback days for crossover detection (default: 7)'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='Output file path'
    )
    parser.add_argument(
        '--no-save', action='store_true',
        help='Do not save to file (terminal only)'
    )

    args = parser.parse_args()

    run(
        lookback_days=args.lookback,
        output_file=args.output,
        auto_save=not args.no_save
    )


if __name__ == "__main__":
    main()
