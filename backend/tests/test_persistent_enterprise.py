"""
Tests for Track 3 Persistent Enterprise Storage:
1. CMMS Work Order persistence, listing, and resolution feedback lifecycle.
2. DB-backed IdempotencyManager survival across process/instance restarts.
3. DB-backed SHA-256 AuditLogger hydration and hash-chain verification across restarts.
"""

import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.security.audit import AuditLogger, get_audit_logger
from backend.security.idempotency import IdempotencyManager

client = TestClient(app)


def test_cmms_work_order_persistence_and_lifecycle():
    """Verifies work orders persist in DB and support IN_PROGRESS -> RESOLVED transitions."""
    asset_id = f"CNC-WO-{uuid.uuid4().hex[:6].upper()}"
    dispatch_res = client.post(
        "/maintenance/dispatch-work-order",
        json={
            "asset_id": asset_id,
            "line_id": "Line 7 - Stamping",
            "plant_location": "Plant 3 - Bay A2",
            "failure_mode": "Thermal Runaway",
            "priority": "CRITICAL",
            "notes": "Spindle cooling delta exceeded threshold.",
        },
    )
    assert dispatch_res.status_code == 200
    wo = dispatch_res.json()
    wo_id = wo["work_order_id"]
    assert wo["status"] == "DISPATCHED_TO_CMMS"

    # Retrieve persisted work order via list endpoint
    list_res = client.get(f"/maintenance/work-orders?asset_id={asset_id}")
    assert list_res.status_code == 200
    orders = list_res.json()
    assert any(o["work_order_id"] == wo_id for o in orders)

    # Transition to IN_PROGRESS
    prog_res = client.patch(
        f"/maintenance/work-orders/{wo_id}",
        json={"status": "IN_PROGRESS"},
    )
    assert prog_res.status_code == 200
    assert prog_res.json()["status"] == "IN_PROGRESS"

    # Transition to RESOLVED with ground-truth feedback
    res_res = client.patch(
        f"/maintenance/work-orders/{wo_id}",
        json={
            "status": "RESOLVED",
            "resolution_notes": "Replaced thermal gasket and flushed coolant line.",
            "actual_failure_confirmed": True,
        },
    )
    assert res_res.status_code == 200
    resolved = res_res.json()
    assert resolved["status"] == "RESOLVED"
    assert resolved["actual_failure_confirmed"] is True
    assert resolved["resolved_at"] is not None


def test_idempotency_persists_across_manager_restart():
    """Verifies IdempotencyManager survives in-memory eviction via DB persistence."""
    key = f"PERSIST-IDEM-{uuid.uuid4().hex}"
    writer = IdempotencyManager(default_ttl_seconds=300, persist_to_db=True)
    writer.set(key, 200, {"work_order_id": "WO-PERSIST-001", "status": "DISPATCHED_TO_CMMS"})

    # Simulate fresh worker process with empty memory store
    reader = IdempotencyManager(default_ttl_seconds=300, persist_to_db=True)
    assert key not in reader._store
    replayed = reader.get(key)
    assert replayed is not None
    assert replayed.status_code == 200
    assert replayed.data["work_order_id"] == "WO-PERSIST-001"


def test_audit_logger_persists_and_hydrates_hash_chain():
    """Verifies global AuditLogger persists SHA-256 chained events and reloads cleanly."""
    global_logger = get_audit_logger()
    marker = f"audit-marker-{uuid.uuid4().hex[:8]}"
    ev = global_logger.record_event(
        event_type="TEST_PERSISTENT_AUDIT",
        actor_id="pytest",
        details={"marker": marker},
    )
    assert ev.event_hash

    # Simulate fresh process hydrating from audit_events table
    reloaded = AuditLogger(persist_to_db=True)
    recent = reloaded.get_recent_events(limit=20)
    assert any(item["details"].get("marker") == marker for item in recent)
    is_valid, err = reloaded.verify_chain()
    assert is_valid is True, f"Persisted audit chain failed verification: {err}"
