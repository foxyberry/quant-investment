"""Kiwoom broker package.

Contains the low-level OCX driver (connection, order, TR, realtime, etc.)
consolidated from the top-level kiwoom/ package.

The BrokerAdapter is intentionally NOT imported here to avoid circular
imports (adapter → kiwoom_service → kiwoom.*).
Import it directly when needed:
    from brokers.kiwoom.adapter import KiwoomBrokerAdapter

Driver code can be imported from here:
    from brokers.kiwoom import KiwoomConnection, HogaType, OrderType
"""

from __future__ import annotations

# Driver exports (no circular deps)
from brokers.kiwoom.connection import KiwoomConnection  # noqa: F401
from brokers.kiwoom.chejan_handler import ChejanHandler, OrderStatus  # noqa: F401
from brokers.kiwoom.order import KiwoomOrderManager, Order  # noqa: F401
from brokers.kiwoom.safety import AuditLogger, DuplicateOrderGuard, KillSwitch, KiwoomSafetyManager, SafetyViolation  # noqa: F401
from brokers.kiwoom.condition_search import ConditionDefinition, ConditionSearchManager  # noqa: F401
from brokers.kiwoom.realtime import RealtimeSubscriptionManager, ScreenManager  # noqa: F401
from brokers.kiwoom.tr import KiwoomTrClient, TrRequest  # noqa: F401
from brokers.kiwoom.constants import (  # noqa: F401
    ChejanGubun, ErrorCode, FID, HogaType, MarketType, OrderType, RealType, ServerType,
)

__all__ = [
    # Adapter (import separately to avoid circular deps)
    # "KiwoomBrokerAdapter",  # from brokers.kiwoom.adapter import KiwoomBrokerAdapter
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
