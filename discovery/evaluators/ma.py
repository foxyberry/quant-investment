"""discovery.evaluators.ma — shim → screener.evaluators.ma"""
import warnings as _warnings
_warnings.warn(
    "discovery.evaluators.ma is deprecated. Use screener.evaluators.ma instead.",
    DeprecationWarning, stacklevel=1,
)
from screener.evaluators.ma import *  # noqa: F401, F403
