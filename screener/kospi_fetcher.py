"""screener.kospi_fetcher — backward-compatibility shim. Use data_sources.market.kr_market instead."""
import warnings as _warnings
_warnings.warn(
    "screener.kospi_fetcher is deprecated. Use data_sources.market.kr_market instead.",
    DeprecationWarning,
    stacklevel=1,
)
from data_sources.market.kr_market import *  # noqa: F401, F403
from data_sources.market.kr_market import KospiListFetcher  # noqa: F401
