"""
PMS Harness CLI & Programmatic Test Orchestrator.

Executes physical telemetry degradation scenarios, evaluates detection latencies,
benchmarks root-cause diagnostics, and produces audit-ready verification reports.
"""

import argparse
import os
import sys
import time
from typing import Any

# Enable unlimited rate for test harness runs
os.environ["LOAD_TEST_MODE"] = "1"

# Ensure stdout handles UTF-8 / Windows console gracefully
if hasattr(sys.stdout, "reconfigure"):
    try:
        getattr(sys.stdout, "reconfigure")(encoding="utf-8", errors="replace")
    except Exception:
        pass

from starlette.testclient import TestClient

from backend.main import app
from harness.scenarios import SCENARIO_REGISTRY, BaseScenario


class HarnessRunner:
    """Orchestrates scenario execution and evaluation against PMS API."""

    def __init__(self, target_url: str | None = None, use_narration: bool = False):
        self.target_url = target_url.rstrip("/") if target_url else None
        self.use_narration = use_narration
        self.endpoint = "/predict/narrate" if use_narration else "/predict"

        if self.target_url:
            import httpx

            self.client: Any = httpx.Client(base_url=self.target_url, timeout=10.0)
            self._is_live = True
        else:
            self.client = TestClient(app)
            self._is_live = False

    def run_scenario(self, scenario: BaseScenario) -> dict[str, Any]:
        """Runs a single scenario end-to-end, streaming telemetry and collecting responses."""
        steps = scenario.generate()
        results = []
        latencies = []

        for step in steps:
            payload = step.to_payload()
            t_start = time.perf_counter()

            if self._is_live:
                resp = self.client.post(self.endpoint, json=payload)
            else:
                resp = self.client.post(self.endpoint, json=payload)

            duration = time.perf_counter() - t_start
            latencies.append(duration)

            if resp.status_code == 200:
                results.append(resp.json())
            else:
                results.append(
                    {
                        "failure_risk": "ERROR",
                        "probability": 0.0,
                        "error": resp.text,
                        "status_code": resp.status_code,
                    }
                )

        eval_summary = scenario.evaluate_run(results, steps)
        eval_summary["mean_latency_ms"] = round((sum(latencies) / len(latencies)) * 1000, 2)
        eval_summary["p95_latency_ms"] = round(sorted(latencies)[int(len(latencies) * 0.95)] * 1000, 2)
        return eval_summary

    def run_suite(self, scenario_names: list[str] | None = None) -> list[dict[str, Any]]:
        """Runs multiple scenarios and returns aggregated evaluations."""
        if not scenario_names or "all" in scenario_names:
            selected_keys = ["thermal_runaway", "overstrain", "tool_wear", "sensor_glitch"]
        else:
            selected_keys = [k for k in scenario_names if k in SCENARIO_REGISTRY]

        summaries = []
        for key in selected_keys:
            scenario_cls = SCENARIO_REGISTRY[key]
            scenario = scenario_cls()
            print(f"[*] Executing Harness Scenario: {scenario.name} ({scenario.total_steps} steps)...")
            summary = self.run_scenario(scenario)
            summaries.append(summary)
            status_symbol = "[PASS]" if summary["pass"] else "[FAIL]"
            print(
                f"    {status_symbol} | Detected: {summary['detected_failures']}/{summary['expected_failures']} | "
                f"First Alert Step: {summary['first_detection_step']} | Latency: {summary['mean_latency_ms']}ms"
            )

        return summaries


def format_markdown_report(summaries: list[dict[str, Any]]) -> str:
    """Formats scenario summaries into a clean Markdown benchmark report."""
    lines = [
        "# PMS Degradation Simulation Harness Report",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "| Scenario | Result | Expected Fails | Detected | First Alert Step | Latency (Mean/P95) | Max Risk Prob |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for s in summaries:
        res = "[PASS]" if s["pass"] else "[FAIL]"
        step = str(s["first_detection_step"]) if s["first_detection_step"] is not None else "N/A"
        lat = f"{s['mean_latency_ms']}ms / {s['p95_latency_ms']}ms"
        max_p = f"{round(s['max_probability'] * 100, 1)}%"
        lines.append(
            f"| **{s['scenario']}** | {res} | {s['expected_failures']} | {s['detected_failures']} | {step} | {lat} | {max_p} |"
        )

    all_passed = all(s["pass"] for s in summaries)
    verdict = (
        "**VERDICT**: All degradation scenarios successfully detected with zero false alarms."
        if all_passed
        else "**VERDICT**: Some failure scenarios degraded or failed detection gates."
    )
    lines.extend(["", verdict, ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="PMS Scenario Simulation Harness")
    parser.add_argument(
        "--scenario",
        nargs="+",
        default=["all"],
        help="Scenarios to run: thermal_runaway, overstrain, tool_wear, sensor_glitch, or all",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default=None,
        help="Optional live URL target (e.g., http://localhost:8000). Defaults to in-process.",
    )
    parser.add_argument(
        "--narrate",
        action="store_true",
        help="Target /predict/narrate instead of /predict",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Path to save markdown report",
    )
    args = parser.parse_args()

    runner = HarnessRunner(target_url=args.endpoint, use_narration=args.narrate)
    summaries = runner.run_suite(args.scenario)

    report_md = format_markdown_report(summaries)
    print("\n" + report_md)

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[+] Saved report to {args.report}")

    all_pass = all(s["pass"] for s in summaries)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
