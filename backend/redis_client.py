"""
Shared Redis client and distributed coordination utilities for multi-worker PMS deployments.

Provides graceful fallback to process-local / memory behavior when REDIS_URL is unset
or Redis is temporarily unreachable, ensuring zero downtime in single-node or CI runs.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import threading
import uuid
from typing import Any

logger = logging.getLogger("pms.redis")

_client_lock = threading.Lock()
_cached_client: Any = None
_client_initialized = False


def get_redis_client(force_refresh: bool = False) -> Any:
    """Returns a connected Redis client if REDIS_URL is configured and reachable, else None."""
    global _cached_client, _client_initialized
    with _client_lock:
        if _client_initialized and not force_refresh:
            return _cached_client

        _client_initialized = True
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            _cached_client = None
            return None

        try:
            redis_mod = importlib.import_module("redis")
            client = redis_mod.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1.5)
            client.ping()
            _cached_client = client
            logger.info("Connected to Redis distributed coordination layer.")
            return _cached_client
        except Exception as err:
            logger.debug(f"Redis unavailable (falling back to local in-memory mode): {err}")
            _cached_client = None
            return None


def set_redis_client_for_testing(client: Any) -> None:
    """Injects a mock/fake Redis client for unit testing (or pass None to reset)."""
    global _cached_client, _client_initialized
    with _client_lock:
        _cached_client = client
        _client_initialized = client is not None


def get_redis_storage_uri() -> str:
    """Returns REDIS_URL for SlowAPI/distributed rate limiting if reachable, else 'memory://'."""
    client = get_redis_client()
    if client is not None:
        redis_url = os.getenv("REDIS_URL", "").strip()
        if redis_url:
            return redis_url
    return "memory://"


def cache_get_json(key: str) -> Any | None:
    """Reads and JSON-decodes a key from Redis; returns None on miss or unavailability."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception as err:
        logger.debug(f"Redis cache_get_json failed for {key}: {err}")
        return None


def cache_set_json(key: str, value: Any, ttl_seconds: int = 60) -> bool:
    """JSON-encodes and writes a key to Redis with TTL."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except Exception as err:
        logger.debug(f"Redis cache_set_json failed for {key}: {err}")
        return False


def cache_delete_prefix(prefix: str) -> None:
    """Deletes keys matching prefix* from Redis when supported."""
    client = get_redis_client()
    if client is None:
        return
    try:
        keys = list(client.scan_iter(match=f"{prefix}*"))
        if keys:
            client.delete(*keys)
    except Exception as err:
        logger.debug(f"Redis cache_delete_prefix failed for {prefix}: {err}")


def acquire_distributed_lock(lock_key: str, ttl_seconds: int = 60) -> bool:
    """
    Attempts atomic lock acquisition via Redis SET NX EX.
    When Redis is not active (single-worker mode), returns True so local execution proceeds.
    """
    client = get_redis_client()
    if client is None:
        return True
    try:
        token = f"{os.getpid()}:{uuid.uuid4().hex[:8]}"
        acquired = client.set(lock_key, token, nx=True, ex=ttl_seconds)
        return bool(acquired)
    except Exception as err:
        logger.debug(f"Redis lock fallback for {lock_key}: {err}")
        return True
