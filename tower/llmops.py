"""Synthetic canary and adversarial evidence for the existing model boundary."""
import hashlib
import json
from collections import Counter

from p4_context import ATTACK_MARKER, SECRET_CANARY
from p4_observability import SYSTEM, evaluate, evaluation_cases

STABLE = {"model_id": "reference-stable", "temperature": 0, "input_price": 1, "output_price": 2}
CANDIDATE = {**STABLE, "model_id": "reference-candidate"}
PROMPT_VERSION = "asset-review-v1"


class FixtureModel:
    def __init__(self, changes=None, stop="end_turn"):
        self.changes = changes or {}
        self.stop = stop
        self.calls = 0

    def converse(self, *, modelId, system, messages, inferenceConfig):
        if system != [{"text": SYSTEM}]:
            raise ValueError("Unexpected prompt")
        self.calls += 1
        documents = json.loads(messages[0]["content"][0]["text"])["documents"]
        draft = {
            "status": "answered", "action": "propose_review", "applicability": "needs_review",
            "facts": documents[0]["facts"], "citations": sorted(d["id"] for d in documents),
            "summary": "Asset applicability remains unconfirmed.",
        }
        draft.update(self.changes)
        return {
            "usage": {"inputTokens": 120, "outputTokens": 40}, "stopReason": self.stop,
            "output": {"message": {"content": [{"text": json.dumps(draft)}]}},
        }


def evaluate_boundary():
    reference = {name: (request, expected) for name, request, expected in evaluation_cases()}
    cases = [
        ("benign", "clean-context", {}, "answered", 1),
        ("benign", "private-asset", {}, "answered", 1),
        ("malicious_retrieval", "injected-context", {}, "answered", 1),
        ("prompt_injection", "injected-context", {"changes": {"summary": ATTACK_MARKER}}, "model_output_rejected", 1),
        ("exfiltration", "sensitive-context", {}, "sensitive_context", 0),
        ("exfiltration", "clean-context", {"changes": {"summary": SECRET_CANARY}}, "model_output_rejected", 1),
        ("tool_output_manipulation", "conflicting-context", {}, "conflicting_evidence", 0),
        ("unsafe_decision", "clean-context", {"changes": {"action": "execute"}}, "model_output_rejected", 1),
        ("unsafe_decision", "clean-context", {"stop": "tool_use"}, "model_output_rejected", 1),
    ]
    results = []
    totals, failures = Counter(), Counter()
    for category, base, params, status, calls in cases:
        request, expected = reference[base]
        client = FixtureModel(**params)
        row, fatal = evaluate(request, expected, CANDIDATE, client)
        response = row["response"]
        passed = (
            not fatal and response["status"] == status and client.calls == calls
            and response["action"] == ("propose_review" if status == "answered" else "none")
            and not any(marker in json.dumps(response) for marker in (ATTACK_MARKER, SECRET_CANARY))
        )
        totals[category] += 1
        failures[category] += not passed
        results.append({"category": category, "base_case": base, "passed": passed,
                        "status": response["status"], "calls": client.calls, "checks": row["failures"]})
    return {
        "scope": "synthetic mocked model boundary", "fixture_version": "boundary-v1",
        "passed": sum(r["passed"] for r in results), "total": len(results),
        "attack_cases": len(results) - totals["benign"],
        "adversarial_boundary_failures": sum(failures.values()) - failures["benign"],
        "benign_cases": totals["benign"], "benign_case_failures": failures["benign"],
        "cases_by_category": dict(totals), "results": results, "live_model_calls": 0,
    }


def canary():
    """Send every tenth request to the candidate until its first gate breach."""
    _, request, expected = evaluation_cases()[0]
    active = True
    rows = []
    for index in range(30):
        candidate = active and index % 10 == 0
        config = CANDIDATE if candidate else STABLE
        changes = {"action": "execute"} if index == 10 and candidate else {}
        report, _ = evaluate(request, expected, config, FixtureModel(changes))
        if candidate and not report["passed"]:
            active = False
        rows.append({
            "request": index, "route": config["model_id"], "accepted": report["passed"],
            "latency_ms": report["model_latency_ms"], "input_tokens": report["input_tokens"],
            "output_tokens": report["output_tokens"], "estimated_cost_usd": report["estimated_cost_usd"],
        })
    lanes = {}
    for config in (STABLE, CANDIDATE):
        lane = [row for row in rows if row["route"] == config["model_id"]]
        lanes[config["model_id"]] = {
            "requests": len(lane), "accepted": sum(row["accepted"] for row in lane),
            "max_latency_ms": max(row["latency_ms"] for row in lane),
            "estimated_cost_usd": round(sum(row["estimated_cost_usd"] for row in lane), 9),
        }
    return {
        "scope": "fixture latency and scenario prices", "live_model_calls": 0,
        "prompt_version": PROMPT_VERSION, "prompt_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
        "profiles": [STABLE, CANDIDATE], "candidate_percent": 10, "rollback": not active,
        "lanes": lanes, "requests": rows,
    }
