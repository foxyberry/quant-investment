"""data_enrichment.technical — backward-compatibility shim. Use data_sources.technical.technical instead."""
import warnings as _warnings
_warnings.warn(
    "data_enrichment.technical is deprecated. Use data_sources.technical.technical instead.",
    DeprecationWarning,
    stacklevel=1,
)
from data_sources.technical.technical import *  # noqa: F401, F403
from data_sources.technical.technical import (  # noqa: F401
    RSISignal,
    MACDCross,
    BBPosition,
    OBVTrend,
    TechnicalEnricherConfig,
    TechnicalEnricher,
    enrich_technical,
)
