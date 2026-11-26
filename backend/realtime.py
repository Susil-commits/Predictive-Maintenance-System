"""
Real-time telemetry WebSocket broadcaster for PMS.

Bridges synchronous ML inference endpoints running in worker threads
to asynchronous WebSocket subscribers on the ASGI event loop.
Supports multi-worker fan-out via Redis Pub/Sub when REDIS_URL is configured.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

from fastapi import WebSocket

from .redis_client import get_redis_client

logger = logging.getLogger("pms.realtime")

TELEMETRY_CHANNEL = "pms:telemetry:stream"


class TelemetryBroadcaster:
    """Thread-safe pub/sub fan-out manager for live telemetry WebSocket streams."""

    def __init__(self, max_queue_size: int = 100):
        self._lock = threading.Lock()
        self._subscribers: dict[WebSocket, tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, Any]]]] = {}
        self._max_queue_size = max_queue_size
        self._pubsub_thread_started = False

    def _ensure_redis_subscriber(self) -> None:
        """Starts a background Redis Pub/Sub listener thread once when Redis is available."""
        with self._lock:
            if self._pubsub_thread_started:
                return
            client = get_redis_client()
            if client is None or not hasattr(client, "pubsub"):
                return
            self._pubsub_thread_started = True

        def _listen_loop() -> None:
            try:
                pubsub = client.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(TELEMETRY_CHANNEL)
                for msg in pubsub.listen():
                    if msg and msg.get("type") == "message":
                        try:
                            event = json.loads(msg["data"])
                            self._deliver_local(event)
                        except Exception:
                            pass
            except Exception as err:
                logger.debug(f"[WS Redis PubSub] Listener stopped: {err}")
                with self._lock:
                    self._pubsub_thread_started = False

        threading.Thread(target=_listen_loop, name="pms-ws-redis-pubsub", daemon=True).start()

    def subscribe(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop) -> asyncio.Queue[dict[str, Any]]:
        self._ensure_redis_subscriber()
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

    def _deliver_local(self, event: dict[str, Any]) -> None:
        with self._lock:
            targets = list(self._subscribers.values())

        for loop, queue in targets:
            try:
                if loop.is_closed():
                    continue
                loop.call_soon_threadsafe(self._enqueue_nowait, queue, event)
            except Exception as err:
                logger.debug(f"[WS] Failed to schedule broadcast: {err}")

    def publish(self, event: dict[str, Any]) -> None:
        """Broadcasts an event across all workers (via Redis Pub/Sub if active, else locally)."""
        client = get_redis_client()
        if client is not None and hasattr(client, "publish"):
            try:
                client.publish(TELEMETRY_CHANNEL, json.dumps(event, default=str))
                if self._pubsub_thread_started:
                    return
            except Exception as err:
                logger.debug(f"[WS Redis PubSub] Publish failed, falling back locally: {err}")

        self._deliver_local(event)

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
