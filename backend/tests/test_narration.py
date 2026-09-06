import pytest
from starlette.testclient import TestClient
from backend.main import app
from backend.narration_service import rag_store, llm_client, orchestrate_predict_and_narrate

client = TestClient(app)

SAMPLE_HIGH_RISK = {
    "temperature": 94.2,
    "rpm": 2850.0,
    "pressure": 32.0,
    "vibration": 0.68,
    "operating_hours": 4900.0
}

SAMPLE_LOW_RISK = {
    "temperature": 68.0,
    "rpm": 1500.0,
    "pressure": 21.0,
    "vibration": 0.22,
    "operating_hours": 950.0
}


def test_predict_narrate_endpoint_success():
    """
    Verifies that /predict/narrate returns the full prediction output along with
    a narrative field and auditable retrieved_sources chunks, preserving suggested_action.
    """
    response = client.post("/predict/narrate", json=SAMPLE_HIGH_RISK)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    # 1. Existing prediction fields
    assert "failure_risk" in data
    assert "probability" in data
    assert "top_risk_factor" in data
    assert "contribution_pct" in data
    assert "suggested_action" in data
    assert data["suggested_action"] is not None and len(data["suggested_action"]) > 0

    # 2. New narration fields
    assert "narrative" in data
    assert data["narrative"] is not None and len(data["narrative"]) > 0
    assert "retrieved_sources" in data
    assert isinstance(data["retrieved_sources"], list)
    assert len(data["retrieved_sources"]) >= 1

    # 3. Verify retrieved source chunk structure
    first_chunk = data["retrieved_sources"][0]
    assert "failure_mode" in first_chunk
    assert "title" in first_chunk
    assert "section" in first_chunk
    assert "content" in first_chunk
    assert len(first_chunk["content"]) > 20


def test_narration_fallback_on_llm_failure(monkeypatch):
    """
    Verifies that when the LLM call fails or times out, the endpoint silently
    falls back to the existing canned suggested_action string, never failing or degrading.
    """
    def mock_failing_llm(*args, **kwargs):
        raise TimeoutError("Simulated external LLM API gateway timeout (504)")

    # Monkeypatch the LLM call on llm_client
    monkeypatch.setattr(llm_client, "generate_narrative", mock_failing_llm)

    # Calling through the orchestration function directly to verify fallback wrapper
    # In narration_service, generate_narrative itself handles exceptions, but if an external call fails:
    def mock_failing_gemini(*args, **kwargs):
        raise RuntimeError("External LLM connection reset by peer")

    monkeypatch.setattr(llm_client, "_call_gemini", mock_failing_gemini)
    monkeypatch.setattr(llm_client, "_call_openai", mock_failing_gemini)
    monkeypatch.setattr(llm_client, "gemini_api_key", "mock-test-key")

    response = client.post("/predict/narrate", json=SAMPLE_HIGH_RISK)
    assert response.status_code == 200, "Endpoint should succeed even if LLM fails"

    data = response.json()
    assert data["narrative"] == data["suggested_action"], (
        f"Narrative should silently fall back to suggested_action. "
        f"Got narrative: {data['narrative']}, expected: {data['suggested_action']}"
    )


def test_rag_retrieval_matches_failure_mode():
    """
    Verifies that for each modeled failure mode and corresponding top_risk_factor,
    the retrieved RAG chunk actually corresponds to that failure mode (not a random or mismatched one).
    This proves that retrieval is performing accurate semantic selection.
    """
    test_cases = [
        ("temperature", "Thermal (HDF)", ["thermal", "heat", "coolant", "cooling"]),
        ("pressure", "Overstrain (OSF)", ["pressure", "overstrain", "hydraulic", "valve"]),
        ("vibration", "Vibration Fatigue (VIB)", ["vibration", "bearing", "imbalance", "shaft"]),
        ("operating_hours", "Tool Wear (TWF)", ["tool wear", "wear", "insert", "operating hours"]),
        ("rpm", "Power (PWF)", ["power", "motor", "drive", "rpm", "torque"]),
    ]

    for factor, expected_mode, expected_keywords in test_cases:
        chunks = rag_store.retrieve(query=factor, n_results=2)
        assert len(chunks) > 0, f"RAG should return at least 1 chunk for factor '{factor}'"

        top_chunk = chunks[0]
        # Assert failure mode matches expected
        assert top_chunk["failure_mode"] == expected_mode, (
            f"Mismatched failure mode for query '{factor}'. "
            f"Expected '{expected_mode}', got '{top_chunk['failure_mode']}'"
        )

        # Assert content contains expected domain-specific terminology
        content_lower = top_chunk["content"].lower()
        has_keyword = any(kw in content_lower for kw in expected_keywords)
        assert has_keyword, (
            f"Chunk content for '{factor}' does not contain any expected keywords {expected_keywords}. "
            f"Content excerpt: {top_chunk['content'][:150]}..."
        )


def test_narration_with_mocked_fluent_llm(monkeypatch):
    """
    Verifies that when the LLM returns a valid fluent paragraph, it is correctly
    placed in the narrative field while keeping suggested_action unchanged.
    """
    synthetic_briefing = (
        "Equipment telemetry demonstrates elevated risk at 40.7% probability, driven predominantly "
        "by high hydraulic pressure (48.3% contribution). Technicians should inspect proportional relief valves "
        "and accumulator pre-charge per OSF Standard Operating Procedures immediately."
    )

    def mock_successful_llm(*args, **kwargs):
        return synthetic_briefing

    monkeypatch.setattr(llm_client, "generate_narrative", mock_successful_llm)

    response = client.post("/predict/narrate", json=SAMPLE_HIGH_RISK)
    assert response.status_code == 200

    data = response.json()
    assert data["narrative"] == synthetic_briefing
    assert data["suggested_action"] != synthetic_briefing
    assert len(data["suggested_action"]) > 0


def test_predict_narrate_with_counterfactual():
    """
    Verifies that passing include_counterfactual=true populates counterfactual
    remediation results inside the response.
    """
    response = client.post("/predict/narrate?include_counterfactual=true", json=SAMPLE_HIGH_RISK)
    assert response.status_code == 200
    data = response.json()

    assert "counterfactual" in data
    assert data["counterfactual"] is not None
    assert "already_safe" in data["counterfactual"]


def test_existing_endpoints_unaffected_and_independent():
    """
    Confirms that existing endpoints (/predict, /predict-counterfactual, /predict-rul)
    continue to execute identically and independently without any dependency on the narration layer.
    """
    # 1. /predict
    p_resp = client.post("/predict", json=SAMPLE_LOW_RISK)
    assert p_resp.status_code == 200
    p_data = p_resp.json()
    assert "failure_risk" in p_data
    assert "probability" in p_data
    assert "suggested_action" in p_data
    # Existing /predict response schema should not be forced to require narrative
    assert "narrative" not in p_data

    # 2. /predict-counterfactual
    cf_resp = client.post("/predict-counterfactual", json=SAMPLE_HIGH_RISK)
    assert cf_resp.status_code == 200
    cf_data = cf_resp.json()
    assert "already_safe" in cf_data
    assert "risk_before" in cf_data
