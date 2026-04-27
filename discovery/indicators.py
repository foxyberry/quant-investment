"""discovery.indicators — backward-compatibility shim. Use screener.indicators instead."""
import warnings as _warnings
_warnings.warn(
    "discovery.indicators is deprecated. Use screener.indicators instead.",
    DeprecationWarning, stacklevel=1,
)
from screener.indicators import *  # noqa: F401, F403
from screener.indicators import (  # noqa: F401
    calculate_indicators, calculate_all_mas, get_ma_distances,
    calculate_obv, calculate_stochastic, calculate_vpci, calculate_bollinger_width,
    TechnicalIndicators,
)
