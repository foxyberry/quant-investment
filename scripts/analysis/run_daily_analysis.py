#!/usr/bin/env python
"""
Daily Stock Analysis Pipeline
일일 주식 분석 파이프라인

Automated pipeline for:
1. Screening 240d MA touch stocks (KOSPI + S&P 500)
2. Enriching with technical, fundamental, news data
3. Analyzing with Claude AI (API or Claude Code)
4. Generating report with position recommendations

Usage:
    # Full analysis with Claude API (requires ANTHROPIC_API_KEY)
    python scripts/analysis/run_daily_analysis.py

    # Single market
    python scripts/analysis/run_daily_analysis.py --market KOSPI
    python scripts/analysis/run_daily_analysis.py --market SP500

    # Skip Claude analysis (enrichment only)
    python scripts/analysis/run_daily_analysis.py --enrich-only

    # Claude Code integration (saves JSON, use /analyze-stocks skill)
    python scripts/analysis/run_daily_analysis.py --claude-code

    # Custom capital for position sizing
    python scripts/analysis/run_daily_analysis.py --capital 50000000

Environment:
    ANTHROPIC_API_KEY: Required for Claude API analysis (not needed with --claude-code)

Claude Code Integration:
    1. Run with --claude-code flag
    2. Use /analyze-stocks skill in Claude Code to analyze the saved JSON
    3. Or ask Claude Code directly to analyze the data file
"""

import sys
import os
import logging
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from screener import StockScreener, MATouchCondition, MinPriceCondition, MinVolumeCondition
from screener.kospi_fetcher import KospiListFetcher
from screener.us_fetcher import UsStockFetcher
from data_enrichment import TechnicalEnricher, FundamentalEnricher, NewsEnricher
from utils.data_cache import OHLCVCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def screen_ma_touch(market: str, ma_period: int = 240, threshold: float = 0.02) -> List[Dict]:
    """
    Screen for stocks touching MA.

    Args:
        market: 'KOSPI' or 'SP500'
        ma_period: MA period (default 240)
        threshold: Touch threshold (default 2%)

    Returns:
        List of screening results
    """
    print(f"\n{'='*60}")
    print(f" Screening {market} - {ma_period}d MA Touch (±{threshold*100:.0f}%)")
    print(f"{'='*60}")

    # Get stock list
    if market == 'KOSPI':
        fetcher = KospiListFetcher()
        stocks = fetcher.get_kospi_symbols()
        min_price = 1000
        min_volume = 100000
    else:  # SP500
        fetcher = UsStockFetcher()
        stocks = fetcher.get_sp500_symbols()
        min_price = 5
        min_volume = 500000

    if not stocks:
        logger.error(f"Failed to fetch {market} stock list")
        return []

    tickers = [s['symbol'] for s in stocks]
    ticker_info = {s['symbol']: s for s in stocks}

    print(f"  Universe: {len(tickers)} stocks")

    # Screen for MA touch
    screener = StockScreener(max_workers=10)
    screener.add_condition(MinPriceCondition(min_price))
    screener.add_condition(MinVolumeCondition(min_volume))
    screener.add_condition(MATouchCondition(period=ma_period, threshold=threshold))

    results = screener.run(tickers=tickers, show_progress=False)

    print(f"  Found: {len(results)} stocks touching {ma_period}d MA")

    # Format results
    formatted = []
    for r in results:
        info = ticker_info.get(r.ticker, {})
        details = next((cr.details for cr in r.condition_results
                       if f'ma_touch_{ma_period}d' in cr.condition_name), {})

        formatted.append({
            'ticker': r.ticker,
            'name': info.get('name', r.name),
            'sector': info.get('sector', ''),
            'current_price': r.current_price,
            'ma_value': details.get('ma_value', 0),
            'distance_pct': details.get('distance_pct', 0) * 100,
            'market': market,
        })

    return formatted


