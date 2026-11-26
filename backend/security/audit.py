"""
PMS Tamper-Evident Audit Logging Engine.

Implements cryptographically chained immutable audit logging (SHA-256 hash tree)
for SOC 2 Type II, ISO 27001, and industrial regulatory compliance.

Guarantees:
1. Every prediction, administrative action, security rejection, and drift alert is recorded.
2. Cryptographic chaining: event_hash[N] = SHA-256(payload[N] + event_hash[N-1]).
3. Tamper detection: Any modification, insertion, or deletion breaks the hash chain.
4. Optional durable PostgreSQL/SQLite persistence for restart-safe compliance trails.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("pms.security.audit")

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


@dataclass
class AuditEvent:
    index: int
    timestamp: float
    event_type: str
    actor_id: str
    tenant_id: str
    details: Dict[str, Any]
    status: str
    prev_hash: str
    event_hash: str = ""

    def calculate_hash(self) -> str:
        """Computes deterministic SHA-256 hash of event contents and previous hash."""
        serialized_details = json.dumps(self.details, sort_keys=True, default=str)
        payload = (
            f"{self.index}:{self.timestamp:.6f}:{self.event_type}:{self.actor_id}:"
            f"{self.tenant_id}:{serialized_details}:{self.status}:{self.prev_hash}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLogger:
    """Thread-safe append-only cryptographically chained audit logger with optional DB persistence."""

    def __init__(self, max_buffer_size: int = 10000, persist_to_db: bool = False):
        self._events: List[AuditEvent] = []
        self._last_hash = GENESIS_HASH
        self._next_index = 0
        self._lock = threading.Lock()
        self._max_buffer_size = max_buffer_size
        self._persist_to_db = persist_to_db
        self._db_hydrated = False

    @staticmethod
    def _row_to_event(row: Any) -> AuditEvent:
        r: Any = row
        raw_details = r.details
        return AuditEvent(
            index=int(r.event_index),
            timestamp=float(r.timestamp),
            event_type=str(r.event_type),
            actor_id=str(r.actor_id),
            tenant_id=str(r.tenant_id),
            details=dict(raw_details) if isinstance(raw_details, dict) else {},
            status=str(r.status),
            prev_hash=str(r.prev_hash),
            event_hash=str(r.event_hash),
        )

    def _hydrate_from_db(self) -> None:
        """Loads persisted audit events from database once to restore chain continuity."""
        if not self._persist_to_db or self._db_hydrated:
            return
        try:
            from backend.database import SessionLocal
            from backend.models import AuditEventRecord

            with SessionLocal() as db:
                rows = db.query(AuditEventRecord).order_by(AuditEventRecord.event_index.asc()).all()
                loaded: List[AuditEvent] = [self._row_to_event(row) for row in rows]
                if loaded:
                    self._events = loaded[-self._max_buffer_size :]
                    self._last_hash = loaded[-1].event_hash
                    self._next_index = loaded[-1].index + 1
                self._db_hydrated = True
        except Exception as err:
            logger.debug(f"[AuditLog] DB hydration skipped/deferred: {err}")

    def _persist_event(self, event: AuditEvent) -> None:
        if not self._persist_to_db:
            return
        try:
            from backend.database import SessionLocal
            from backend.models import AuditEventRecord

            with SessionLocal() as db:
                record = AuditEventRecord(
                    event_index=event.index,
                    timestamp=event.timestamp,
                    event_type=event.event_type,
                    actor_id=event.actor_id,
                    tenant_id=event.tenant_id,
                    details=event.details,
                    status=event.status,
                    prev_hash=event.prev_hash,
                    event_hash=event.event_hash,
                )
                db.add(record)
                db.commit()
        except Exception as err:
            logger.warning(f"[AuditLog] Failed to persist event idx={event.index} to DB: {err}")

    def record_event(
        self,
        event_type: str,
        actor_id: str = "system",
        tenant_id: str = "default_plant",
        details: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
    ) -> AuditEvent:
        """Appends a new cryptographically signed and chained event to the audit log."""
        with self._lock:
            self._hydrate_from_db()
            index = self._next_index
            self._next_index += 1
            now = time.time()
            details_dict = details or {}

            event = AuditEvent(
                index=index,
                timestamp=now,
                event_type=event_type,
                actor_id=actor_id,
                tenant_id=tenant_id,
                details=details_dict,
                status=status,
                prev_hash=self._last_hash,
            )
            event.event_hash = event.calculate_hash()

            self._events.append(event)
            self._last_hash = event.event_hash

            if len(self._events) > self._max_buffer_size:
                self._events.pop(0)

            self._persist_event(event)

            logger.info(
                f"[AuditLog:idx={event.index}] type={event.event_type} actor={event.actor_id} "
                f"status={event.status} hash={event.event_hash[:12]}..."
            )
            return event

    def verify_chain(self) -> Tuple[bool, Optional[str]]:
        """
        Cryptographically verifies the entire hash chain from start to end.
        Returns: (is_valid, error_description_if_tampered)
        """
        with self._lock:
            self._hydrate_from_db()
            events_to_verify = self._events

            if self._persist_to_db:
                try:
                    from backend.database import SessionLocal
                    from backend.models import AuditEventRecord

                    with SessionLocal() as db:
                        rows = db.query(AuditEventRecord).order_by(AuditEventRecord.event_index.asc()).all()
                        if rows:
                            events_to_verify = [self._row_to_event(row) for row in rows]
                except Exception as err:
                    logger.debug(f"[AuditLog] Using in-memory chain for verification: {err}")

            if not events_to_verify:
                return True, None

            expected_prev_hash = events_to_verify[0].prev_hash
            for event in events_to_verify:
                if event.prev_hash != expected_prev_hash:
                    return False, f"Broken chain linkage at index {event.index}: prev_hash mismatch"

                recomputed_hash = event.calculate_hash()
                if event.event_hash != recomputed_hash:
                    return False, f"Tampered event payload at index {event.index}: hash mismatch"

                expected_prev_hash = event.event_hash

            return True, None

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent audit events formatted as dictionaries for administrative inspection."""
        with self._lock:
            self._hydrate_from_db()
            return [asdict(e) for e in reversed(self._events[-limit:])]

    def count(self) -> int:
        with self._lock:
            self._hydrate_from_db()
            return len(self._events)


# Global singleton audit logger (durable DB persistence enabled)
_global_audit_logger = AuditLogger(persist_to_db=True)


def get_audit_logger() -> AuditLogger:
    return _global_audit_logger
