"""screener.us_fetcher — backward-compatibility shim. Use data_sources.market.us_market instead."""
import warnings as _warnings
_warnings.warn(
    "screener.us_fetcher is deprecated. Use data_sources.market.us_market instead.",
    DeprecationWarning,
    stacklevel=1,
)
from data_sources.market.us_market import *  # noqa: F401, F403
from data_sources.market.us_market import UsStockFetcher  # noqa: F401
