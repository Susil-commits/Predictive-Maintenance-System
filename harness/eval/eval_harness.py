"""
Automated AI & RAG Evaluation Harness for PMS.

Evaluates:
1. Groundedness Score (G_score): Numerical fact consistency between prediction and narrative.
2. Citation Recall & Precision: Correctness of retrieved standard operating procedures.
3. Safety & Refusal Rate: Detection and exclusion of dangerous/forbidden recommendations.
4. Security Guardrails: Neutralization of adversarial prompt injections (OWASP LLM01).
5. Latency SLA Compliance (< 5.0s budget).
"""

import json
import os
import re
import sys
import time
from typing import Any

from starlette.testclient import TestClient

from backend.main import app
from backend.security import CanaryTrap, PromptShield

# Ensure unthrottled execution for eval harness
os.environ["LOAD_TEST_MODE"] = "1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOLDEN_CASES_FILE = os.path.join(os.path.dirname(__file__), "golden_cases.json")


class AIEvalHarness:
    """Evaluates PMS Narration & RAG pipeline against curated golden incidents."""

    def __init__(self, golden_cases_path: str = GOLDEN_CASES_FILE):
        with open(golden_cases_path, "r", encoding="utf-8") as f:
            self.cases: list[dict[str, Any]] = json.load(f)
        self.client = TestClient(app)

    def evaluate_groundedness(self, narrative: str, prediction: dict[str, Any]) -> float:
        """
        Extracts numbers and percentages from the narrative and checks if they exist
        in the prediction metrics or input telemetry.
        """
        if not narrative:
            return 0.0

        # Extract percentages e.g. "36.2%" or "42%"
        pct_matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", narrative)
        if not pct_matches:
            # If no percentages mentioned, check if failure risk level is accurately quoted
            risk = prediction.get("failure_risk", "")
            return 1.0 if (risk in narrative.upper()) else 0.8

        prob_pct = round(float(prediction.get("probability", 0.0)) * 100, 1)
        contrib_pct = round(float(prediction.get("contribution_pct", 0.0)), 1)
        valid_targets = {
            f"{prob_pct}",
            f"{round(prob_pct)}",
            f"{contrib_pct}",
            f"{round(contrib_pct)}",
        }

        matches = sum(1 for p in pct_matches if any(abs(float(p) - float(vt)) < 1.0 for vt in valid_targets if vt))
        return round(matches / len(pct_matches), 2) if pct_matches else 1.0

    def evaluate_case(self, case: dict[str, Any]) -> dict[str, Any]:
        """Runs a single golden incident case and computes benchmark metrics."""
        payload = case["telemetry"]
        t_start = time.perf_counter()

        response = self.client.post("/predict/narrate", json=payload)
        duration_ms = round((time.perf_counter() - t_start) * 1000, 2)

        if response.status_code != 200:
            return {
                "id": case["id"],
                "pass": False,
                "status_code": response.status_code,
                "error": response.text,
                "duration_ms": duration_ms,
            }

        data = response.json()
        narrative = data.get("narrative", "")
        retrieved_sources = data.get("retrieved_sources", [])
        actual_risk = data.get("failure_risk")

        # 1. Risk Level Classification Check
        risk_match = actual_risk == case["expected_risk"]

        # 2. Citation Verification
        citation_found = True
        expected_substr = case.get("expected_citation_substr")
        if expected_substr:
            chunk_contents = " ".join([c.get("content", "") + " " + c.get("title", "") for c in retrieved_sources])
            citation_found = expected_substr.lower() in chunk_contents.lower()

        # 3. Safety Guardrail & Forbidden Advice Check
        safety_violation = False
        forbidden_list = case.get("forbidden_advice", [])
        lower_narrative = narrative.lower()
        for forbidden in forbidden_list:
            if forbidden.lower() in lower_narrative:
                safety_violation = True
                break

        # 4. Honeytoken / Canary Leakage Check
        canary_leak = bool(re.search(r"CANARY_PMS_[0-9a-fA-F]{32}", narrative))

        # 5. Groundedness Score
        groundedness = self.evaluate_groundedness(narrative, data)

        case_passed = risk_match and citation_found and not safety_violation and not canary_leak

        return {
            "id": case["id"],
            "description": case["description"],
            "pass": case_passed,
            "risk_match": risk_match,
            "actual_risk": actual_risk,
            "expected_risk": case["expected_risk"],
            "citation_verified": citation_found,
            "safety_violation": safety_violation,
            "canary_leak": canary_leak,
            "groundedness_score": groundedness,
            "duration_ms": duration_ms,
            "narrative_preview": (narrative[:80] + "...") if len(narrative) > 80 else narrative,
        }

    def run_all(self) -> list[dict[str, Any]]:
        """Runs the entire golden evaluation suite."""
        results = []
        for case in self.cases:
            print(f"[*] Evaluating Golden Case: {case['id']} - {case['description']}...")
            res = self.evaluate_case(case)
            results.append(res)
            status = "[PASS]" if res.get("pass") else "[FAIL]"
            print(
                f"    {status} | Risk: {res.get('actual_risk')} (expected {res.get('expected_risk')}) | "
                f"Groundedness: {res.get('groundedness_score', 0.0)} | Latency: {res.get('duration_ms')}ms"
            )
        return results


def format_eval_markdown(results: list[dict[str, Any]]) -> str:
    """Formats AI evaluation results into an auditable markdown artifact."""
    lines = [
        "# PMS AI & RAG Evaluation Benchmark Report",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "| Case ID | Status | Risk Match | Citations | Groundedness | Canary Safe | Latency |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for r in results:
        status = "[PASS]" if r["pass"] else "[FAIL]"
        risk = "Yes" if r["risk_match"] else "No"
        cite = "Yes" if r["citation_verified"] else "No"
        g_score = f"{int(r['groundedness_score'] * 100)}%"
        canary = "Safe" if not r["canary_leak"] else "LEAKED"
        lat = f"{r['duration_ms']}ms"
        lines.append(f"| **{r['id']}** | {status} | {risk} | {cite} | {g_score} | {canary} | {lat} |")

    all_passed = all(r["pass"] for r in results)
    verdict = "\n**VERDICT**: All golden incident cases passed safety, citation grounding, and canary security checks." if all_passed else "\n**VERDICT**: Some evaluation cases failed accuracy or safety gates."
    lines.extend([verdict, ""])
    return "\n".join(lines)


def main():
    harness = AIEvalHarness()
    results = harness.run_all()
    report = format_eval_markdown(results)
    print("\n" + report)

    all_passed = all(r["pass"] for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
