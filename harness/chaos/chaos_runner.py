"""
PMS Chaos & Resilience Harness Runner.

Orchestrates automated fault injection across database failovers,
third-party AI circuit breaker trips, and network latency anomalies.
"""

import os
import sys
import time
from typing import Any

from harness.chaos.circuit_breaker_chaos import run_circuit_breaker_chaos_experiment
from harness.chaos.db_resilience_chaos import run_database_resilience_experiment

# Ensure unthrottled execution for chaos runs
os.environ["LOAD_TEST_MODE"] = "1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class ChaosHarnessRunner:
    """Executes structured fault-injection experiments and benchmarks resilience."""

    def run_all(self) -> list[dict[str, Any]]:
        experiments = [
            ("AI Circuit Breaker Outage", run_circuit_breaker_chaos_experiment),
            ("Database Outage Ingestion Resilience", run_database_resilience_experiment),
        ]

        results = []
        for name, fn in experiments:
            print(f"[*] Running Chaos Experiment: {name}...")
            t_start = time.perf_counter()
            res = fn()
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            res["duration_ms"] = duration_ms
            results.append(res)
            status = "[PASS]" if res.get("pass") else "[FAIL]"
            print(f"    {status} | Experiment: {name} | Duration: {duration_ms}ms")

        return results


def format_chaos_markdown(results: list[dict[str, Any]]) -> str:
    """Formats chaos results into an auditable markdown artifact."""
    lines = [
        "# PMS Chaos & Resilience Fault-Injection Report",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "| Experiment | Status | Verification Criteria | Latency / Recovery |",
        "| :--- | :---: | :---: | :---: |",
    ]

    for r in results:
        status = "[PASS]" if r["pass"] else "[FAIL]"
        name = r["experiment"]
        dur = f"{r['duration_ms']}ms"
        if "fast_rejection_latency_us" in r:
            criteria = f"FSM Transition (CLOSED -> OPEN -> HALF_OPEN -> CLOSED); Rejection: {r['fast_rejection_latency_us']}µs"
        else:
            criteria = f"Zero 500 crashes during DB loss (Status: {r['phase_2_chaos_resilience_status']})"
        lines.append(f"| **{name}** | {status} | {criteria} | {dur} |")

    all_passed = all(r["pass"] for r in results)
    verdict = "\n**VERDICT**: System survived all injected infrastructure faults with zero request drops or crashes." if all_passed else "\n**VERDICT**: Chaos injection caused system failures."
    lines.extend([verdict, ""])
    return "\n".join(lines)


def main():
    runner = ChaosHarnessRunner()
    results = runner.run_all()
    report = format_chaos_markdown(results)
    print("\n" + report)

    all_passed = all(r["pass"] for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

