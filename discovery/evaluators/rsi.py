"""discovery.evaluators.rsi — shim → screener.evaluators.rsi"""
import warnings as _warnings
_warnings.warn(
    "discovery.evaluators.rsi is deprecated. Use screener.evaluators.rsi instead.",
    DeprecationWarning, stacklevel=1,
)
from screener.evaluators.rsi import *  # noqa: F401, F403
