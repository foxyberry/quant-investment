"""
Screening Strategy Template

Copy this file to scripts/screening/ and customize with your own conditions.

Usage:
    cp docs/examples/screening_template.py scripts/screening/my_strategy.py
    python scripts/screening/my_strategy.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from screener import (
    StockScreener,
    # Price conditions
    MinPriceCondition,
    MaxPriceCondition,
    PriceRangeCondition,
    # Volume conditions
    MinVolumeCondition,
    VolumeAboveAvgCondition,
    VolumeSpikeCondition,
    # MA conditions
    MATouchCondition,
    AboveMACondition,
    BelowMACondition,
    MACrossUpCondition,
    MACrossDownCondition,
    # RSI conditions
    RSIOversoldCondition,
    RSIOverboughtCondition,
    RSIRangeCondition,
    # Composite conditions
    AndCondition,
    OrCondition,
    NotCondition,
    # Presets
    get_preset,
    list_presets,
)


def run():
    """
    Main screening logic - customize this function

    Returns:
        List of ScreeningResult
    """
    print("Starting custom screening strategy...")

    # ===== OPTION 1: Use Preset =====
    # Available presets: ma_touch_160, golden_cross, oversold_bounce, etc.
    # print(f"Available presets: {list_presets()}")
    # screener = StockScreener(conditions=get_preset("ma_touch_160"))

    # ===== OPTION 2: Build Custom Conditions =====
    screener = StockScreener()

    # Add price filters
    screener.add_condition(MinPriceCondition(min_price=5000))
    # screener.add_condition(MaxPriceCondition(max_price=100000))

    # Add MA conditions
    screener.add_condition(MATouchCondition(period=160, threshold=0.03))

    # Add volume conditions (optional)
    # screener.add_condition(MinVolumeCondition(min_volume=100000))
    # screener.add_condition(VolumeSpikeCondition(multiplier=1.5))

    # Add RSI conditions (optional)
    # screener.add_condition(RSIOversoldCondition(threshold=40))

    # ===== OPTION 3: Complex Conditions =====
    # condition = AndCondition([
    #     MinPriceCondition(5000),
    #     OrCondition([
    #         MATouchCondition(period=120),
    #         MATouchCondition(period=160),
    #         MATouchCondition(period=200),
    #     ]),
    #     RSIOversoldCondition(threshold=40),
    # ])
    # screener = StockScreener(conditions=[condition])

    # ===== RUN SCREENING =====
    # Universe options: "KOSPI", "KOSDAQ", "ALL"
    # Or specify tickers: tickers=["005930.KS", "035420.KS"]
    results = screener.run(universe="KOSPI", show_progress=True)

    # ===== PROCESS RESULTS =====
    if results:
        print(f"\n{'='*60}")
        print(f"Found {len(results)} matching stocks:")
        print(f"{'='*60}")

        for r in results:
            print(f"\n{r.ticker} ({r.name})")
            print(f"  Price: {r.current_price:,.0f} KRW")
            print(f"  Volume: {r.volume:,}")
            for cr in r.condition_results:
                status = "✓" if cr.matched else "✗"
                print(f"  {status} {cr.condition_name}")

        # Convert to DataFrame for further analysis
        df = screener.to_dataframe(results)
        print(f"\n{df[['ticker', 'name', 'current_price', 'matched']].to_string(index=False)}")
    else:
        print("\nNo matching stocks found.")

    return results


if __name__ == "__main__":
    run()
