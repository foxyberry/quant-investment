#!/usr/bin/env python3
"""
Market Calendar Example
Demonstrates how to use market calendar functions for valid trading dates
"""
from datetime import datetime, timedelta
from utils.timezone_utils import (
    now, 
    is_trading_day, 
    get_last_trading_day, 
    get_next_trading_day,
    get_valid_backtest_dates,
    validate_trading_date,
    get_trading_days_between
)

def main():
    print("=== Market Calendar Example ===\n")
    
    # 1. Check if current date is a trading day
    current_time = now()
    print(f"1. Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Is trading day: {is_trading_day(current_time)}")
    print(f"   Day of week: {current_time.strftime('%A')}")
    
    # 2. Get last trading day
    last_trading = get_last_trading_day()
    print(f"\n2. Last trading day: {last_trading.strftime('%Y-%m-%d %A')}")
    
    # 3. Get next trading day
    next_trading = get_next_trading_day()
    print(f"3. Next trading day: {next_trading.strftime('%Y-%m-%d %A')}")
    
    # 4. Test some specific dates
    test_dates = [
        datetime(2024, 1, 15),  # Martin Luther King Jr. Day (Monday holiday)
        datetime(2024, 2, 19),  # Presidents' Day (Monday holiday)
        datetime(2024, 12, 25), # Christmas Day (Wednesday holiday)
        datetime(2024, 1, 20),  # Saturday
        datetime(2024, 1, 21),  # Sunday
        datetime(2024, 1, 16),  # Regular Tuesday
    ]
    
    print(f"\n4. Testing specific dates:")
    for date in test_dates:
        is_trading = is_trading_day(date)
        day_name = date.strftime('%A')
        print(f"   {date.strftime('%Y-%m-%d')} ({day_name}): {'✅ Trading' if is_trading else '❌ Not Trading'}")
    
    # 5. Validate and adjust dates
    print(f"\n5. Validating dates:")
    invalid_dates = [
        datetime(2024, 1, 15),  # Holiday
        datetime(2024, 1, 20),  # Saturday
    ]
    
    for date in invalid_dates:
        adjusted = validate_trading_date(date, f"Date {date.strftime('%Y-%m-%d')}")
        print(f"   Original: {date.strftime('%Y-%m-%d %A')} -> Adjusted: {adjusted.strftime('%Y-%m-%d %A')}")
    
    # 6. Get valid backtest dates
    print(f"\n6. Getting valid backtest dates:")
    start_date, end_date = get_valid_backtest_dates(days_back=30)
    print(f"   30 trading days back:")
    print(f"   Start: {start_date.strftime('%Y-%m-%d %A')}")
    print(f"   End: {end_date.strftime('%Y-%m-%d %A')}")
    
    # 7. Get trading days between dates
    print(f"\n7. Trading days in the last week:")
    week_ago = end_date - timedelta(days=7)
    trading_days = get_trading_days_between(week_ago, end_date)
    for day in trading_days:
        print(f"   {day.strftime('%Y-%m-%d %A')}")
    
    # 8. Demonstrate weekend handling
    print(f"\n8. Weekend handling:")
    friday = datetime(2024, 1, 19)  # Friday
    saturday = datetime(2024, 1, 20)  # Saturday
    sunday = datetime(2024, 1, 21)   # Sunday
    monday = datetime(2024, 1, 22)   # Monday
    
    print(f"   Friday {friday.strftime('%Y-%m-%d')}: {is_trading_day(friday)}")
    print(f"   Saturday {saturday.strftime('%Y-%m-%d')}: {is_trading_day(saturday)}")
    print(f"   Sunday {sunday.strftime('%Y-%m-%d')}: {is_trading_day(sunday)}")
    print(f"   Monday {monday.strftime('%Y-%m-%d')}: {is_trading_day(monday)}")
    
    print(f"\n✅ Market calendar example completed!")

if __name__ == "__main__":
    main() 