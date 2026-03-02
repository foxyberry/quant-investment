"""WebSocket connection manager for broadcasting events to clients."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage multiple WebSocket connections and broadcast messages.

    Each ``ConnectionManager`` instance tracks its own set of connected
    clients and can broadcast JSON-serialisable dicts to all of them.

    Usage::

        manager = ConnectionManager()

        # In a WebSocket endpoint:
        await manager.connect(ws)
        ...
        manager.disconnect(ws)

        # From any async context:
        await manager.broadcast({"type": "order", "status": "FILLED"})
    """

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._connections.add(websocket)
        logger.info(
            "WebSocket client connected (total: %d)", len(self._connections)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        self._connections.discard(websocket)
        logger.info(
            "WebSocket client disconnected (total: %d)", len(self._connections)
        )

    async def broadcast(
        self,
        data: Dict[str, Any],
        timeout_seconds: float = 5.0,
        max_concurrent_sends: int = 32,
    ) -> None:
        """Send *data* as JSON to every connected client.

        Connections that fail to receive or exceed *timeout_seconds* are
        silently removed.
        """
        message = json.dumps(data, default=str)
        if not self._connections:
            return

        disconnected: List[WebSocket] = []
        semaphore = asyncio.Semaphore(max(1, max_concurrent_sends))
        connections = list(self._connections)

        async def _send(ws: WebSocket) -> None:
            async with semaphore:
                try:
                    await asyncio.wait_for(
                        ws.send_text(message), timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    disconnected.append(ws)
                except Exception:
                    disconnected.append(ws)

        await asyncio.gather(*(_send(ws) for ws in connections))
        for ws in disconnected:
            self._connections.discard(ws)

    @property
    def connection_count(self) -> int:
        """Return the number of currently active connections."""
        return len(self._connections)
