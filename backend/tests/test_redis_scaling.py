"""
Tests for Multi-Worker Redis Scaling:
1. Graceful fallback when Redis is unset/unavailable.
2. Distributed leader lock (acquire_distributed_lock SET NX EX semantics).
3. Shared Redis drift cache & invalidation via /drift-status and /drift-status/reset.
4. Cross-worker CanaryManager state sync via Redis.
5. TelemetryBroadcaster Redis Pub/Sub message delivery.
"""

import asyncio
import fnmatch
import os
import time
from typing import Any

from fastapi.testclient import TestClient

import backend.main as main_mod
from backend.canary import CanaryManager
from backend.main import app
from backend.realtime import TELEMETRY_CHANNEL, TelemetryBroadcaster
from backend.redis_client import (
    acquire_distributed_lock,
    cache_delete_prefix,
    cache_get_json,
    cache_set_json,
    get_redis_storage_uri,
    set_redis_client_for_testing,
)

client = TestClient(app)
ADMIN_API_KEY = (os.getenv("PMS_API_KEY") or "").strip()


class _FakePubSub:
    def __init__(self, bus: list[tuple[str, str]]):
        self._bus = bus
        self._channels: set[str] = set()
        self._cursor = len(bus)

    def subscribe(self, channel: str) -> None:
        self._channels.add(channel)

    def listen(self):
        # Yield any newly published messages, then stop gracefully
        deadline = time.time() + 1.5
        while time.time() < deadline:
            if self._cursor < len(self._bus):
                ch, data = self._bus[self._cursor]
                self._cursor += 1
                if ch in self._channels:
                    yield {"type": "message", "channel": ch, "data": data}
                    return
            time.sleep(0.01)


class _FakeRedis:
    def __init__(self):
        self.kv: dict[str, str] = {}
        self.bus: list[tuple[str, str]] = []

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        return self.kv.get(key)

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.kv:
            return False
        self.kv[key] = value
        return True

    def setex(self, key: str, ttl: int, value: str) -> bool:
        self.kv[key] = value
        return True

    def scan_iter(self, match: str = "*"):
        return [k for k in list(self.kv.keys()) if fnmatch.fnmatch(k, match)]

    def delete(self, *keys: str) -> int:
        removed = 0
        for k in keys:
            if k in self.kv:
                del self.kv[k]
                removed += 1
        return removed

    def publish(self, channel: str, message: str) -> int:
        self.bus.append((channel, message))
        return 1

    def pubsub(self, ignore_subscribe_messages: bool = True) -> _FakePubSub:
        return _FakePubSub(self.bus)


def test_redis_fallback_without_redis_server():
    """Verifies safe single-node fallback when REDIS_URL is not configured."""
    set_redis_client_for_testing(None)
    assert get_redis_storage_uri() == "memory://"
    assert acquire_distributed_lock("pms:lock:test_fallback", ttl_seconds=10) is True


def test_distributed_lock_and_drift_cache_across_workers():
    """Verifies atomic lock acquisition and shared Redis drift cache behavior."""
    fake = _FakeRedis()
    set_redis_client_for_testing(fake)
    try:
        # 1. Leader lock succeeds once, blocks second worker
        assert acquire_distributed_lock("pms:lock:drift_check", ttl_seconds=60) is True
        assert acquire_distributed_lock("pms:lock:drift_check", ttl_seconds=60) is False

        # 2. Drift cache read/write/prefix invalidation
        cached_report = {
            "status": "HEALTHY",
            "drift_detected": False,
            "retrain_recommended": False,
            "max_psi": 0.0123,
            "drifted_features": [],
            "analyzed_samples": 42,
            "reference_version": "v18",
            "message": "Served from Redis cache",
            "feature_metrics": [],
        }
        assert cache_set_json("pms:drift_cache:77", cached_report, ttl_seconds=20) is True
        cached_hit = cache_get_json("pms:drift_cache:77")
        assert cached_hit is not None
        assert cached_hit["max_psi"] == 0.0123

        # Clear local in-memory cache and confirm /drift-status?window=77 hits Redis
        main_mod._drift_cache["report"] = None
        res = client.get("/drift-status?window=77")
        assert res.status_code == 200
        assert res.json()["message"] == "Served from Redis cache"

        # Reset clears Redis drift cache keys
        reset_res = client.post("/drift-status/reset", headers={"X-API-Key": ADMIN_API_KEY})
        assert reset_res.status_code == 200
        assert cache_get_json("pms:drift_cache:77") is None

        cache_set_json("pms:drift_cache:99", {"max_psi": 0.1}, ttl_seconds=20)
        cache_delete_prefix("pms:drift_cache:")
        assert cache_get_json("pms:drift_cache:99") is None
    finally:
        set_redis_client_for_testing(None)
        main_mod._drift_cache["report"] = None


def test_canary_manager_syncs_state_via_redis():
    """Verifies CanaryManager writes state to Redis so sibling workers observe active rollouts."""
    fake = _FakeRedis()
    set_redis_client_for_testing(fake)
    try:
        worker_a = CanaryManager()
        worker_a.is_active = True
        worker_a.canary_version = "v99-candidate"
        worker_a.evaluated_requests = 12
        worker_a.remaining_requests = 38
        worker_a._sync_to_redis()

        # Sibling worker B (standby locally) reads active state from Redis
        worker_b = CanaryManager()
        status_b = worker_b.get_status()
        assert status_b["is_active"] is True
        assert status_b["canary_version"] == "v99-candidate"
        assert status_b["evaluated_requests"] == 12
    finally:
        set_redis_client_for_testing(None)


def test_telemetry_broadcaster_redis_pubsub():
    """Verifies TelemetryBroadcaster publishes and receives events over Redis Pub/Sub."""
    fake = _FakeRedis()
    set_redis_client_for_testing(fake)
    try:
        broadcaster = TelemetryBroadcaster()
        loop = asyncio.new_event_loop()

        class _DummyWS:
            pass

        ws: Any = _DummyWS()
        queue = broadcaster.subscribe(ws, loop)
        time.sleep(0.05)  # Give subscriber thread a moment to attach
        broadcaster.publish({"type": "prediction", "asset_id": "REDIS-PUMP-01"})

        # Run loop briefly to process call_soon_threadsafe callback
        deadline = time.time() + 1.0
        received = None
        while time.time() < deadline and received is None:
            loop.run_until_complete(asyncio.sleep(0.02))
            if not queue.empty():
                received = queue.get_nowait()

        assert received is not None
        assert received["asset_id"] == "REDIS-PUMP-01"
        assert len(fake.bus) == 1
        assert fake.bus[0][0] == TELEMETRY_CHANNEL
        broadcaster.unsubscribe(ws)
        loop.close()
    finally:
        set_redis_client_for_testing(None)
