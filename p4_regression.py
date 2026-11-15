"""Versioned regression gate over the existing context/orchestration implementation."""
import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from p4_baseline import grade
from p4_context import run_context, SECRET_CANARY, ATTACK_MARKER

ROOT = Path(__file__).resolve().parent
SOURCES = ("p4_baseline.py", "p4_context.py", "p4_orchestration.py", "p4_reliability.py", "p4_regression.py")
def evaluate(dataset, runner=run_context):
    if dataset.get("schema_version") != 1 or not dataset.get("version") or not dataset.get("cases"):
        raise ValueError("Nonempty versioned dataset required")
    ids = [c["id"] for c in dataset["cases"]]
    if len(ids) != len(set(ids)): raise ValueError("Duplicate case IDs")
    rows = []
    for case in dataset["cases"]:
        started = time.perf_counter()
        response = runner(case["request"])
        latency = (time.perf_counter() - started) * 1000
        failures = grade(response, case["expected"])
        if any(canary in json.dumps(response) for canary in (SECRET_CANARY, ATTACK_MARKER)):
            failures.append("canary_leak")
        trace = response.get("trace")
        if not isinstance(trace, list) or not trace:
            failures.append("missing_trace")
        rows.append({"id": case["id"], "passed": not failures, "failures": failures,
                     "latency_ms": latency, "tool_calls": response.get("tool_calls"),
                     "trace": trace, "retry_delays_seconds": response.get("retry_delays_seconds", [])})
    times = sorted(r["latency_ms"] for r in rows)
    return {"schema_version": 1, "mode": "offline_reference", "dataset_version": dataset["version"],
            "dataset_sha256": hashlib.sha256(json.dumps(dataset, sort_keys=True, allow_nan=False).encode()).hexdigest(),
            "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
            "total": len(rows), "passed": sum(r["passed"] for r in rows),
            "median_ms": statistics.median(times), "p95_ms": times[math.ceil(.95 * len(times)) - 1],
            "model_calls": 0, "model_tokens": None, "model_cost_usd": None,
            "ai_quality_decision": "BLOCKED_PENDING_NEW_HUMAN_EVALUATION",
            "limitations": "Development regression fixtures; offline timing is not model latency. No held-out performance claim.",
            "results": rows}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(ROOT / "tests/fixtures/p4-regression-v1.json"))
    parser.add_argument("--output")
    args = parser.parse_args()
    report = evaluate(json.loads(Path(args.dataset).read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2) + "\n"
    if args.output: Path(args.output).write_text(text, encoding="utf-8")
    else: print(text)
    return 0 if report["passed"] == report["total"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
