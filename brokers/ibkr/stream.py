"""IBKR WebSocket order streaming.

Connects to the Client Portal WebSocket endpoint in a background daemon
thread.  Dispatches ``OrderEvent`` DTOs to registered callbacks when
``sor`` (Smart Order Routing) messages arrive.
"""

from __future__ import annotations

import json
import logging
import ssl
import threading
import time
from typing import Any, Optional

import websocket  # websocket-client

from brokers.base import OrderCallback, OrderEvent, OrderStatus
from brokers.ibkr.constants import (
    IBKR_STATUS_MAP,
    WS_HEARTBEAT_INTERVAL,
    WS_RECONNECT_BASE,
    WS_RECONNECT_CAP,
)

logger = logging.getLogger(__name__)


class IBKROrderStream:
    """Background WebSocket stream for IBKR order updates.

    Parameters
    ----------
    gateway_url:
        Base gateway URL (e.g. ``https://localhost:5000``).
        The ``wss://`` endpoint is derived by replacing the scheme.
    """

    def __init__(self, gateway_url: str) -> None:
        # Build WS URL: https://host:port -> wss://host:port/v1/api/ws
        ws_base = gateway_url.replace("https://", "wss://").replace("http://", "ws://")
        self._ws_url = f"{ws_base.rstrip('/')}/v1/api/ws"

        self._callbacks: list[OrderCallback] = []
        self._cb_lock = threading.RLock()

        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    # -- callback management ------------------------------------------------

    def add_callback(self, callback: OrderCallback) -> None:
        with self._cb_lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_callback(self, callback: OrderCallback) -> None:
        with self._cb_lock:
            try:
                self._callbacks.remove(callback)
            except ValueError:
                pass

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Start the WebSocket connection in a daemon thread."""
        if self._running:
            return

        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            name="ibkr-ws-stream",
            daemon=True,
        )
        self._thread.start()
        logger.info("IBKR order stream started")

    def stop(self) -> None:
        """Stop the WebSocket connection."""
        self._running = False
        self._stop_event.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        logger.info("IBKR order stream stopped")

    # -- internal -----------------------------------------------------------

    def _run_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        backoff = WS_RECONNECT_BASE

        while not self._stop_event.is_set():
            try:
                self._connect()
            except Exception:
                logger.exception("IBKR WS connection error")

            if self._stop_event.is_set():
                break

            logger.info("IBKR WS reconnecting in %.1fs", backoff)
            self._stop_event.wait(backoff)
            backoff = min(backoff * 2, WS_RECONNECT_CAP)

    def _connect(self) -> None:
        """Create and run a WebSocket connection (blocking)."""
        ssl_opts = {"cert_reqs": ssl.CERT_NONE}

        self._ws = websocket.WebSocketApp(
            self._ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self._ws.run_forever(
            sslopt=ssl_opts,
            ping_interval=WS_HEARTBEAT_INTERVAL,
            ping_timeout=5,
        )

    def _on_open(self, ws: Any) -> None:
        """Subscribe to order updates on connection open."""
        logger.info("IBKR WS connected to %s", self._ws_url)
        # Subscribe to Smart Order Routing updates
        try:
            ws.send("sor+{}")
        except Exception:
            logger.exception("Failed to send SOR subscription")

    def _on_message(self, ws: Any, message: str) -> None:
        """Parse incoming WS messages and dispatch order events."""
        try:
            data = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return

        topic = data.get("topic", "")
        if not topic.startswith("sor"):
            return

        self._dispatch_order_event(data)

    def _on_error(self, ws: Any, error: Any) -> None:
        if not self._stop_event.is_set():
            logger.warning("IBKR WS error: %s", error)

    def _on_close(self, ws: Any, close_status_code: Any, close_msg: Any) -> None:
        logger.info("IBKR WS closed (code=%s)", close_status_code)

    def _dispatch_order_event(self, data: dict) -> None:
        """Convert a SOR message to an OrderEvent and notify callbacks."""
        order_id = str(data.get("orderId", ""))
        if not order_id:
            return

        raw_status = data.get("status", "")
        status = IBKR_STATUS_MAP.get(raw_status, OrderStatus.RECEIVED)

        event = OrderEvent(
            broker="ibkr",
            order_id=order_id,
            ticker=data.get("symbol", data.get("ticker", "")),
            status=status,
            filled_quantity=int(data.get("filledQuantity", 0)),
            unfilled_quantity=int(data.get("remainingQuantity", 0)),
            filled_price=self._safe_float(data.get("avgPrice")),
        )

        with self._cb_lock:
            callbacks = list(self._callbacks)

        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                logger.exception("Order stream callback raised for order %s", order_id)

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