def enrich_stocks(candidates: List[Dict], show_progress: bool = True) -> List[Dict]:
    """
    Enrich candidates with technical, fundamental, news data.
    """
    if not candidates:
        return []

    print(f"\n{'='*60}")
    print(f" Enriching {len(candidates)} candidates")
    print(f"{'='*60}")

    cache = OHLCVCache()
    tech_enricher = TechnicalEnricher()
    fund_enricher = FundamentalEnricher()
    news_enricher = NewsEnricher(max_articles=5, days=7)

    enriched = []
    total = len(candidates)

    for i, stock in enumerate(candidates, 1):
        ticker = stock['ticker']
        if show_progress:
            print(f"  [{i}/{total}] {ticker}...", end=" ", flush=True)

        try:
            # Get OHLCV data
            data = cache.get(ticker, days=250)
            if data is None or data.empty:
                if show_progress:
                    print("No data")
                continue

            # Enrich
            technical = tech_enricher.enrich(ticker, data)
            fundamental = fund_enricher.enrich(ticker)
            news = news_enricher.enrich(ticker, stock.get('name'))

            stock['technical'] = technical
            stock['fundamental'] = fundamental
            stock['news'] = news
            stock['ma_240'] = stock.get('ma_value', data['close'].tail(240).mean())

            enriched.append(stock)

            if show_progress:
                rsi = technical.get('rsi', 0)
                pe = fundamental.get('pe_ratio', 'N/A')
                print(f"RSI={rsi:.0f}, P/E={pe}")

        except Exception as e:
            if show_progress:
                print(f"Error: {e}")
            logger.warning(f"Failed to enrich {ticker}: {e}")

    return enriched


def save_enriched_json(enriched: List[Dict], market: str = "ALL") -> Path:
    """
    Save enriched stock data to JSON file for Claude Code analysis.

    Args:
        enriched: List of enriched stock data
        market: Market identifier

    Returns:
        Path to the saved JSON file
    """
    output_dir = project_root / "data" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"enriched_{market.lower()}_{date_str}.json"
    filepath = output_dir / filename

    # Prepare data for JSON serialization
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "market": market,
        "stock_count": len(enriched),
        "stocks": enriched
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n  Enriched data saved: {filepath}")
    return filepath


def analyze_with_claude(enriched: List[Dict], show_progress: bool = True) -> List:
    """
    Analyze enriched stocks with Claude.
    """
    if not enriched:
        return []

    # Check for API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("\n⚠️  ANTHROPIC_API_KEY not set. Skipping Claude analysis.")
        print("   Set the environment variable to enable AI analysis.")
        return []

    print(f"\n{'='*60}")
    print(f" Analyzing {len(enriched)} stocks with Claude")
    print(f"{'='*60}")

    try:
        from llm import StockAnalyzer
        analyzer = StockAnalyzer()
    except Exception as e:
        logger.error(f"Failed to initialize Claude analyzer: {e}")
        return []

    results = []
    total = len(enriched)

    for i, stock in enumerate(enriched, 1):
        ticker = stock['ticker']
        if show_progress:
            print(f"  [{i}/{total}] Analyzing {ticker}...", end=" ", flush=True)

        try:
            from llm import StockProfile

            profile = StockProfile(
                ticker=ticker,
                name=stock.get('name', ticker),
                current_price=stock['current_price'],
                ma_240=stock.get('ma_240', stock['current_price']),
                currency='₩' if ticker.endswith('.KS') or ticker.endswith('.KQ') else '$',
                technical=stock.get('technical', {}),
                fundamental=stock.get('fundamental', {}),
                news=stock.get('news', {}),
            )

            result = analyzer.analyze_with_profile(profile)
            results.append(result)

            if show_progress:
                print(f"{result.entry_recommendation} "
                      f"(V:{result.valuation_score:.0f}, R:{result.risk_score:.0f})")

        except Exception as e:
            if show_progress:
                print(f"Error: {e}")
            logger.warning(f"Failed to analyze {ticker}: {e}")

    return results


def generate_report(
    results: List,
    capital: float = 10000000,
    market: str = "ALL"
) -> str:
    """
    Generate analysis report.
    """
    if not results:
        return "No results to report."

    print(f"\n{'='*60}")
    print(f" Generating Report")
    print(f"{'='*60}")

    try:
        from pipeline import ReportGenerator, calculate_position_sizes
        from portfolio import PositionSizer

        # Calculate position sizes for BUY recommendations
        buy_results = [r for r in results if r.entry_recommendation == 'BUY']
        positions = []

        if buy_results:
            sizer = PositionSizer(
                total_capital=capital,
                max_position_pct=0.10,
                max_risk_per_trade_pct=0.02
            )

            for r in buy_results:
                pos = sizer.calculate(
                    ticker=r.ticker,
                    current_price=r.current_price,
                    risk_score=r.risk_score,
                    currency='₩' if r.ticker.endswith('.KS') or r.ticker.endswith('.KQ') else '$'
                )
                positions.append(pos)

        # Generate report
        generator = ReportGenerator()
        report = generator.generate_daily_report(
            results=results,
            positions=positions,
            market=market
        )

        # Save report
        filepath = generator.save_report(report)
        print(f"  Report saved: {filepath}")

        # Print summary
        generator.print_summary(results)

        return report

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        return f"Error generating report: {e}"


