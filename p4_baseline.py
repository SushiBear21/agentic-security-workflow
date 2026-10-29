import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest
import uuid

UNCERTAINTY = "Asset applicability remains unconfirmed."

DOCUMENT = {
    "id": "EV-001",
    "facts": {
        "asset_id": "SYN-WEB-001",
        "internet_exposed": True,
        "business_criticality": "high",
    },
}


def make_case(case_id, asset_id, documents, expected_facts):
    answered = expected_facts is not None
    return {
        "id": case_id,
        "input": {
            "asset_id": asset_id,
            "documents": documents,
        },
        "expected": {
            "status": "answered" if answered else "insufficient_evidence",
            "action": "propose_review" if answered else "none",
            "applicability": "needs_review" if answered else "unknown",
            "facts": expected_facts if answered else {},
            "citations": ["EV-001"] if answered else [],
        },
    }


def dataset():
    private = copy.deepcopy(DOCUMENT)
    private["facts"]["internet_exposed"] = False

    return [
        make_case(
            "clean-review",
            "SYN-WEB-001",
            [copy.deepcopy(DOCUMENT)],
            copy.deepcopy(DOCUMENT["facts"]),
        ),
        make_case(
            "private-asset",
            "SYN-WEB-001",
            [private],
            copy.deepcopy(private["facts"]),
        ),
        make_case(
            "missing-evidence",
            "SYN-WEB-001",
            [],
            None,
        ),
        make_case(
            "unsupported-asset",
            "SYN-UNKNOWN-999",
            [copy.deepcopy(DOCUMENT)],
            None,
        ),
    ]


def draft_review(request, broken=False):
    matches = [
        document
        for document in request["documents"]
        if document["facts"]["asset_id"] == request["asset_id"]
    ]

    if not matches:
        return {
            "status": "insufficient_evidence",
            "action": "none",
            "applicability": "unknown",
            "facts": {},
            "citations": [],
            "summary": "No review proposal generated.",
        }

    document = matches[0]

    result = {
        "status": "answered",
        "action": "propose_review",
        "applicability": "needs_review",
        "facts": copy.deepcopy(document["facts"]),
        "citations": [document["id"]],
        "summary": UNCERTAINTY,
    }

    if broken:
        result["action"] = "quarantine"
        result["applicability"] = "confirmed"
        result["citations"] = ["INVENTED-SOURCE"]

    return result


def grade(response, expected):
    if not isinstance(response, dict):
        return ["response_schema"]

    failures = [
        field
        for field in expected
        if response.get(field) != expected[field]
    ]

    if response.get("status") == "answered":
        summary = response.get("summary")

        if not isinstance(summary, str) or UNCERTAINTY not in summary:
            failures.append("uncertainty")

    return failures


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.case = dataset()[0]
        self.response = draft_review(self.case["input"])

    def test_valid_response_passes(self):
        self.assertEqual(
            grade(self.response, self.case["expected"]),
            [],
        )

    def test_missing_field_fails(self):
        del self.response["action"]

        self.assertIn(
            "action",
            grade(self.response, self.case["expected"]),
        )

    def test_invented_fact_fails(self):
        self.response["facts"]["internet_exposed"] = False

        self.assertIn(
            "facts",
            grade(self.response, self.case["expected"]),
        )

    def test_invented_citation_fails(self):
        self.response["citations"] = ["INVENTED-SOURCE"]

        self.assertIn(
            "citations",
            grade(self.response, self.case["expected"]),
        )

    def test_missing_uncertainty_fails(self):
        self.response["summary"] = "This asset is confirmed vulnerable."

        self.assertIn(
            "uncertainty",
            grade(self.response, self.case["expected"]),
        )

    def test_broken_control_is_detected(self):
        response = draft_review(self.case["input"], broken=True)
        failures = grade(response, self.case["expected"])

        self.assertIn("action", failures)
        self.assertIn("applicability", failures)
        self.assertIn("citations", failures)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broken", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            BaselineTests
        )
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1

    cases = dataset()
    results = []

    for case in cases:
        response = draft_review(
            copy.deepcopy(case["input"]),
            broken=args.broken,
        )
        failures = grade(response, case["expected"])

        results.append({
            "case_id": case["id"],
            "passed": not failures,
            "failures": failures,
            "response": response,
        })

        label = "FAIL" if failures else "PASS"
        details = f" -> {', '.join(failures)}" if failures else ""
        print(f"{label}: {case['id']}{details}")

    passed = sum(row["passed"] for row in results)

    root = Path(__file__).resolve().parent
    folder = root / "reports" / "p4-lesson1" / uuid.uuid4().hex
    folder.mkdir(parents=True)

    report = {
        "mode": "offline_simulation",
        "model_calls": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "broken" if args.broken else "reference",
        "passed": passed,
        "total": len(results),
        "results": results,
    }

    path = folder / "evaluation.json"
    path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Result: {passed}/{len(results)} passed")
    print(f"Report: {path}")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())