"""
Tests for PMS Model Context Protocol (MCP) Server.

Validates JSON-RPC 2.0 compliance for:
- initialize and handshake
- tools/list and tools/call
- resources/list and resources/read
- prompts/list and prompts/get
- FastAPI /mcp gateway integration
"""

import json
from starlette.testclient import TestClient

from backend.main import app
from backend.mcp_server import mcp_server

client = TestClient(app)

SAMPLE_TELEMETRY = {
    "temperature": 88.0,
    "rpm": 2600.0,
    "pressure": 30.0,
    "vibration": 0.52,
    "operating_hours": 3800.0,
}


def test_mcp_initialize():
    """Verifies standard MCP initialize handshake."""
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-agent", "version": "1.0"},
        },
    }
    resp = mcp_server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    result = resp["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert result["serverInfo"]["name"] == "pms-mcp-server"
    assert "tools" in result["capabilities"]
    assert "resources" in result["capabilities"]
    assert "prompts" in result["capabilities"]


def test_mcp_tools_list():
    """Verifies MCP tools/list returns all registered PMS tools."""
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    resp = mcp_server.handle_request(req)
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "predict_equipment_risk" in tool_names
    assert "predict_and_narrate" in tool_names
    assert "simulate_derate_intervention" in tool_names
    assert "dispatch_work_order" in tool_names
    assert "get_drift_telemetry" in tool_names
    assert "run_inference_benchmark" in tool_names


def test_mcp_tools_call_predict():
    """Verifies MCP tools/call for predict_equipment_risk."""
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "predict_equipment_risk",
            "arguments": SAMPLE_TELEMETRY,
        },
    }
    resp = mcp_server.handle_request(req)
    assert "result" in resp
    content = resp["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    payload = json.loads(content[0]["text"])
    assert "probability" in payload
    assert "failure_risk" in payload


def test_mcp_tools_call_derate():
    """Verifies MCP tools/call for simulate_derate_intervention."""
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "simulate_derate_intervention",
            "arguments": {
                **SAMPLE_TELEMETRY,
                "derate_rpm_pct": -15.0,
                "derate_pressure_pct": -10.0,
            },
        },
    }
    resp = mcp_server.handle_request(req)
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert "baseline_probability" in payload
    assert "simulated_probability" in payload
    assert "rul_extension_hours" in payload


def test_mcp_resources_list_and_read():
    """Verifies MCP resources/list and resources/read."""
    list_req = {"jsonrpc": "2.0", "id": 5, "method": "resources/list", "params": {}}
    list_resp = mcp_server.handle_request(list_req)
    resources = list_resp["result"]["resources"]
    uris = [r["uri"] for r in resources]
    assert "pms://system/health" in uris
    assert "pms://models/manifest" in uris

    # Read resource
    read_req = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "resources/read",
        "params": {"uri": "pms://system/health"},
    }
    read_resp = mcp_server.handle_request(read_req)
    assert "contents" in read_resp["result"]
    health_data = json.loads(read_resp["result"]["contents"][0]["text"])
    assert health_data["status"] == "healthy"
    assert health_data["model_loaded"] is True


def test_mcp_prompts_list_and_get():
    """Verifies MCP prompts/list and prompts/get."""
    list_req = {"jsonrpc": "2.0", "id": 7, "method": "prompts/list", "params": {}}
    list_resp = mcp_server.handle_request(list_req)
    prompts = list_resp["result"]["prompts"]
    prompt_names = [p["name"] for p in prompts]
    assert "diagnose_machine_anomaly" in prompt_names
    assert "shift_handover_report" in prompt_names

    # Get prompt
    get_req = {
        "jsonrpc": "2.0",
        "id": 8,
        "method": "prompts/get",
        "params": {
            "name": "diagnose_machine_anomaly",
            "arguments": {"machine_id": "CNC-MILL-99", "observed_symptoms": "High whining noise"},
        },
    }
    get_resp = mcp_server.handle_request(get_req)
    messages = get_resp["result"]["messages"]
    assert len(messages) >= 1
    assert "CNC-MILL-99" in messages[0]["content"]["text"]
    assert "High whining noise" in messages[0]["content"]["text"]


def test_fastapi_mcp_endpoint():
    """Verifies FastAPI /mcp POST endpoint handles JSON-RPC 2.0 calls."""
    req_body = {
        "jsonrpc": "2.0",
        "id": 100,
        "method": "tools/list",
        "params": {},
    }
    response = client.post("/mcp", json=req_body)
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 100
    assert "tools" in data["result"]

