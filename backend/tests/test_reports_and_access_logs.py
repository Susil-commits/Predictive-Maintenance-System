"""
Tests for PostgreSQL-backed Diagnostic Reports and User Access Logs.
"""

import os
import uuid

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)
ADMIN_API_KEY = (os.getenv("PMS_API_KEY") or "").strip()


def test_reports_and_access_logs_require_auth():
    assert client.get("/reports").status_code == 401
    assert client.post("/reports", json={"risk": "LOW"}).status_code == 401
    assert client.get("/auth/access-logs").status_code == 401
    assert client.post("/auth/access-logs", json={"page": "dashboard"}).status_code == 401


def test_employee_and_admin_report_and_access_log_lifecycle():
    emp_username = f"emp_rep_{uuid.uuid4().hex[:6]}"
    other_username = f"emp_oth_{uuid.uuid4().hex[:6]}"
    password = "TestEmpPassword123!"

    # 1. Admin creates two employee accounts
    r1 = client.post(
        "/auth/users",
        headers={"X-API-Key": ADMIN_API_KEY},
        json={"username": emp_username, "password": password, "role": "employee", "designation": "Analyst"},
    )
    assert r1.status_code == 201
    emp_id = r1.json()["id"]

    r2 = client.post(
        "/auth/users",
        headers={"X-API-Key": ADMIN_API_KEY},
        json={"username": other_username, "password": password, "role": "employee"},
    )
    assert r2.status_code == 201
    other_id = r2.json()["id"]

    try:
        # 2. Employee 1 logs in -> automatically records login access log
        login_res = client.post("/auth/login", json={"username": emp_username, "password": password})
        assert login_res.status_code == 200
        emp_token = login_res.json()["access_token"]
        emp_headers = {"Authorization": f"Bearer {emp_token}"}

        # Employee 1 records dashboard access
        acc_res = client.post("/auth/access-logs", headers=emp_headers, json={"page": "dashboard"})
        assert acc_res.status_code == 201
        assert acc_res.json()["page"] == "dashboard"
        assert acc_res.json()["userId"] == emp_id

        # Employee 1 lists access logs (scoped to self)
        emp_logs = client.get("/auth/access-logs", headers=emp_headers)
        assert emp_logs.status_code == 200
        pages = {item["page"] for item in emp_logs.json()}
        assert {"login", "dashboard"}.issubset(pages)
        assert all(item["userId"] == emp_id for item in emp_logs.json())

        # 3. Employee 1 saves a diagnostic report
        save_res = client.post(
            "/reports",
            headers=emp_headers,
            json={
                "predictionId": f"pred-{uuid.uuid4().hex[:8]}",
                "risk": "HIGH",
                "probability": 0.87,
                "inputData": {"temperature": 93.0, "rpm": 2800},
                "shapFactors": [{"factor": "temperature", "impact": 0.42}],
                "userName": emp_username,
                "userDesignation": "Analyst",
            },
        )
        assert save_res.status_code == 201
        saved = save_res.json()
        report_id = saved["reportId"]
        assert saved["userId"] == emp_id
        assert saved["risk"] == "HIGH"

        # 4. Employee 2 cannot view or delete Employee 1's report
        login_2 = client.post("/auth/login", json={"username": other_username, "password": password})
        other_headers = {"Authorization": f"Bearer {login_2.json()['access_token']}"}
        other_reports = client.get("/reports", headers=other_headers).json()
        assert all(r["reportId"] != report_id for r in other_reports)

        forbidden_del = client.delete(f"/reports/{report_id}", headers=other_headers)
        assert forbidden_del.status_code == 403

        # 5. Admin sees all reports and all access logs
        admin_reports = client.get("/reports", headers={"X-API-Key": ADMIN_API_KEY}).json()
        assert any(r["reportId"] == report_id for r in admin_reports)

        admin_logs = client.get("/auth/access-logs", headers={"X-API-Key": ADMIN_API_KEY}).json()
        assert any(log_item["userId"] == emp_id for log_item in admin_logs)

        # 6. Owner deletes report
        del_res = client.delete(f"/reports/{report_id}", headers=emp_headers)
        assert del_res.status_code == 200

        # Non-admin cannot clear global access logs or reports
        assert client.delete("/auth/access-logs", headers=emp_headers).status_code == 403
        assert client.delete("/reports", headers=emp_headers).status_code == 403
    finally:
        client.delete(f"/auth/users/{emp_id}", headers={"X-API-Key": ADMIN_API_KEY})
        client.delete(f"/auth/users/{other_id}", headers={"X-API-Key": ADMIN_API_KEY})
