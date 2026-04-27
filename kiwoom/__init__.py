"""Kiwoom OpenAPI+ integration module — backward-compatibility shim.

All Kiwoom driver code has been consolidated into brokers/kiwoom/.
This package re-exports everything so existing import paths continue to work.

New code should import directly from brokers.kiwoom:
    from brokers.kiwoom.connection import KiwoomConnection
    from brokers.kiwoom.constants import HogaType, OrderType
"""

import warnings as _warnings
_warnings.warn(
    "The top-level 'kiwoom' package is deprecated. "
    "Use 'brokers.kiwoom' instead.",
    DeprecationWarning,
    stacklevel=1,
)

from brokers.kiwoom.connection import KiwoomConnection  # noqa: F401, E402
from brokers.kiwoom.chejan_handler import ChejanHandler, OrderStatus  # noqa: F401, E402
from brokers.kiwoom.order import KiwoomOrderManager, Order  # noqa: F401, E402
from brokers.kiwoom.safety import AuditLogger, DuplicateOrderGuard, KillSwitch, KiwoomSafetyManager, SafetyViolation  # noqa: F401, E402
from brokers.kiwoom.condition_search import ConditionDefinition, ConditionSearchManager  # noqa: F401, E402
from brokers.kiwoom.realtime import RealtimeSubscriptionManager, ScreenManager  # noqa: F401, E402
from brokers.kiwoom.tr import KiwoomTrClient, TrRequest  # noqa: F401, E402
from brokers.kiwoom.constants import (  # noqa: F401, E402
    ChejanGubun,
    ErrorCode,
    FID,
    HogaType,
    MarketType,
    OrderType,
    RealType,
    ServerType,
)

__all__ = [
    "KiwoomConnection",
    "ChejanHandler",
    "OrderStatus",
    "KiwoomOrderManager",
    "Order",
    "KiwoomSafetyManager",
    "KillSwitch",
    "AuditLogger",
    "DuplicateOrderGuard",
    "SafetyViolation",
    "ConditionDefinition",
    "ConditionSearchManager",
    "KiwoomTrClient",
    "TrRequest",
    "ScreenManager",
    "RealtimeSubscriptionManager",
    "ChejanGubun",
    "ErrorCode",
    "FID",
    "HogaType",
    "MarketType",
    "OrderType",
    "RealType",
    "ServerType",
]
