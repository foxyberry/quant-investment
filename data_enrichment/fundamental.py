"""data_enrichment.fundamental — backward-compatibility shim. Use data_sources.fundamental.fundamental instead."""
import warnings as _warnings
_warnings.warn(
    "data_enrichment.fundamental is deprecated. Use data_sources.fundamental.fundamental instead.",
    DeprecationWarning,
    stacklevel=1,
)
from data_sources.fundamental.fundamental import *  # noqa: F401, F403
from data_sources.fundamental.fundamental import (  # noqa: F401
    FundamentalData,
    FundamentalEnricher,
    enrich_fundamental,
)
