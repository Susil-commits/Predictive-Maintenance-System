"""
Real-time telemetry WebSocket broadcaster for PMS.

Bridges synchronous ML inference endpoints running in worker threads
to asynchronous WebSocket subscribers on the ASGI event loop.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("pms.realtime")


class TelemetryBroadcaster:
    """Thread-safe pub/sub fan-out manager for live telemetry WebSocket streams."""

    def __init__(self, max_queue_size: int = 100):
        self._lock = threading.Lock()
        self._subscribers: dict[WebSocket, tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, Any]]]] = {}
        self._max_queue_size = max_queue_size

    def subscribe(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._max_queue_size)
        with self._lock:
            self._subscribers[websocket] = (loop, queue)
        logger.debug(f"[WS] Client subscribed (total={len(self._subscribers)})")
        return queue

    def unsubscribe(self, websocket: WebSocket) -> None:
        with self._lock:
            self._subscribers.pop(websocket, None)
        logger.debug(f"[WS] Client unsubscribed (total={len(self._subscribers)})")

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def publish(self, event: dict[str, Any]) -> None:
        """Broadcasts an event from any sync/async thread to all connected WebSocket clients."""
        with self._lock:
            targets = list(self._subscribers.values())

        for loop, queue in targets:
            try:
                if loop.is_closed():
                    continue
                loop.call_soon_threadsafe(self._enqueue_nowait, queue, event)
            except Exception as err:
                logger.debug(f"[WS] Failed to schedule broadcast: {err}")

    @staticmethod
    def _enqueue_nowait(queue: asyncio.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


telemetry_broadcaster = TelemetryBroadcaster()
