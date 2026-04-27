"""discovery.evaluators — backward-compatibility shim. Use screener.evaluators instead."""
import warnings as _warnings
_warnings.warn(
    "discovery.evaluators is deprecated. Use screener.evaluators instead.",
    DeprecationWarning, stacklevel=1,
)
from screener.evaluators import *  # noqa: F401, F403
from screener.evaluators import get_evaluator, EVALUATOR_MAP  # noqa: F401
