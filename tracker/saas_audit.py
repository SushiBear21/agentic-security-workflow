"""Evaluate the fixed simulated two-product audit evidence period."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

from tracker.audit_workpapers import EVIDENCE
from tracker.audit_bundle import require


def build_packet(fixture_path=EVIDENCE / "saas-audit-fixture.json"):
    raw = fixture_path.read_bytes()
    fixture = json.loads(raw)
    period = fixture["period"]
    start, end = (date.fromisoformat(period[key]) for key in ("start", "end"))

    def in_period(timestamp):
        return start <= date.fromisoformat(timestamp[:10]) <= end

    roles = fixture["product_a_role_changes"]
    require(roles and all(in_period(row["date"]) for row in roles), "Role sample outside period")
    require(len({row["id"] for row in roles}) == len(roles), "Duplicate role sample")
    role_tests = []
    for row in roles:
        expected_access = {"grant": True, "revoke": False}[row["action"]]
        passed = (row["approved"] is True and row["expected_access"] is expected_access
                  and row["observed_access"] is expected_access)
        role_tests.append({"evidence": row, "result": "pass" if passed else "fail"})

    require(all(row["result"] == "pass" for row in role_tests), "Unexpected role test failure")
    require(fixture["conmon_logging_observation"] == "unverified",
            "Expected an unverified logging observation")
    monitoring_tests = []
    for row in fixture["conmon_asset_observations"]:
        measured = row["last_observed"]
        if measured is None:
            result = "missing"
        else:
            age = (end - date.fromisoformat(measured)).days
            require(age >= 0, "Future monitoring observation")
            result = "current" if age <= 30 else "stale"
        monitoring_tests.append({"evidence": row, "result": result})

    finding = fixture["conmon_remediation"]
    before, after = (finding["retest"][key] for key in ("before", "after"))
    require(before["observed_at"] < period["start"]
            and in_period(after["observed_at"])
            and finding["closure_reference"] == after["id"], "Unexpected remediation chronology")
    remediation_tests = [
        {"evidence": row, "result": "pass" if row["remediation_confirmed"] is True else "fail"}
        for row in (before, after)
    ]
    require([row["result"] for row in remediation_tests] == ["fail", "pass"],
            "Expected failed baseline and passing remediation retest")

    due = "2026-11-20"
    return {
        "classification": fixture["classification"],
        "period": period,
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "monitoring_source": fixture["monitoring_source"],
        "requests": [
            {"id": "SAAS-ER-01", "control": "A-ACCESS", "period": period, "due": due,
             "owner": "Product A Access Owner", "fixture_key": "product_a_role_changes",
             "status": "fulfilled", "population": len(roles), "sample": role_tests},
            {"id": "SAAS-ER-02", "control": "SH-LOG", "period": period, "due": due,
             "owner": "Evidence Operations", "fixture_key": "conmon_logging_observation",
             "status": "insufficient", "population": 1,
             "sample": [{"id": "SYN-S3 logging", "evidence": fixture["conmon_logging_observation"],
                         "result": "insufficient"}], "finding": "SAAS-G01"},
            {"id": "SAAS-ER-03", "control": "B-PATCH", "period": period, "due": due,
             "owner": finding["owner"], "fixture_key": "conmon_remediation",
             "status": "fulfilled", "population": 1, "sample": remediation_tests,
             "finding": "SAAS-F01"},
            {"id": "SAAS-ER-04", "control": "SH-MON", "period": period, "due": due,
             "owner": "Monitoring Lead", "fixture_key": "conmon_asset_observations",
             "status": "insufficient", "population": len(monitoring_tests),
             "sample": monitoring_tests, "finding": "SAAS-G02"},
            {"id": "SAAS-ER-05", "control": "B-CHANGE", "period": period, "due": due,
             "owner": "Product B Release Owner", "fixture_key": None,
             "status": "missing", "population": None, "sample": [], "finding": "SAAS-G03"},
        ],
        "findings": {
            "SAAS-G01": {
                "source": "SYN-002",
                "impact": "Audit events might not reach central storage.",
                "root_cause": "The fixture contains an unverified lookup and no event-delivery receipt.",
                "owner": "Evidence Operations",
                "action": "Provide event-class coverage and trace a product event to the archive.",
                "retest": "pending", "closure": "pending",
            },
            "SAAS-G02": {
                "impact": "Unobserved assets could carry undiscovered configuration or image issues.",
                "root_cause": "The fixture inventory contains one stale and one missing observation.",
                "owner": "Monitoring Lead",
                "action": "Refresh DynamoDB and collect the ECR observation, then rerun freshness.",
                "retest": "pending", "closure": "pending",
            },
            "SAAS-G03": {
                "impact": "Changes may reach the product without documented approval.",
                "root_cause": "The exercise has no Product B approval or promotion record.",
                "owner": "Product B Release Owner",
                "action": "Capture the population and bind a lab approval to a promotion revision.",
                "retest": "pending", "closure": "pending",
            },
            "SAAS-F01": {
                "source": finding["id"],
                "impact": "A simulated flaw could remain unresolved while reported as fixed.",
                "root_cause": "The fixture baseline omitted remediation confirmation.",
                "owner": finding["owner"], "action": finding["remediation"],
                "retest": after["id"], "retest_result": "pass in fixture",
                "simulated_source_disposition": finding["status"],
                "independent_reviewer_disposition": "pending", "closure": "pending",
            },
        },
        "review": {"reviewer": None, "revision": None, "decision": "pending",
                   "owner_signoff": "pending"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = build_packet()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(packet, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
