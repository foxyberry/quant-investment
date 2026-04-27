"""
Stock Discovery Module — backward-compatibility shim.

All logic has been moved to the screener package:
  discovery.indicators  → screener.indicators
  discovery.decision    → screener.decision
  discovery.evaluator   → screener.evaluator
  discovery.evaluators  → screener.evaluators

This module re-exports everything so existing import paths continue to work.
"""

import warnings as _warnings

_warnings.warn(
    "The 'discovery' package is deprecated. "
    "Use 'screener.indicators', 'screener.decision', or 'screener.evaluators' instead.",
    DeprecationWarning,
    stacklevel=1,
)

from screener.evaluator import evaluate_condition, evaluate_conditions  # noqa: F401, E402
from screener.indicators import calculate_indicators, calculate_all_mas, get_ma_distances  # noqa: F401, E402
from screener.decision import analyze_buy_signal, BuyDecision, Recommendation, RiskLevel  # noqa: F401, E402

__all__ = [
    "evaluate_condition", "evaluate_conditions",
    "calculate_indicators", "calculate_all_mas", "get_ma_distances",
    "analyze_buy_signal", "BuyDecision", "Recommendation", "RiskLevel",
]
