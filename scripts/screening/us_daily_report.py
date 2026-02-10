"""
US Stock Daily Comprehensive Screening Report
미국 주식 일일 종합 스크리닝 리포트

Generates a comprehensive daily screening report for S&P 500 stocks:
- Golden/Dead cross signals
- Long-term MA touch/below
- Trend strength analysis

Usage:
    python scripts/screening/us_daily_report.py
    python scripts/screening/us_daily_report.py --output report.txt
    python scripts/screening/us_daily_report.py --lookback 10
    python scripts/screening/us_daily_report.py --sector Technology
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from screener.us_fetcher import UsStockFetcher
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
    auto_save: bool = True,
    sector_filter: str = None
) -> dict:
    """
    Generate daily comprehensive report for US stocks.

    Args:
        lookback_days: Days to look back for crossover detection
        output_file: Output file path
        auto_save: Auto-save to reports/ folder
        sector_filter: Filter by sector (e.g., "Technology", "Healthcare")

    Returns:
        Comprehensive analysis results
    """
    report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    today_str = datetime.now().strftime('%Y-%m-%d')

    # Auto-save path
    if auto_save and output_file is None:
        output_file = f"reports/us_daily_{today_str}.txt"

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
        print("#" + "US Stock Daily Screening Report".center(60) + "        #")
        print("#" + " " * 68 + "#")
        print("#" * 70)
        print(f"\nReport Date: {report_date}")
        print(f"Settings: Crossover lookback {lookback_days}d | Touch threshold +/-2%")

        # 1. Fetch S&P 500 stock list
        logger.info("Fetching S&P 500 stock list...")
        fetcher = UsStockFetcher()
        stock_list = fetcher.get_sp500_symbols()

        if not stock_list:
            logger.error("Failed to fetch stock list")
            return {}

        # Sector filter
        if sector_filter:
            stock_list = [s for s in stock_list if sector_filter.lower() in s.get('sector', '').lower()]
            print(f"Sector Filter: {sector_filter}")

        tickers = [s['symbol'] for s in stock_list]
        ticker_info = {s['symbol']: s['name'] for s in stock_list}
        ticker_sector = {s['symbol']: s.get('sector', '') for s in stock_list}
        print(f"Universe: S&P 500 - {len(tickers)} stocks")

        # Common conditions (USD)
        min_price = 5  # $5 minimum
        min_volume = 500000  # 500K shares

        # 2. Golden Cross (50d crosses above 200d - classic signal)
        print_section("Golden Cross (50d crosses above 200d)")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(MACrossUpCondition(50, 200, lookback_days))

        golden_cross = screener.run(tickers=tickers, show_progress=False)
        if golden_cross:
            print(f"\nGolden Cross - {len(golden_cross)} stocks:")
            print(f"  {'#':>2}  {'Symbol':<6} {'Name':<20} {'Price':>10} {'Sector':<20} {'Days'}")
            print(f"  {'-'*2}  {'-'*6} {'-'*20} {'-'*10} {'-'*20} {'-'*4}")
            for i, r in enumerate(golden_cross[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:18]
                sector = ticker_sector.get(r.ticker, '')[:18]
                details = next((cr.details for cr in r.condition_results
                               if 'ma_cross_up' in cr.condition_name), {})
                cross_day = details.get('cross_day', '?')
                print(f"  {i:2}. {r.ticker:<6} {name:<20} ${r.current_price:>9,.2f} {sector:<20} {cross_day}d ago")
        else:
            print("  No golden cross detected")

        # 3. Dead Cross (50d crosses below 200d)
        print_section("Dead Cross (50d crosses below 200d)")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(MACrossDownCondition(50, 200, lookback_days))

        dead_cross = screener.run(tickers=tickers, show_progress=False)
        if dead_cross:
            print(f"\nDead Cross - {len(dead_cross)} stocks:")
            print(f"  {'#':>2}  {'Symbol':<6} {'Name':<20} {'Price':>10} {'Sector':<20} {'Days'}")
            print(f"  {'-'*2}  {'-'*6} {'-'*20} {'-'*10} {'-'*20} {'-'*4}")
            for i, r in enumerate(dead_cross[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:18]
                sector = ticker_sector.get(r.ticker, '')[:18]
                details = next((cr.details for cr in r.condition_results
                               if 'ma_cross_down' in cr.condition_name), {})
                cross_day = details.get('cross_day', '?')
                print(f"  {i:2}. {r.ticker:<6} {name:<20} ${r.current_price:>9,.2f} {sector:<20} {cross_day}d ago")
        else:
            print("  No dead cross detected")

        # 4. 200-day MA Touch (long-term support test)
        print_section("200-day MA Touch (+/-2%) - Long-term Support Test")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(MATouchCondition(period=200, threshold=0.02))

        ma200_touch = screener.run(tickers=tickers, show_progress=False)
        if ma200_touch:
            print(f"\n200d MA Touch - {len(ma200_touch)} stocks:")
            print(f"  {'#':>2}  {'Symbol':<6} {'Name':<20} {'Price':>10} {'Distance':>10}")
            print(f"  {'-'*2}  {'-'*6} {'-'*20} {'-'*10} {'-'*10}")
            for i, r in enumerate(ma200_touch[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:18]
                details = next((cr.details for cr in r.condition_results
                               if 'ma_touch_200d' in cr.condition_name), {})
                dist = details.get('distance_pct', 0) * 100
                print(f"  {i:2}. {r.ticker:<6} {name:<20} ${r.current_price:>9,.2f} {dist:>+9.1f}%")
        else:
            print("  No stocks touching 200d MA")

        # 5. 200-day MA Below (long-term decline)
        print_section("200-day MA Below - Long-term Decline")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(BelowMACondition(period=200, max_distance_pct=-0.02))

        ma200_below = screener.run(tickers=tickers, show_progress=False)
        ma200_below_sorted = sorted(
            ma200_below,
            key=lambda r: next((cr.details.get('distance_pct', 0) for cr in r.condition_results
                               if 'below_ma_200d' in cr.condition_name), 0)
        )
        if ma200_below_sorted:
            print(f"\n200d MA Below - {len(ma200_below_sorted)} stocks:")
            print(f"  {'#':>2}  {'Symbol':<6} {'Name':<20} {'Price':>10} {'Distance':>10}")
            print(f"  {'-'*2}  {'-'*6} {'-'*20} {'-'*10} {'-'*10}")
            for i, r in enumerate(ma200_below_sorted[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:18]
                details = next((cr.details for cr in r.condition_results
                               if 'below_ma_200d' in cr.condition_name), {})
                dist = details.get('distance_pct', 0) * 100
                print(f"  {i:2}. {r.ticker:<6} {name:<20} ${r.current_price:>9,.2f} {dist:>+9.1f}%")
        else:
            print("  No stocks below 200d MA")

        # 6. 50d & 200d Both Below (serious decline)
        print_section("50d & 200d MA Both Below - Serious Decline")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(BelowMACondition(period=50))
        screener.add_condition(BelowMACondition(period=200))

        both_below = screener.run(tickers=tickers, show_progress=False)
        both_below_sorted = sorted(
            both_below,
            key=lambda r: next((cr.details.get('distance_pct', 0) for cr in r.condition_results
                               if 'below_ma_200d' in cr.condition_name), 0)
        )
        if both_below_sorted:
            print(f"\nBelow both 50d & 200d MA - {len(both_below_sorted)} stocks:")
            print(f"  {'#':>2}  {'Symbol':<6} {'Name':<20} {'Price':>10} {'50d':>8} {'200d':>8}")
            print(f"  {'-'*2}  {'-'*6} {'-'*20} {'-'*10} {'-'*8} {'-'*8}")
            for i, r in enumerate(both_below_sorted[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:18]
                d50 = next((cr.details for cr in r.condition_results
                           if 'below_ma_50d' in cr.condition_name), {})
                d200 = next((cr.details for cr in r.condition_results
                            if 'below_ma_200d' in cr.condition_name), {})
                dist50 = d50.get('distance_pct', 0) * 100
                dist200 = d200.get('distance_pct', 0) * 100
                print(f"  {i:2}. {r.ticker:<6} {name:<20} ${r.current_price:>9,.2f} {dist50:>+7.1f}% {dist200:>+7.1f}%")
        else:
            print("  No stocks below both MAs")

        # 7. Strong Uptrend (Above both 50d & 200d)
        print_section("Strong Uptrend - Above both 50d & 200d MA")
        screener = StockScreener(max_workers=10)
        screener.add_condition(MinPriceCondition(min_price))
        screener.add_condition(MinVolumeCondition(min_volume))
        screener.add_condition(AboveMACondition(period=50, min_distance_pct=0.02))
        screener.add_condition(AboveMACondition(period=200, min_distance_pct=0.05))

        strong_uptrend = screener.run(tickers=tickers, show_progress=False)
        strong_uptrend_sorted = sorted(
            strong_uptrend,
            key=lambda r: next((cr.details.get('distance_pct', 0) for cr in r.condition_results
                               if 'above_ma_200d' in cr.condition_name), 0),
            reverse=True
        )
        if strong_uptrend_sorted:
            print(f"\nStrong Uptrend - {len(strong_uptrend_sorted)} stocks:")
            print(f"  {'#':>2}  {'Symbol':<6} {'Name':<20} {'Price':>10} {'50d':>8} {'200d':>8}")
            print(f"  {'-'*2}  {'-'*6} {'-'*20} {'-'*10} {'-'*8} {'-'*8}")
            for i, r in enumerate(strong_uptrend_sorted[:15], 1):
                name = ticker_info.get(r.ticker, r.name)[:18]
                d50 = next((cr.details for cr in r.condition_results
                           if 'above_ma_50d' in cr.condition_name), {})
                d200 = next((cr.details for cr in r.condition_results
                            if 'above_ma_200d' in cr.condition_name), {})
                dist50 = d50.get('distance_pct', 0) * 100
                dist200 = d200.get('distance_pct', 0) * 100
                print(f"  {i:2}. {r.ticker:<6} {name:<20} ${r.current_price:>9,.2f} {dist50:>+7.1f}% {dist200:>+7.1f}%")
        else:
            print("  No stocks in strong uptrend")

        # 8. Summary
        print_section("Summary")
        print(f"""
  Universe: S&P 500 ({len(tickers)} stocks)

  Bullish Signals:
    Golden Cross (50/200): {len(golden_cross)} stocks
    Strong Uptrend: {len(strong_uptrend_sorted)} stocks

  Bearish Signals:
    Dead Cross (50/200): {len(dead_cross)} stocks
    200d MA Below: {len(ma200_below_sorted)} stocks
    50d & 200d Both Below: {len(both_below_sorted)} stocks

  Watch:
    200d MA Touch: {len(ma200_touch)} stocks
""")

        print("\n" + "=" * 70)
        print(f" Report Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")

        return {
            'golden_cross': golden_cross,
            'dead_cross': dead_cross,
            'ma200_touch': ma200_touch,
            'ma200_below': ma200_below_sorted,
            'both_below': both_below_sorted,
            'strong_uptrend': strong_uptrend_sorted,
        }

    finally:
        if file_handle:
            sys.stdout = original_stdout
            file_handle.close()
            print(f"\nReport saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='US Stock Daily Comprehensive Screening Report'
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
    parser.add_argument(
        '--sector', type=str, default=None,
        help='Filter by sector (e.g., Technology, Healthcare, Financials)'
    )

    args = parser.parse_args()

    run(
        lookback_days=args.lookback,
        output_file=args.output,
        auto_save=not args.no_save,
        sector_filter=args.sector
    )


if __name__ == "__main__":
    main()
