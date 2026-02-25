"""Tiger Brokers order streaming via PushClient.

Wraps the ``tigeropen`` SDK's ``PushClient`` to deliver real-time
``OrderEvent`` DTOs to registered callbacks.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from brokers.base import OrderCallback, OrderEvent, OrderStatus
from brokers.tiger.constants import TIGER_STATUS_MAP

logger = logging.getLogger(__name__)


class TigerOrderStream:
    """PushClient wrapper for real-time order updates.

    Parameters
    ----------
    config:
        A ``TigerOpenClientConfig`` instance (from ``TigerSession.config``).
    account:
        The account to subscribe order updates for.
    """

    def __init__(self, config: Any, account: str) -> None:
        self._config = config
        self._account = account

        self._callbacks: list[OrderCallback] = []
        self._cb_lock = threading.RLock()

        self._push_client: Any = None
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
        """Connect PushClient and subscribe to order updates."""
        if self._running:
            return

        try:
            from tigeropen.push.push_client import PushClient

            self._push_client = PushClient(self._config)
            self._push_client.order_changed = self._on_order_changed
            self._push_client.connect(self._config.tiger_id, self._config.private_key)
            self._push_client.subscribe_order(account=self._account)
            self._running = True
            logger.info("Tiger order stream started for account %s", self._account)
        except Exception:
            logger.exception("Failed to start Tiger order stream")
            raise

    def stop(self) -> None:
        """Unsubscribe and disconnect PushClient."""
        if self._push_client:
            try:
                self._push_client.unsubscribe_order()
            except Exception:
                logger.debug("Error unsubscribing Tiger orders", exc_info=True)
            try:
                self._push_client.disconnect()
            except Exception:
                logger.debug("Error disconnecting Tiger push client", exc_info=True)

        self._push_client = None
        self._running = False
        logger.info("Tiger order stream stopped")

    # -- internal -----------------------------------------------------------

    def _on_order_changed(self, frame: Any) -> None:
        """Convert an OrderStatusData frame to OrderEvent and dispatch."""
        try:
            order_id = str(getattr(frame, "id", "") or "")
            if not order_id:
                return

            ticker = str(getattr(frame, "symbol", "") or "")

            raw_status = str(getattr(frame, "status", "") or "")
            status = TIGER_STATUS_MAP.get(raw_status, OrderStatus.RECEIVED)

            filled_qty = self._safe_int(getattr(frame, "filled", 0))
            total_qty = self._safe_int(getattr(frame, "quantity", 0))
            unfilled_qty = max(0, total_qty - filled_qty)

            filled_price = self._safe_float(getattr(frame, "avg_fill_price", None))

            event = OrderEvent(
                broker="tiger",
                order_id=order_id,
                ticker=ticker,
                status=status,
                filled_quantity=filled_qty,
                unfilled_quantity=unfilled_qty,
                filled_price=filled_price,
            )

            with self._cb_lock:
                callbacks = list(self._callbacks)

            for cb in callbacks:
                try:
                    cb(event)
                except Exception:
                    logger.exception(
                        "Tiger order stream callback raised for order %s", order_id
                    )

        except Exception:
            logger.exception("Error processing Tiger order update")

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