def run_pipeline(
    market: str = "ALL",
    capital: float = 10000000,
    enrich_only: bool = False,
    claude_code: bool = False,
    ma_period: int = 240,
    threshold: float = 0.02,
):
    """
    Run the full analysis pipeline.

    Args:
        market: Market to analyze (ALL, KOSPI, SP500)
        capital: Total capital for position sizing
        enrich_only: Only run screening and enrichment
        claude_code: Save JSON for Claude Code analysis instead of API
        ma_period: MA period for screening
        threshold: MA touch threshold
    """
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#" + "Daily Stock Analysis Pipeline".center(58) + "#")
    print("#" + " " * 58 + "#")
    print("#" * 60)
    print(f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Market: {market}")
    print(f"Capital: {capital:,.0f}")

    # 1. Screening
    candidates = []

    if market in ['ALL', 'KOSPI']:
        kospi_candidates = screen_ma_touch('KOSPI', ma_period, threshold)
        candidates.extend(kospi_candidates)

    if market in ['ALL', 'SP500']:
        sp500_candidates = screen_ma_touch('SP500', ma_period, threshold)
        candidates.extend(sp500_candidates)

    if not candidates:
        print("\nNo candidates found. Exiting.")
        return

    print(f"\nTotal candidates: {len(candidates)}")

    # 2. Enrichment
    enriched = enrich_stocks(candidates)

    # Save enriched data to JSON
    json_path = save_enriched_json(enriched, market)

    if enrich_only:
        print("\n--enrich-only flag set. Skipping analysis.")
        print(f"\nEnriched {len(enriched)} stocks.")
        print(f"Data saved to: {json_path}")
        return enriched

    if claude_code:
        print("\n--claude-code flag set. Skipping API analysis.")
        print(f"\nEnriched {len(enriched)} stocks.")
        print(f"Data saved to: {json_path}")
        print("\n" + "=" * 60)
        print(" Next Step: Analyze with Claude Code")
        print("=" * 60)
        print(f"\nRun the following command in Claude Code:")
        print(f"  /analyze-stocks {json_path}")
        print("\nOr ask Claude Code to analyze the enriched data:")
        print(f"  'Analyze the stocks in {json_path} and provide")
        print(f"   buy/wait/avoid recommendations with reasoning.'")
        return enriched

    # 3. Claude API Analysis
    results = analyze_with_claude(enriched)

    if not results:
        print("\nNo analysis results. Check API key or try --enrich-only.")
        print(f"\nYou can still analyze manually using the saved data:")
        print(f"  {json_path}")
        return enriched

    # 4. Report Generation
    report = generate_report(results, capital, market)

    print("\n" + "=" * 60)
    print(" Pipeline Complete")
    print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Daily Stock Analysis Pipeline'
    )
    parser.add_argument(
        '--market', '-m',
        type=str,
        default='ALL',
        choices=['ALL', 'KOSPI', 'SP500'],
        help='Market to analyze (default: ALL)'
    )
    parser.add_argument(
        '--capital', '-c',
        type=float,
        default=10000000,
        help='Total capital for position sizing (default: 10,000,000)'
    )
    parser.add_argument(
        '--enrich-only',
        action='store_true',
        help='Only enrich data, skip Claude analysis'
    )
    parser.add_argument(
        '--claude-code',
        action='store_true',
        help='Save JSON for Claude Code analysis (instead of Claude API)'
    )
    parser.add_argument(
        '--ma-period',
        type=int,
        default=240,
        help='MA period for screening (default: 240)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.02,
        help='MA touch threshold (default: 0.02 = 2%%)'
    )

    args = parser.parse_args()

    run_pipeline(
        market=args.market,
        capital=args.capital,
        enrich_only=args.enrich_only,
        claude_code=args.claude_code,
        ma_period=args.ma_period,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
