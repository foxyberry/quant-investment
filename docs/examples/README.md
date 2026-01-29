# Examples & Templates

Templates and examples for creating new strategies.

## Templates

Copy these templates to `scripts/` folder when creating new strategies.

| File | Purpose | Copy to |
|------|---------|---------|
| `screening_template.py` | Stock screening strategy | `scripts/screening/` |
| `live_template.py` | Live trading bot | `scripts/live/` |

### Usage

```bash
# Create screening strategy
cp docs/examples/screening_template.py scripts/screening/my_strategy.py

# Create live trading bot
cp docs/examples/live_template.py scripts/live/my_bot.py

# Run strategy
python scripts/screening/my_strategy.py
```

## Examples

| File | Description |
|------|-------------|
| `market_calendar_example.py` | Market calendar usage example |

```bash
python docs/examples/market_calendar_example.py
```

## Related Docs

- [Screener README](../SCREENER_README.md)
- [Project README](../../README.md)
