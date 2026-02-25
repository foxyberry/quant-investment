"""Tiger Brokers SDK constants and status mappings."""

from __future__ import annotations

from brokers.base import OrderStatus, OrderType

# ---------------------------------------------------------------------------
# Tiger SDK OrderStatus -> canonical OrderStatus
# ---------------------------------------------------------------------------

TIGER_STATUS_MAP: dict[str, OrderStatus] = {
    # Initial / New (-1)
    "Initial": OrderStatus.RECEIVED,
    "NEW": OrderStatus.RECEIVED,
    # PendingNew
    "PendingNew": OrderStatus.RECEIVED,
    "PENDING_NEW": OrderStatus.RECEIVED,
    # Held / Submitted (5)
    "Held": OrderStatus.CONFIRMED,
    "HELD": OrderStatus.CONFIRMED,
    "Submitted": OrderStatus.CONFIRMED,
    "SUBMITTED": OrderStatus.CONFIRMED,
    # PendingCancel (3)
    "PendingCancel": OrderStatus.CONFIRMED,
    "PENDING_CANCEL": OrderStatus.CONFIRMED,
    # PartiallyFilled (2)
    "PartiallyFilled": OrderStatus.PARTIAL,
    "PARTIALLY_FILLED": OrderStatus.PARTIAL,
    # Filled (6)
    "Filled": OrderStatus.FILLED,
    "FILLED": OrderStatus.FILLED,
    # Cancelled (4)
    "Cancelled": OrderStatus.CANCELED,
    "CANCELLED": OrderStatus.CANCELED,
    # Rejected (7)
    "Rejected": OrderStatus.REJECTED,
    "REJECTED": OrderStatus.REJECTED,
    # Expired (-2)
    "Expired": OrderStatus.REJECTED,
    "EXPIRED": OrderStatus.REJECTED,
}

# ---------------------------------------------------------------------------
# Canonical OrderType -> Tiger order type string
# ---------------------------------------------------------------------------

ORDER_TYPE_TO_TIGER: dict[OrderType, str] = {
    OrderType.MARKET: "MKT",
    OrderType.LIMIT: "LMT",
}

TIGER_TO_ORDER_TYPE: dict[str, OrderType] = {v: k for k, v in ORDER_TYPE_TO_TIGER.items()}

# ---------------------------------------------------------------------------
# Supported markets and currency mapping
# ---------------------------------------------------------------------------

SUPPORTED_MARKETS: list[str] = ["US", "HK", "SG"]

MARKET_CURRENCY: dict[str, str] = {
    "US": "USD",
    "HK": "HKD",
    "SG": "SGD",
}

# Default currency when market cannot be determined from ticker
DEFAULT_CURRENCY: str = "USD"
