"""data_enrichment.news — backward-compatibility shim. Use data_sources.news.aggregator instead."""
import warnings as _warnings
_warnings.warn(
    "data_enrichment.news is deprecated. Use data_sources.news.aggregator instead.",
    DeprecationWarning,
    stacklevel=1,
)
from data_sources.news.aggregator import *  # noqa: F401, F403
from data_sources.news.aggregator import NewsEnricher  # noqa: F401
