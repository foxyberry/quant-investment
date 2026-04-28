"""screener.sector_fetcher — backward-compatibility shim. Use data_sources.market.sector instead."""
import warnings as _warnings
_warnings.warn(
    "screener.sector_fetcher is deprecated. Use data_sources.market.sector instead.",
    DeprecationWarning,
    stacklevel=1,
)
from data_sources.market.sector import *  # noqa: F401, F403
from data_sources.market.sector import SectorFetcher, get_sector_fetcher  # noqa: F401
