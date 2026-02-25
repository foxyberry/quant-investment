"""IBKR Client Portal API constants and status mappings."""

from __future__ import annotations

from brokers.base import OrderStatus, OrderType

# ---------------------------------------------------------------------------
# IBKR order status -> canonical OrderStatus
# ---------------------------------------------------------------------------

IBKR_STATUS_MAP: dict[str, OrderStatus] = {
    "PreSubmitted": OrderStatus.RECEIVED,
    "PendingSubmit": OrderStatus.RECEIVED,
    "ApiPending": OrderStatus.RECEIVED,
    "Submitted": OrderStatus.CONFIRMED,
    "PendingCancel": OrderStatus.CONFIRMED,
    "Filled": OrderStatus.FILLED,
    "Cancelled": OrderStatus.CANCELED,
    "ApiCancelled": OrderStatus.CANCELED,
    "Inactive": OrderStatus.REJECTED,
}

# ---------------------------------------------------------------------------
# Canonical OrderType -> IBKR order type string
# ---------------------------------------------------------------------------

ORDER_TYPE_TO_IBKR: dict[OrderType, str] = {
    OrderType.MARKET: "MKT",
    OrderType.LIMIT: "LMT",
}

IBKR_TO_ORDER_TYPE: dict[str, OrderType] = {v: k for k, v in ORDER_TYPE_TO_IBKR.items()}

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

RATE_LIMIT_MAX_TOKENS: int = 10
RATE_LIMIT_REFILL_INTERVAL: float = 1.0  # seconds

# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

WS_HEARTBEAT_INTERVAL: float = 10.0  # seconds
WS_RECONNECT_BASE: float = 1.0  # seconds
WS_RECONNECT_CAP: float = 60.0  # seconds

# ---------------------------------------------------------------------------
# Session keepalive
# ---------------------------------------------------------------------------

TICKLE_INTERVAL: float = 55.0  # seconds
TICKLE_MAX_FAILURES: int = 3

# ---------------------------------------------------------------------------
# Contract cache
# ---------------------------------------------------------------------------

CONTRACT_CACHE_TTL: float = 3600.0  # 1 hour in seconds

# ---------------------------------------------------------------------------
# Order confirmation
# ---------------------------------------------------------------------------

MAX_CONFIRM_ROUNDS: int = 5

# ---------------------------------------------------------------------------
# HTTP retry
# ---------------------------------------------------------------------------

HTTP_MAX_RETRIES: int = 3
HTTP_BACKOFF_BASE: float = 1.0  # seconds

# ---------------------------------------------------------------------------
# Default gateway URL
# ---------------------------------------------------------------------------

DEFAULT_GATEWAY_URL: str = "https://localhost:5000"

# ---------------------------------------------------------------------------
# Default TIF (Time In Force)
# ---------------------------------------------------------------------------

DEFAULT_TIF: str = "DAY"
