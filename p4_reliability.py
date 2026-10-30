import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest
import uuid

from p4_baseline import DOCUMENT, draft_review, grade
from p4_orchestration import ALLOWED_TOOL, MAX_STEPS

MAX_ATTEMPTS = 3


class SyntheticRetriever:
    def __init__(self, documents, outcomes=None):
        self.documents = documents
        self.outcomes = outcomes or ["ok"]
        self.calls = 0

    def retrieve(self):
        self.calls += 1

        outcome = self.outcomes[
            min(self.calls - 1, len(self.outcomes) - 1)
        ]

        if outcome == "timeout":
            raise TimeoutError("Synthetic timeout")

        if outcome == "temporary":
            raise ConnectionError("Synthetic temporary failure")

        if outcome == "permanent":
            raise PermissionError("Synthetic permanent failure")

        if outcome == "malformed":
            return {"wrong": "shape"}

        if outcome != "ok":
            raise ValueError("Unknown fixture outcome")

        return copy.deepcopy(self.documents)


def valid_documents(documents):
    if not isinstance(documents, list):
        return False

    for document in documents:
        if not isinstance(document, dict):
            return False

        if (
            not isinstance(document.get("id"), str)
            or not document["id"]
        ):
            return False

        facts = document.get("facts")

        if not isinstance(facts, dict):
            return False

        if set(facts) != {
            "asset_id",
            "internet_exposed",
            "business_criticality",
        }:
            return False

        if (
            not isinstance(facts["asset_id"], str)
            or not facts["asset_id"]
        ):
            return False

        if type(facts["internet_exposed"]) is not bool:
            return False

        if facts["business_criticality"] not in (
            "low", "medium", "high"
        ):
            return False

    return True


def run_reliable(request):
    trace = []
    delays = []

    tool = SyntheticRetriever(
        request.get("documents", []),
        request.get("outcomes"),
    )

    def stop(status):
        return {
            "status": status,
            "action": "none",
            "applicability": "unknown",
            "facts": {},
            "citations": [],
            "summary": "No review proposal generated.",
            "tool_calls": tool.calls,
            "trace": list(trace),
            "retry_delays_seconds": list(delays),
        }

    asset = request.get("asset_id")
    plan = request.get("plan", [ALLOWED_TOOL])

    if (
        not isinstance(asset, str)
        or not asset.strip()
        or request.get("audience") not in (
            "employees", "soc_analysts"
        )
        or not isinstance(plan, list)
        or not plan
    ):
        trace.append("request_rejected")
        return stop("invalid_request")

    trace.append("request_validated")

    if any(name != ALLOWED_TOOL for name in plan):
        trace.append("tool_plan_denied")
        return stop("unauthorized_action")

    if len(plan) > MAX_STEPS:
        trace.append("step_limit_exceeded")
        return stop("step_limit")

    trace.append("tool_plan_authorized")
    documents = []

    for step in range(1, len(plan) + 1):
        while True:
            if tool.calls >= MAX_ATTEMPTS:
                trace.append("global_attempt_budget_exhausted")
                return stop("step_limit")

            trace.append(
                f"attempt_started:{tool.calls + 1}:step:{step}"
            )

            try:
                documents = tool.retrieve()

            except (TimeoutError, ConnectionError):
                trace.append("temporary_failure")

                if tool.calls >= MAX_ATTEMPTS:
                    trace.append("retries_exhausted")
                    return stop("tool_unavailable")

                delay = round(
                    0.1 * (2 ** (tool.calls - 1)), 3
                )

                delays.append(delay)
                trace.append(f"retry_scheduled:{delay}")

                # Record intended delay without actually sleeping.
                continue

            except PermissionError:
                trace.append("permanent_failure_no_retry")
                return stop("tool_unavailable")

            if not valid_documents(documents):
                trace.append("malformed_response_no_retry")
                return stop("tool_unavailable")

            trace.append("retrieval_succeeded")
            break

    response = draft_review({
        "asset_id": asset,
        "documents": documents,
    })

    trace.append("review_completed")

    response.update(
        tool_calls=tool.calls,
        trace=list(trace),
        retry_delays_seconds=list(delays),
    )

    return response


class SyntheticReviewStore:
    """In-memory fixture only: no real ticket creation."""

    def __init__(self):
        self.records = {}
        self.writes = 0

    def create(self, key, payload):
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        digest = hashlib.sha256(
            encoded.encode("utf-8")
        ).hexdigest()

        if key in self.records:
            record = self.records[key]

            if record["payload_sha256"] != digest:
                raise ValueError(
                    "Same key used with a changed payload"
                )

            return {
                "status": "already_created",
                "ticket_id": record["ticket_id"],
            }

        ticket_id = "SYNTHETIC-" + uuid.uuid4().hex[:12]

        self.records[key] = {
            "payload_sha256": digest,
            "ticket_id": ticket_id,
        }

        self.writes += 1

        return {
            "status": "created",
            "ticket_id": ticket_id,
        }


def fixture(**changes):
    request = {
        "asset_id": "SYN-WEB-001",
        "audience": "employees",
        "plan": [ALLOWED_TOOL],
        "documents": [copy.deepcopy(DOCUMENT)],
        "outcomes": ["ok"],
    }

    request.update(changes)
    return request


