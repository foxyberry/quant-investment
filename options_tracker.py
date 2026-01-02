#!/usr/bin/env python3
"""
Options Volume Tracker Bot
Monitors unusual options activity for specified stocks
Based on Todo/1.bot.md specifications
"""

import sys
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict
from utils.options_fetch import (
    fetch_options_chain,
    calculate_volume_metrics,
    detect_unusual_activity,
    save_options_volume_history,
    get_options_volume_history
)
from utils.timezone_utils import get_current_market_time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/options_tracker.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Target stocks to monitor (from Todo/1.bot.md)
TARGET_SYMBOLS = ['NVDA', 'AAPL', 'TSLA', 'AMZN']

# Configuration
CHECK_INTERVAL = 60  # seconds
VOLUME_THRESHOLD = 2.0  # 2x average for unusual activity
ALERT_THRESHOLD = 3.0  # 3x average for high alert

def format_number(num):
    """Format large numbers for display"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(int(num))

def analyze_single_stock(symbol: str) -> Dict:
    """
    Analyze options activity for a single stock
    
    Returns:
        Dict with analysis results
    """
    logger.info(f"Analyzing {symbol}...")
    
    try:
        # Fetch current options chain
        options_data = fetch_options_chain(symbol)
        
        # Calculate metrics for calls and puts
        call_metrics = calculate_volume_metrics(options_data['calls'])
        put_metrics = calculate_volume_metrics(options_data['puts'])
        
        # Combined metrics
        total_metrics = {
            'total_volume': call_metrics['total_volume'] + put_metrics['total_volume'],
            'call_volume': call_metrics['total_volume'],
            'put_volume': put_metrics['total_volume'],
            'total_open_interest': call_metrics['total_open_interest'] + put_metrics['total_open_interest'],
            'put_call_ratio': put_metrics['total_volume'] / call_metrics['total_volume'] 
                             if call_metrics['total_volume'] > 0 else 0
        }
        
        # Detect unusual activity
        detection = detect_unusual_activity(symbol, total_metrics, VOLUME_THRESHOLD)
        
        # Save to history
        save_options_volume_history(symbol, total_metrics)
        
        # Prepare result
        result = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'metrics': total_metrics,
            'detection': detection,
            'top_call_strikes': call_metrics['top_strikes'][:3],
            'top_put_strikes': put_metrics['top_strikes'][:3],
            'alert_level': 'HIGH' if detection['ratio'] >= ALERT_THRESHOLD else 
                          'MEDIUM' if detection['is_unusual'] else 'NORMAL'
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'error': str(e),
            'alert_level': 'ERROR'
        }

def display_results(results: List[Dict]):
    """Display analysis results in formatted table"""
    
    print("\n" + "="*80)
    print(f"OPTIONS VOLUME TRACKER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Summary table
    print(f"\n{'Symbol':<8} {'Volume':<12} {'vs Avg':<8} {'P/C Ratio':<10} {'Alert':<10} {'Status'}")
    print("-"*70)
    
    alerts = []
    
    for result in results:
        if 'error' in result:
            print(f"{result['symbol']:<8} {'ERROR':<12} {'-':<8} {'-':<10} {'ERROR':<10} {result['error'][:30]}")
            continue
        
        metrics = result['metrics']
        detection = result['detection']
        
        volume_str = format_number(metrics['total_volume'])
        ratio_str = f"{detection['ratio']:.1f}x" if detection['ratio'] > 0 else "N/A"
        pc_ratio = f"{metrics['put_call_ratio']:.2f}"
        alert = result['alert_level']
        status = detection['reason']
        
        # Highlight unusual activity
        if alert == 'HIGH':
            marker = "🔴"
            alerts.append(result)
        elif alert == 'MEDIUM':
            marker = "🟡"
            alerts.append(result)
        else:
            marker = "🟢"
        
        print(f"{marker} {result['symbol']:<6} {volume_str:<12} {ratio_str:<8} {pc_ratio:<10} {alert:<10} {status}")
    
    # Detailed alerts
    if alerts:
        print("\n" + "="*80)
        print("UNUSUAL ACTIVITY DETECTED")
        print("="*80)
        
        for alert in alerts:
            print(f"\n📊 {alert['symbol']} - {alert['alert_level']} ALERT")
            print(f"   Current Volume: {format_number(alert['metrics']['total_volume'])}")
            print(f"   5-Day Average: {format_number(alert['detection']['avg_volume'])}")
            print(f"   Ratio: {alert['detection']['ratio']:.2f}x normal")
            print(f"   Put/Call Ratio: {alert['metrics']['put_call_ratio']:.2f}")
            
            if alert['top_call_strikes']:
                print("   Top Call Strikes:")
                for strike in alert['top_call_strikes'][:2]:
                    print(f"      ${strike['strike']:.2f} - Vol: {format_number(strike['volume'])} (Exp: {strike['expiry']})")
            
            if alert['top_put_strikes']:
                print("   Top Put Strikes:")
                for strike in alert['top_put_strikes'][:2]:
                    print(f"      ${strike['strike']:.2f} - Vol: {format_number(strike['volume'])} (Exp: {strike['expiry']})")

def run_continuous_monitoring():
    """Run continuous monitoring during market hours"""
    
    logger.info("Starting Options Volume Tracker Bot")
    print("\n🤖 Options Volume Tracker Bot Started")
    print(f"   Monitoring: {', '.join(TARGET_SYMBOLS)}")
    print(f"   Check Interval: {CHECK_INTERVAL} seconds")
    print(f"   Alert Thresholds: {VOLUME_THRESHOLD}x (Medium), {ALERT_THRESHOLD}x (High)")
    print("\n   Press Ctrl+C to stop\n")
    
    check_count = 0
    
    try:
        while True:
            check_count += 1
            
            # Check if market is open (optional - can run after hours too)
            market_time = get_current_market_time()
            
            # Analyze all stocks
            results = []
            for symbol in TARGET_SYMBOLS:
                result = analyze_single_stock(symbol)
                results.append(result)
            
            # Display results
            display_results(results)
            
            # Log high alerts
            high_alerts = [r for r in results if r.get('alert_level') == 'HIGH']
            if high_alerts:
                logger.warning(f"HIGH ALERTS: {[r['symbol'] for r in high_alerts]}")
            
            print(f"\n⏱️  Check #{check_count} completed. Next check in {CHECK_INTERVAL} seconds...")
            print("   (Press Ctrl+C to stop)")
            
            # Wait for next check
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Options Volume Tracker stopped by user")
        logger.info("Options Volume Tracker stopped")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Error: {e}")
        
def run_single_check():
    """Run a single check of all stocks"""
    
    print("\n🔍 Running single options volume check...")
    
    results = []
    for symbol in TARGET_SYMBOLS:
        result = analyze_single_stock(symbol)
        results.append(result)
    
    display_results(results)
    
    # Summary
    unusual = [r for r in results if r.get('detection', {}).get('is_unusual', False)]
    if unusual:
        print(f"\n⚠️  Unusual activity detected in {len(unusual)} stocks: {[r['symbol'] for r in unusual]}")
    else:
        print("\n✅ No unusual activity detected")

def main():
    """Main entry point"""
    
    # Create logs directory if needed
    import os
    os.makedirs('logs', exist_ok=True)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run single check
        run_single_check()
    else:
        # Run continuous monitoring
        run_continuous_monitoring()

if __name__ == "__main__":
    main()