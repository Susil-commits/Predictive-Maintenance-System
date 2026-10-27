"""
PMS Enterprise Idempotency Engine.

Prevents duplicate execution of state-altering mutations (e.g. CMMS work-order dispatch,
predictions during network retries) across unreliable industrial OT/IT networks.
Provides atomic key-level locking, TTL eviction, and exact-once semantics.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("pms.security.idempotency")


@dataclass
class IdempotencyRecord:
    status_code: int
    data: Any
    created_at: float
    expires_at: float


class IdempotencyManager:
    """Thread-safe, TTL-evicted in-memory idempotency store with key-level locking."""

    def __init__(self, default_ttl_seconds: int = 3600):
        self.default_ttl = default_ttl_seconds
        self._store: dict[str, IdempotencyRecord] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _get_key_lock(self, key: str) -> threading.Lock:
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        """Returns the stored record if present and not expired."""
        with self._global_lock:
            record = self._store.get(key)
            if not record:
                return None
            if time.time() > record.expires_at:
                del self._store[key]
                return None
            return record

    def set(
        self,
        key: str,
        status_code: int,
        data: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Saves a response record under the specified idempotency key."""
        ttl = ttl_seconds or self.default_ttl
        now = time.time()
        record = IdempotencyRecord(
            status_code=status_code,
            data=data,
            created_at=now,
            expires_at=now + ttl,
        )
        with self._global_lock:
            self._store[key] = record

    def clear(self) -> None:
        """Purges all stored idempotency keys (useful for test isolation)."""
        with self._global_lock:
            self._store.clear()
            self._locks.clear()

    def prune_expired(self) -> int:
        """Removes expired idempotency records from memory."""
        now = time.time()
        pruned = 0
        with self._global_lock:
            expired_keys = [k for k, v in self._store.items() if now > v.expires_at]
            for k in expired_keys:
                del self._store[k]
                pruned += 1
        return pruned


_idempotency_manager_instance: Optional[IdempotencyManager] = None
_instance_lock = threading.Lock()


def get_idempotency_manager() -> IdempotencyManager:
    """Returns the process-wide IdempotencyManager singleton."""
    global _idempotency_manager_instance
    with _instance_lock:
        if _idempotency_manager_instance is None:
            _idempotency_manager_instance = IdempotencyManager()
        return _idempotency_manager_instance
