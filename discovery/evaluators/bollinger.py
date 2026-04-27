"""discovery.evaluators.bollinger — shim → screener.evaluators.bollinger"""
import warnings as _warnings
_warnings.warn(
    "discovery.evaluators.bollinger is deprecated. Use screener.evaluators.bollinger instead.",
    DeprecationWarning, stacklevel=1,
)
from screener.evaluators.bollinger import *  # noqa: F401, F403
