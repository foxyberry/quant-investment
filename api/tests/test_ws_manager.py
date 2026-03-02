"""Tests for websocket connection manager broadcast behavior."""

import asyncio
import time

from api.services.ws_manager import ConnectionManager


class _FakeWebSocket:
    def __init__(self, delay: float = 0.0, fail: bool = False):
        self.delay = delay
        self.fail = fail
        self.messages: list[str] = []

    async def send_text(self, message: str) -> None:
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("send failed")
        self.messages.append(message)


def test_broadcast_removes_failed_connections() -> None:
    manager = ConnectionManager()
    ok = _FakeWebSocket()
    bad = _FakeWebSocket(fail=True)
    manager._connections = {ok, bad}

    asyncio.run(manager.broadcast({"type": "ping"}, timeout_seconds=0.2))

    assert manager.connection_count == 1
    assert ok in manager._connections
    assert bad not in manager._connections


def test_broadcast_sends_concurrently() -> None:
    manager = ConnectionManager()
    ws1 = _FakeWebSocket(delay=0.05)
    ws2 = _FakeWebSocket(delay=0.05)
    manager._connections = {ws1, ws2}

    start = time.perf_counter()
    asyncio.run(manager.broadcast({"type": "ping"}, timeout_seconds=0.2, max_concurrent_sends=2))
    elapsed = time.perf_counter() - start

    assert elapsed < 0.09
    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 1
