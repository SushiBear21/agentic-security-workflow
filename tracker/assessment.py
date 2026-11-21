"""Generate a selected-objective CMMC Level 2 lab assessment using synthetic evidence."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.workflow import digest
from tower.core import verify
from tracker.store import Principal, Tracker

FIXTURE_ID = "4cfe23f3-d300-47d1-bb90-85439c61a239"
CHANGE = "LAB-CHANGE-001"


def approval_check(record, candidate):
    return record.get("approver") == "fixture-release-reviewer" and record.get("candidate_sha256") == candidate


def exercise():
    with TemporaryDirectory() as tmp:
        tracker = Tracker(Path(tmp) / "lab.db", clock=lambda: 1_800_000_000)
        contributor = Principal("Aster", "Casey", "contributor")
        reviewer = Principal("Aster", "Drew", "reviewer")
        other = Principal("Other", "Drew", "reviewer")
        item = tracker.run(contributor, "submit", {
            "id": FIXTURE_ID, "title": "Synthetic CUI training record", "note": "Fictional checklist only"
        })
        review = {"id": item["id"], "sha256": item["sha256"], "decision": "approve",
                  "reason": "Fixture reviewed against the lab checklist"}
        try:
            tracker.run(contributor, "review", review)
        except PermissionError:
            contributor_denied = True
        else:
            contributor_denied = False
        approved = tracker.run(reviewer, "review", review)
        export = tracker.run(reviewer, "export")
        verify({"events": export["events"], "proposals": {}})
        identity_trace = [(entry["kind"], entry["actor"]) for entry in export["events"]]
        access_passed = contributor_denied and not tracker.run(other, "list") and approved["status"] == "approved"
        audit_passed = identity_trace == [("submitted", "Casey"), ("reviewed", "Drew"), ("exported", "Drew")]

    candidate = digest({"id": CHANGE, "scope": "synthetic tracker configuration"})
    baseline = {"id": CHANGE, "candidate_sha256": candidate, "approver": None}
    corrected = {**baseline, "approver": "fixture-release-reviewer"}
    findings = [{
        "id": "F-001", "requirement": "3.4.3", "observation": "Baseline fixture has no approver",
        "baseline": baseline, "baseline_sha256": digest(baseline),
        "baseline_passed": approval_check(baseline, candidate),
        "root_cause": "The fixture change record had no mandatory approval evidence",
        "owner": "fictional change manager",
        "corrective_action": "Require a separate reviewer and bind approval to the candidate hash",
        "retest": corrected, "retest_sha256": digest(corrected),
        "retest_passed": approval_check(corrected, candidate),
        "changed_candidate_blocked": not approval_check(corrected, digest({"changed": True})),
        "scope": "simulated change approval case",
    }]
    return {
        "scope": "Selected objective exercise using synthetic CUI only",
        "organization": "Aster Ridge Engineering, fictional",
        "assessment_baseline": "NIST SP 800-171 Rev. 2 as referenced in the Level 2 exercise",
        "objectives": [
            {"requirement": "3.1.2", "observation": "Role-specific actions and workspace boundaries",
             "method": "test", "passed": access_passed, "export_sha256": digest(export)},
            {"requirement": "3.3.2", "observation": "Trace three successful actions to configured lab principals",
             "method": "examine and test", "passed": audit_passed, "trace": identity_trace,
             "export_sha256": digest(export)},
            {"requirement": "3.4.3", "observation": "Example release change has candidate-bound approval",
             "method": "examine and test", "finding_id": "F-001"},
        ],
        "findings": findings,
        "tracker_export": export,
        "certification_claimed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = exercise()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    verified = (all(row.get("passed", True) for row in result["objectives"])
                and all(not row["baseline_passed"] and row["retest_passed"] and row["changed_candidate_blocked"]
                        for row in result["findings"]))
    return int(not verified)


if __name__ == "__main__":
    raise SystemExit(main())
