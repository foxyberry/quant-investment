"""
utils.fetch — backward-compatibility shim.

All fetch logic has been moved to data_sources.market.ohlcv.
This module re-exports everything so existing import paths continue to work.

New code should use:
    from data_sources.market.ohlcv import get_ohlcv
"""

import warnings as _warnings
_warnings.warn(
    "utils.fetch is deprecated. Use data_sources.market.ohlcv instead.",
    DeprecationWarning,
    stacklevel=1,
)

from data_sources.market.ohlcv import *  # noqa: F401, F403
from data_sources.market.ohlcv import (  # noqa: F401
    get_ohlcv,
    get_current_price,
    get_cache_path,
    load_cached_data,
    save_data_to_cache,
    fetch_yfinance_data,
    history_data,
    get_historical_data,
)
