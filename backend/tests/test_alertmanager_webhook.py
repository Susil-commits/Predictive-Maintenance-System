"""
Tests for Prometheus Alertmanager webhook ingestion and Ops alert feed:
- Rejects unauthenticated webhook calls (401)
- Accepts X-API-Key and Bearer ALERTMANAGER_WEBHOOK_SECRET
- Persists tamper-evident PROMETHEUS_ALERT audit records
- Auto-dispatches deduplicated CMMS work orders for critical asset-scoped firing alerts
- Supports severity and status filtering on GET /ops/alerts
"""

import os
import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.security.audit import get_audit_logger

client = TestClient(app)
ADMIN_API_KEY = (os.getenv("PMS_API_KEY") or "").strip()


def test_alertmanager_webhook_requires_auth():
    res = client.post(
        "/ops/alerts/webhook",
        json={"status": "firing", "alerts": []},
    )
    assert res.status_code == 401


def test_alertmanager_webhook_bearer_secret_and_ops_feed(monkeypatch):
    monkeypatch.setenv("ALERTMANAGER_WEBHOOK_SECRET", "alertmanager-ci-bearer-secret")
    fp = f"fp-{uuid.uuid4().hex[:8]}"

    res = client.post(
        "/ops/alerts/webhook",
        headers={"Authorization": "Bearer alertmanager-ci-bearer-secret"},
        json={
            "status": "firing",
            "receiver": "pms-backend-webhook",
            "alerts": [
                {
                    "status": "firing",
                    "fingerprint": fp,
                    "labels": {
                        "alertname": "PMSDataDriftCritical",
                        "severity": "critical",
                        "asset_id": "CNC-MILL-99",
                        "line_id": "Line-B",
                    },
                    "annotations": {
                        "summary": "Thermal drift breach",
                        "description": "PSI reached 0.34 on CNC-MILL-99",
                    },
                }
            ],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["received_alerts"] == 1
    assert body["recorded_events"] == 1
    assert len(body["dispatched_work_orders"]) == 1
    wo_id = body["dispatched_work_orders"][0]

    # Repeat webhook notification for the same firing fingerprint must NOT create a duplicate work order
    repeat_res = client.post(
        "/ops/alerts/webhook",
        headers={"X-API-Key": ADMIN_API_KEY},
        json={
            "status": "firing",
            "receiver": "pms-backend-webhook",
            "alerts": [
                {
                    "status": "firing",
                    "fingerprint": fp,
                    "labels": {
                        "alertname": "PMSDataDriftCritical",
                        "severity": "critical",
                        "asset_id": "CNC-MILL-99",
                    },
                    "annotations": {"summary": "Thermal drift breach"},
                }
            ],
        },
    )
    assert repeat_res.status_code == 200
    assert repeat_res.json()["dispatched_work_orders"] == []

    # Resolved alert should log cleanly with no work-order dispatch
    resolved_res = client.post(
        "/ops/alerts/webhook",
        headers={"X-API-Key": ADMIN_API_KEY},
        json={
            "status": "resolved",
            "alerts": [
                {
                    "status": "resolved",
                    "fingerprint": fp,
                    "labels": {"alertname": "PMSDataDriftCritical", "severity": "critical"},
                    "annotations": {"summary": "Resolved"},
                }
            ],
        },
    )
    assert resolved_res.status_code == 200
    assert resolved_res.json()["dispatched_work_orders"] == []

    # Ops alerts feed filters accurately and exposes dispatched work_order_id
    ops_res = client.get(
        "/ops/alerts?severity=critical&status=firing&limit=20",
        headers={"X-API-Key": ADMIN_API_KEY},
    )
    assert ops_res.status_code == 200
    alerts = ops_res.json()
    matched = [a for a in alerts if a.get("fingerprint") == fp]
    assert len(matched) >= 1
    assert matched[0]["work_order_id"] == wo_id
    assert matched[0]["status"] == "firing"

    # Cryptographic audit chain remains valid
    is_valid, err = get_audit_logger().verify_chain()
    assert is_valid is True, err
