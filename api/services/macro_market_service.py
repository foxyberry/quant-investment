"""Backward-compatibility re-export.

This module has been split into:
  - api.services.macro_service        (MacroMarketService, get_macro_market_service)
  - api.services.market_data_service  (MarketDataMixin — data fetch adapters)

All existing imports continue to work via this shim.
"""

from api.services.macro_service import MacroMarketService, get_macro_market_service

__all__ = ["MacroMarketService", "get_macro_market_service"]