def cases():
    return [
        (
            "clean-retrieval",
            fixture(),
            "answered",
            1,
        ),
        (
            "timeout-then-recovery",
            fixture(outcomes=["timeout", "ok"]),
            "answered",
            2,
        ),
        (
            "temporary-retry-exhaustion",
            fixture(outcomes=["temporary"]),
            "tool_unavailable",
            3,
        ),
        (
            "permanent-no-retry",
            fixture(outcomes=["permanent"]),
            "tool_unavailable",
            1,
        ),
        (
            "malformed-no-retry",
            fixture(outcomes=["malformed"]),
            "tool_unavailable",
            1,
        ),
        (
            "missing-evidence",
            fixture(documents=[]),
            "insufficient_evidence",
            1,
        ),
        (
            "unauthorized-no-dispatch",
            fixture(plan=["create_ticket"]),
            "unauthorized_action",
            0,
        ),
        (
            "shared-attempt-budget",
            fixture(
                plan=[ALLOWED_TOOL] * 3,
                outcomes=["timeout", "ok", "ok"],
            ),
            "step_limit",
            3,
        ),
    ]


class ReliabilityTests(unittest.TestCase):
    def test_timeout_recovers(self):
        result = run_reliable(
            fixture(outcomes=["timeout", "ok"])
        )

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["tool_calls"], 2)

    def test_temporary_failure_stops_after_three_attempts(self):
        result = run_reliable(
            fixture(outcomes=["temporary"])
        )

        self.assertEqual(
            result["status"], "tool_unavailable"
        )
        self.assertEqual(result["tool_calls"], 3)

    def test_permanent_failure_is_not_retried(self):
        result = run_reliable(
            fixture(outcomes=["permanent", "ok"])
        )

        self.assertEqual(
            result["status"], "tool_unavailable"
        )
        self.assertEqual(result["tool_calls"], 1)

    def test_malformed_response_is_not_retried(self):
        result = run_reliable(
            fixture(outcomes=["malformed", "ok"])
        )

        self.assertEqual(
            result["status"], "tool_unavailable"
        )
        self.assertEqual(result["tool_calls"], 1)

    def test_budget_is_shared_across_steps(self):
        result = run_reliable(
            fixture(
                plan=[ALLOWED_TOOL] * 3,
                outcomes=["timeout", "ok", "ok"],
            )
        )

        self.assertEqual(result["status"], "step_limit")
        self.assertEqual(result["tool_calls"], 3)
        self.assertNotIn(
            "review_completed", result["trace"]
        )

    def test_unauthorized_plan_has_zero_attempts(self):
        result = run_reliable(
            fixture(
                plan=[ALLOWED_TOOL, "quarantine"]
            )
        )

        self.assertEqual(
            result["status"], "unauthorized_action"
        )
        self.assertEqual(result["tool_calls"], 0)

    def test_backoff_schedule_is_bounded(self):
        result = run_reliable(
            fixture(outcomes=["timeout"])
        )

        self.assertEqual(
            result["retry_delays_seconds"],
            [0.1, 0.2],
        )

    def test_duplicate_key_and_payload_create_one_record(self):
        store = SyntheticReviewStore()
        payload = {"asset_id": "SYN-WEB-001"}

        first = store.create("review-001", payload)
        second = store.create("review-001", payload)

        self.assertEqual(
            first["ticket_id"], second["ticket_id"]
        )
        self.assertEqual(
            second["status"], "already_created"
        )
        self.assertEqual(store.writes, 1)

    def test_changed_payload_cannot_reuse_key(self):
        store = SyntheticReviewStore()

        store.create(
            "review-001",
            {"asset_id": "SYN-WEB-001"},
        )

        with self.assertRaises(ValueError):
            store.create(
                "review-001",
                {"asset_id": "SYN-OTHER-002"},
            )

        self.assertEqual(store.writes, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            ReliabilityTests
        )

        result = unittest.TextTestRunner(
            verbosity=2
        ).run(suite)

        return 0 if result.wasSuccessful() else 1

    rows = []

    for name, request, status, calls in cases():
        answered = status == "answered"

        expected = {
            "status": status,
            "tool_calls": calls,
            "action": "propose_review" if answered else "none",
            "applicability": "needs_review" if answered else "unknown",
            "facts": copy.deepcopy(DOCUMENT["facts"]) if answered else {},
            "citations": ["EV-001"] if answered else [],
        }

        response = run_reliable(request)
        failures = grade(response, expected)

        rows.append({
            "case_id": name,
            "passed": not failures,
            "failures": failures,
            "response": response,
        })

        label = "FAIL" if failures else "PASS"

        print(
            f"{label}: {name} "
            f"| calls={response['tool_calls']}"
        )

    passed = sum(row["passed"] for row in rows)

    folder = (
        Path(__file__).resolve().parent
        / "reports"
        / "p4-lesson3"
        / uuid.uuid4().hex
    )

    folder.mkdir(parents=True)
    path = folder / "evaluation.json"

    path.write_text(
        json.dumps(
            {
                "mode": "offline_simulation",
                "model_calls": 0,
                "max_attempts": MAX_ATTEMPTS,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "passed": passed,
                "total": len(rows),
                "results": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Result: {passed}/{len(rows)} passed")
    print(f"Report: {path}")

    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())