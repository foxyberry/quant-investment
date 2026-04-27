"""discovery.evaluator — backward-compatibility shim. Use screener.evaluator instead."""
import warnings as _warnings
_warnings.warn(
    "discovery.evaluator is deprecated. Use screener.evaluator instead.",
    DeprecationWarning, stacklevel=1,
)
from screener.evaluator import *  # noqa: F401, F403
from screener.evaluator import evaluate_condition, evaluate_conditions  # noqa: F401
