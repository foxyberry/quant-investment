# Market Calendar Functionality

[한국어 문서](ko/MARKET_CALENDAR_README.md)

This project includes comprehensive market calendar functionality to ensure that all backtesting and analysis uses valid trading days only.

## Overview

The market calendar system ensures that:
- ✅ Only trading days are used for backtesting
- ✅ Weekends are automatically excluded
- ✅ US market holidays are automatically excluded
- ✅ Invalid dates are automatically adjusted to the nearest trading day
- ✅ All date operations are timezone-aware (US Eastern)

## Key Functions

### 1. Trading Day Validation

```python
from utils.timezone_utils import is_trading_day, validate_trading_date

# Check if a date is a trading day
date = datetime(2024, 1, 15)  # Martin Luther King Jr. Day
is_trading = is_trading_day(date)  # Returns False

# Validate and adjust dates automatically
adjusted_date = validate_trading_date(date, "End date")
# Automatically adjusts to the previous trading day
```

### 2. Get Trading Days

```python
from utils.timezone_utils import get_last_trading_day, get_next_trading_day

# Get the last trading day
last_trading = get_last_trading_day()  # Returns last trading day

# Get the next trading day
next_trading = get_next_trading_day()  # Returns next trading day
```

### 3. Backtesting Date Ranges

```python
from utils.timezone_utils import get_valid_backtest_dates

# Get valid start and end dates for backtesting
start_date, end_date = get_valid_backtest_dates(days_back=365)
# Returns valid trading dates for 365 trading days back
```

### 4. Trading Days Between Dates

```python
from utils.timezone_utils import get_trading_days_between

# Get all trading days between two dates
trading_days = get_trading_days_between(start_date, end_date)
# Returns list of all trading days in the range
```

## Usage Examples

### Example 1: Basic Trading Day Check

```python
from datetime import datetime
from utils.timezone_utils import is_trading_day

# Test various dates
dates_to_test = [
    datetime(2024, 1, 15),  # MLK Day (holiday)
    datetime(2024, 1, 20),  # Saturday
    datetime(2024, 1, 21),  # Sunday
    datetime(2024, 1, 16),  # Regular Tuesday
]

for date in dates_to_test:
    is_trading = is_trading_day(date)
    print(f"{date.strftime('%Y-%m-%d %A')}: {'✅ Trading' if is_trading else '❌ Not Trading'}")
```

### Example 2: Backtesting with Valid Dates

```python
from utils.timezone_utils import get_valid_backtest_dates

# Get valid backtest dates
start_date, end_date = get_valid_backtest_dates(days_back=365)

print(f"Backtesting period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"Start day: {start_date.strftime('%A')}")
print(f"End day: {end_date.strftime('%A')}")

# Use these dates in your backtesting
result = backtester.run_backtest(
    symbol="AAPL",
    start_date=start_date,
    end_date=end_date,
    # ... other parameters
)
```

### Example 3: Date Validation in Data Fetching

```python
from utils.timezone_utils import validate_trading_date

def fetch_stock_data(symbol, end_date):
    # Validate the end date
    valid_end_date = validate_trading_date(end_date, f"End date for {symbol}")
    
    # Fetch data using the validated date
    data = yfinance.download(symbol, end=valid_end_date)
    return data
```

## Market Holidays Handled

The system automatically handles all US market holidays including:

- New Year's Day
- Martin Luther King Jr. Day
- Presidents' Day
- Good Friday
- Memorial Day
- Juneteenth
- Independence Day
- Labor Day
- Thanksgiving Day
- Christmas Day

## Timezone Handling

All dates are handled in US Eastern timezone (the US stock market timezone):

```python
from utils.timezone_utils import now, get_current_market_time

# Get current market time
current_time = now()  # Returns timezone-aware datetime in US Eastern
market_time = get_current_market_time()  # Same as now()
```

## Integration with Backtesting

The market calendar is automatically integrated into the backtesting system:

1. **Automatic Date Validation**: All dates are validated before use
2. **Holiday Awareness**: No backtesting on holidays or weekends
3. **Proper Date Ranges**: Ensures sufficient trading days for analysis
4. **Timezone Consistency**: All dates in US Eastern timezone

## Running the Example

Test the market calendar functionality:

```bash
python market_calendar_example.py
```

This will demonstrate:
- Current trading day status
- Holiday detection
- Weekend handling
- Date validation and adjustment
- Valid backtest date generation

## Dependencies

The market calendar functionality requires:

```
pandas_market_calendars>=4.0.0
pytz>=2023.3
```

## Benefits

1. **Accuracy**: No false signals from non-trading days
2. **Reliability**: Automatic handling of holidays and weekends
3. **Consistency**: All date operations use the same calendar
4. **Ease of Use**: Simple functions for common date operations
5. **Timezone Safety**: No timezone-related errors

## Best Practices

1. **Always validate dates**: Use `validate_trading_date()` for user input
2. **Use trading day functions**: Use `get_valid_backtest_dates()` for backtesting
3. **Check trading status**: Use `is_trading_day()` before operations
4. **Handle timezones**: Use the provided timezone utilities consistently
5. **Test with examples**: Run the example script to verify functionality 