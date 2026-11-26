"""
PMS Enterprise Idempotency Engine.

Prevents duplicate execution of state-altering mutations (e.g. CMMS work-order dispatch,
predictions during network retries) across unreliable industrial OT/IT networks.
Supports three storage tiers:
1. Optional Redis distributed cache (via REDIS_URL) for multi-worker deployments.
2. Durable PostgreSQL / SQLite persistence (idempotency_keys table) across restarts.
3. Process-local in-memory fallback with TTL eviction.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
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
    """Thread-safe, TTL-evicted idempotency store backed by optional Redis, DB, and memory."""

    def __init__(self, default_ttl_seconds: int = 3600, persist_to_db: bool = False):
        self.default_ttl = default_ttl_seconds
        self.persist_to_db = persist_to_db
        self._store: dict[str, IdempotencyRecord] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        self._redis_client: Any = self._init_redis()

    def _init_redis(self) -> Any:
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            return None
        try:
            redis_mod = importlib.import_module("redis")

            client = redis_mod.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1.5)
            client.ping()
            logger.info("IdempotencyManager connected to Redis distributed store.")
            return client
        except Exception as err:
            logger.debug(f"Redis unavailable for IdempotencyManager (using DB/memory): {err}")
            return None

    def _get_key_lock(self, key: str) -> threading.Lock:
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        """Returns the stored record if present and not expired across memory, Redis, or DB."""
        now = time.time()
        with self._global_lock:
            record = self._store.get(key)
            if record:
                if now > record.expires_at:
                    del self._store[key]
                else:
                    return record

        if self._redis_client is not None:
            try:
                raw = self._redis_client.get(f"pms:idem:{key}")
                if raw:
                    parsed = json.loads(raw)
                    rec = IdempotencyRecord(
                        status_code=int(parsed["status_code"]),
                        data=parsed["data"],
                        created_at=float(parsed["created_at"]),
                        expires_at=float(parsed["expires_at"]),
                    )
                    if now <= rec.expires_at:
                        with self._global_lock:
                            self._store[key] = rec
                        return rec
            except Exception as err:
                logger.debug(f"Redis get fallback on idempotency key: {err}")

        if self.persist_to_db:
            try:
                from backend.database import SessionLocal
                from backend.models import IdempotencyKeyRecord

                with SessionLocal() as db:
                    row = db.query(IdempotencyKeyRecord).filter(IdempotencyKeyRecord.key == key).first()
                    if row is not None:
                        row_any: Any = row
                        exp = float(row_any.expires_at)
                        if now > exp:
                            db.delete(row)
                            db.commit()
                            return None
                        rec = IdempotencyRecord(
                            status_code=int(row_any.status_code),
                            data=row_any.data,
                            created_at=float(row_any.created_at),
                            expires_at=exp,
                        )
                        with self._global_lock:
                            self._store[key] = rec
                        return rec
            except Exception as err:
                logger.debug(f"DB get fallback on idempotency key: {err}")

        return None

    def set(
        self,
        key: str,
        status_code: int,
        data: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Saves a response record under the specified idempotency key across active tiers."""
        ttl = ttl_seconds or self.default_ttl
        now = time.time()
        expires_at = now + ttl
        record = IdempotencyRecord(
            status_code=status_code,
            data=data,
            created_at=now,
            expires_at=expires_at,
        )
        with self._global_lock:
            self._store[key] = record

        if self._redis_client is not None:
            try:
                payload = json.dumps(
                    {
                        "status_code": status_code,
                        "data": data,
                        "created_at": now,
                        "expires_at": expires_at,
                    },
                    default=str,
                )
                self._redis_client.setex(f"pms:idem:{key}", ttl, payload)
            except Exception as err:
                logger.debug(f"Redis set failed for idempotency key: {err}")

        if self.persist_to_db:
            try:
                from backend.database import SessionLocal
                from backend.models import IdempotencyKeyRecord

                with SessionLocal() as db:
                    db_row = IdempotencyKeyRecord(
                        key=key,
                        status_code=status_code,
                        data=data,
                        created_at=now,
                        expires_at=expires_at,
                    )
                    db.merge(db_row)
                    db.commit()
            except Exception as err:
                logger.warning(f"Failed to persist idempotency key to DB: {err}")

    def clear(self) -> None:
        """Purges all stored idempotency keys (useful for test isolation)."""
        with self._global_lock:
            self._store.clear()
            self._locks.clear()

        if self.persist_to_db:
            try:
                from backend.database import SessionLocal
                from backend.models import IdempotencyKeyRecord

                with SessionLocal() as db:
                    db.query(IdempotencyKeyRecord).delete()
                    db.commit()
            except Exception:
                pass

    def prune_expired(self) -> int:
        """Removes expired idempotency records from memory and DB."""
        now = time.time()
        pruned = 0
        with self._global_lock:
            expired_keys = [k for k, v in self._store.items() if now > v.expires_at]
            for k in expired_keys:
                del self._store[k]
                pruned += 1

        if self.persist_to_db:
            try:
                from backend.database import SessionLocal
                from backend.models import IdempotencyKeyRecord

                with SessionLocal() as db:
                    db_pruned = db.query(IdempotencyKeyRecord).filter(IdempotencyKeyRecord.expires_at < now).delete()
                    db.commit()
                    pruned = max(pruned, db_pruned or 0)
            except Exception:
                pass
        return pruned


_idempotency_manager_instance: Optional[IdempotencyManager] = None
_instance_lock = threading.Lock()


def get_idempotency_manager() -> IdempotencyManager:
    """Returns the process-wide IdempotencyManager singleton."""
    global _idempotency_manager_instance
    with _instance_lock:
        if _idempotency_manager_instance is None:
            _idempotency_manager_instance = IdempotencyManager(persist_to_db=True)
        return _idempotency_manager_instance
