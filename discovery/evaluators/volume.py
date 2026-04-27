"""discovery.evaluators.volume — shim → screener.evaluators.volume"""
import warnings as _warnings
_warnings.warn(
    "discovery.evaluators.volume is deprecated. Use screener.evaluators.volume instead.",
    DeprecationWarning, stacklevel=2,
)
from screener.evaluators.volume import *  # noqa: F401, F403
