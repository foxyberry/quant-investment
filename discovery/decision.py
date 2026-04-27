"""discovery.decision — backward-compatibility shim. Use screener.decision instead."""
import warnings as _warnings
_warnings.warn(
    "discovery.decision is deprecated. Use screener.decision instead.",
    DeprecationWarning, stacklevel=2,
)
from screener.decision import *  # noqa: F401, F403
from screener.decision import analyze_buy_signal, BuyDecision, Recommendation, RiskLevel  # noqa: F401
