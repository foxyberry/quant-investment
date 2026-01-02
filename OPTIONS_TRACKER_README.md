# Options Volume Tracker Bot

Based on the requirements in `Todo/1.bot.md`, this bot monitors unusual options activity for key stocks.

## Features

- **Automated Monitoring**: Tracks options volume for NVDA, AAPL, TSLA, AMZN
- **Spike Detection**: Alerts when volume is 2-3x above the 5-day average  
- **Smart Caching**: Stores options data locally to minimize API calls
- **Historical Analysis**: Builds volume history for trend analysis

## Usage

### Single Check
```bash
# Activate virtual environment
source venv/bin/activate

# Run a one-time check
python options_tracker.py --once
```

### Continuous Monitoring
```bash
# Activate virtual environment  
source venv/bin/activate

# Run continuous monitoring (checks every 60 seconds)
python options_tracker.py
```

## Alert Levels

- 🟢 **NORMAL**: Volume within normal range
- 🟡 **MEDIUM**: Volume 2x above 5-day average
- 🔴 **HIGH**: Volume 3x above 5-day average

## Data Storage

- **Options Chains**: `data/options/[SYMBOL]/`
- **Volume History**: `data/options_volume/`
- **Logs**: `logs/options_tracker.log`

## Configuration

Edit these variables in `options_tracker.py`:
- `TARGET_SYMBOLS`: Stocks to monitor
- `CHECK_INTERVAL`: Seconds between checks (default: 60)
- `VOLUME_THRESHOLD`: Medium alert threshold (default: 2.0x)
- `ALERT_THRESHOLD`: High alert threshold (default: 3.0x)

## Architecture

The tracker reuses the existing project infrastructure:
- `utils/options_fetch.py`: Options data fetching and caching
- `utils/fetch.py`: Pattern for historical data management
- `utils/timezone_utils.py`: Market time handling

## Example Output

```
================================================================================
OPTIONS VOLUME TRACKER - 2025-10-11 23:40:32
================================================================================

Symbol   Volume       vs Avg   P/C Ratio  Alert      Status
----------------------------------------------------------------------
🟢 NVDA   2.0M         1.2x     0.68       NORMAL     Normal activity
🟡 AAPL   590.5K       2.5x     0.60       MEDIUM     Volume is 2.5x the 5-day average
🟢 TSLA   1.2M         0.9x     0.93       NORMAL     Normal activity
🔴 AMZN   624.4K       3.2x     0.36       HIGH       Volume is 3.2x the 5-day average
```