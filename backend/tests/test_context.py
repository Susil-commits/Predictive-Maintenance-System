"""
Tests for Context Engineering Layer in PMS.

Validates:
1. Backward compatibility: Standard telemetry payloads without context succeed unchanged.
2. Contextual Telemetry: Payloads with MachineContext, OperationalRegime, and temporal momentum.
3. RAG & Narration Context Grounding: Prompt construction with operational environment and counterfactuals.
"""

from starlette.testclient import TestClient

from backend.main import app
from backend.narration_service import llm_client

client = TestClient(app)

SAMPLE_TELEMETRY = {
    "temperature": 88.5,
    "rpm": 2700.0,
    "pressure": 31.0,
    "vibration": 0.58,
    "operating_hours": 3200.0,
}


def test_prediction_without_context_backward_compatibility():
    """Verifies that legacy uncontextualized payloads return standard schema without breaking."""
    response = client.post("/predict", json=SAMPLE_TELEMETRY)
    assert response.status_code == 200
    data = response.json()
    assert "failure_risk" in data
    assert "probability" in data
    assert data.get("context") is None
    assert data.get("operational_context_summary") is None


def test_prediction_with_operational_context():
    """Verifies that payloads with MachineContext receive synthesized context summary."""
    contextual_payload = {
        **SAMPLE_TELEMETRY,
        "context": {
            "machine_id": "CNC-MILL-ALPHA",
            "machine_type": "Heavy-Duty-5Axis",
            "regime": "steady_state_heavy",
            "ambient_temperature": 24.5,
            "hours_since_last_service": 85.0,
            "recent_fault_count_24h": 2,
        },
        "temp_rate_of_change": 1.45,
        "vibration_crest_factor": 3.2,
    }

    response = client.post("/predict", json=contextual_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["context"] is not None
    assert data["context"]["machine_id"] == "CNC-MILL-ALPHA"
    assert data["context"]["regime"] == "steady_state_heavy"
    assert "operational_context_summary" in data
    summary = data["operational_context_summary"]
    assert "CNC-MILL-ALPHA" in summary
    assert "steady_state_heavy" in summary
    assert "ΔT=" in summary
    assert "dT/dt=+1.45°C/min" in summary
    assert "2 prior alerts" in summary


def test_narrate_with_operational_context():
    """Verifies that /predict/narrate ingests operational context and returns grounding chunks."""
    contextual_payload = {
        **SAMPLE_TELEMETRY,
        "context": {
            "machine_id": "SPINDLE-402",
            "machine_type": "High-Speed",
            "regime": "warmup",
            "ambient_temperature": 22.0,
            "hours_since_last_service": 15.0,
            "recent_fault_count_24h": 0,
        },
        "temp_rate_of_change": 0.5,
    }

    response = client.post("/predict/narrate", json=contextual_payload)
    assert response.status_code == 200
    data = response.json()
    assert "narrative" in data
    assert "retrieved_sources" in data
    assert data["context"]["machine_id"] == "SPINDLE-402"
    assert "operational_context_summary" in data
    assert "SPINDLE-402" in data["operational_context_summary"]


def test_llm_prompt_incorporates_context_envelope():
    """Verifies that llm_client.build_prompt injects the structured OPERATIONAL EQUIPMENT & TEMPORAL CONTEXT block."""
    prediction = {
        "failure_risk": "HIGH",
        "probability": 0.82,
        "top_risk_factor": "temperature",
        "contribution_pct": 52.0,
    }
    chunks = [
        {"title": "HDF Procedure", "section": "Thermal Mitigation", "content": "Inspect secondary heat exchanger."}
    ]
    context = {
        "machine_id": "LATHE-77",
        "machine_type": "Precision",
        "regime": "steady_state_heavy",
        "ambient_temperature": 26.0,
        "hours_since_last_service": 210.0,
        "recent_fault_count_24h": 3,
    }

    prompt = llm_client.build_prompt(
        prediction=prediction,
        retrieved_chunks=chunks,
        counterfactual=None,
        context=context,
        temp_rate_of_change=2.1,
        vibration_crest_factor=4.5,
    )

    assert "OPERATIONAL EQUIPMENT & TEMPORAL CONTEXT:" in prompt
    assert "LATHE-77" in prompt
    assert "steady_state_heavy" in prompt
    assert "Ambient Floor Temperature: 26.0°C" in prompt
    assert "Thermal Gradient (dT/dt): +2.10°C/min" in prompt
    assert "Vibration Crest Factor: 4.50" in prompt
    assert "3 prior alerts" in prompt
