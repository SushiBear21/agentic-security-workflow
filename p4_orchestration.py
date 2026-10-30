import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest
import uuid

from p4_baseline import DOCUMENT, draft_review, grade

MAX_STEPS = 3
ALLOWED_TOOL = "retrieve_context"


def run_workflow(request):
    trace = []
    calls = 0

    def stop(status):
        return {
            "status": status,
            "action": "none",
            "applicability": "unknown",
            "facts": {},
            "citations": [],
            "summary": "No review proposal generated.",
            "tool_calls": calls,
            "trace": list(trace),
        }

    asset_id = request.get("asset_id")
    audience = request.get("audience")
    plan = request.get("plan", [ALLOWED_TOOL])

    if (
        not isinstance(asset_id, str)
        or not asset_id.strip()
        or audience not in ("employees", "soc_analysts")
        or not isinstance(plan, list)
        or not plan
    ):
        trace.append("request_rejected")
        return stop("invalid_request")

    trace.append("request_validated")

    # Authorize every operation before dispatching the first one.
    if any(tool != ALLOWED_TOOL for tool in plan):
        trace.append("tool_plan_denied")
        return stop("unauthorized_action")

    if len(plan) > MAX_STEPS:
        trace.append("step_limit_exceeded")
        return stop("step_limit")

    trace.append("tool_plan_authorized")
    documents = []

    for step, tool in enumerate(plan, start=1):
        calls += 1
        trace.append(f"tool_started:{step}:{tool}")

        try:
            # Synthetic retrieval fixture: no API or model call.
            if request.get("simulate_failure"):
                raise TimeoutError("Synthetic retrieval failure")

            documents = copy.deepcopy(
                request.get("documents", [])
            )

        except TimeoutError:
            trace.append("retrieval_failed")
            return stop("tool_unavailable")

        trace.append(f"tool_completed:{step}")

    response = draft_review({
        "asset_id": asset_id,
        "documents": documents,
    })

    trace.append("review_completed")
    response["tool_calls"] = calls
    response["trace"] = list(trace)
    return response


def request_fixture(**changes):
    request = {
        "asset_id": "SYN-WEB-001",
        "audience": "employees",
        "plan": [ALLOWED_TOOL],
        "documents": [copy.deepcopy(DOCUMENT)],
    }

    request.update(changes)
    return request


def expected_result(status, calls):
    answered = status == "answered"

    return {
        "status": status,
        "action": "propose_review" if answered else "none",
        "applicability": "needs_review" if answered else "unknown",
        "facts": copy.deepcopy(DOCUMENT["facts"]) if answered else {},
        "citations": ["EV-001"] if answered else [],
        "tool_calls": calls,
    }


def scenarios():
    return [
        (
            "authorized-two-step",
            request_fixture(plan=[ALLOWED_TOOL, ALLOWED_TOOL]),
            expected_result("answered", 2),
        ),
        (
            "missing-evidence",
            request_fixture(documents=[]),
            expected_result("insufficient_evidence", 1),
        ),
        (
            "unauthorized-tool",
            request_fixture(plan=["create_ticket"]),
            expected_result("unauthorized_action", 0),
        ),
        (
            "mixed-unauthorized-plan",
            request_fixture(plan=[ALLOWED_TOOL, "quarantine"]),
            expected_result("unauthorized_action", 0),
        ),
        (
            "step-budget",
            request_fixture(plan=[ALLOWED_TOOL] * 4),
            expected_result("step_limit", 0),
        ),
        (
            "invalid-audience",
            request_fixture(audience="administrator"),
            expected_result("invalid_request", 0),
        ),
        (
            "retrieval-failure",
            request_fixture(simulate_failure=True),
            expected_result("tool_unavailable", 1),
        ),
    ]


class OrchestrationTests(unittest.TestCase):
    def test_authorized_workflow_stays_within_budget(self):
        result = run_workflow(
            request_fixture(plan=[ALLOWED_TOOL] * 3)
        )

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["tool_calls"], MAX_STEPS)
        self.assertEqual(
            result["trace"][-1],
            "review_completed",
        )

        self.assertLess(
            result["trace"].index("tool_plan_authorized"),
            result["trace"].index(
                "tool_started:1:retrieve_context"
            ),
        )

    def test_unauthorized_tool_never_dispatches(self):
        result = run_workflow(
            request_fixture(plan=["create_ticket"])
        )

        self.assertEqual(
            result["status"],
            "unauthorized_action",
        )
        self.assertEqual(result["tool_calls"], 0)

    def test_mixed_plan_is_rejected_before_first_tool(self):
        result = run_workflow(
            request_fixture(
                plan=[ALLOWED_TOOL, "quarantine"]
            )
        )

        self.assertEqual(
            result["status"],
            "unauthorized_action",
        )
        self.assertEqual(result["tool_calls"], 0)

        self.assertFalse(
            any(
                event.startswith("tool_started:")
                for event in result["trace"]
            )
        )

    def test_excessive_plan_never_dispatches(self):
        result = run_workflow(
            request_fixture(plan=[ALLOWED_TOOL] * 4)
        )

        self.assertEqual(result["status"], "step_limit")
        self.assertEqual(result["tool_calls"], 0)

    def test_invalid_request_never_dispatches(self):
        for changes in (
            {"audience": "administrator"},
            {"plan": []},
        ):
            result = run_workflow(
                request_fixture(**changes)
            )

            self.assertEqual(
                result["status"],
                "invalid_request",
            )
            self.assertEqual(result["tool_calls"], 0)

    def test_retrieval_failure_stops_the_workflow(self):
        result = run_workflow(
            request_fixture(
                plan=[ALLOWED_TOOL] * 3,
                simulate_failure=True,
            )
        )

        self.assertEqual(
            result["status"],
            "tool_unavailable",
        )
        self.assertEqual(result["tool_calls"], 1)
        self.assertNotIn(
            "review_completed",
            result["trace"],
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            OrchestrationTests
        )

        result = unittest.TextTestRunner(
            verbosity=2
        ).run(suite)

        return 0 if result.wasSuccessful() else 1

    rows = []

    for name, request, expected in scenarios():
        response = run_workflow(request)
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
        / "p4-lesson2"
        / uuid.uuid4().hex
    )

    folder.mkdir(parents=True)
    path = folder / "evaluation.json"

    path.write_text(
        json.dumps(
            {
                "mode": "offline_simulation",
                "model_calls": 0,
                "max_steps": MAX_STEPS,
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