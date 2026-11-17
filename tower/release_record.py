"""Assemble a lab release record from scan, holdout, review, and approval evidence."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from p4_holdout import ANSWERED, PROTOCOL, cases
from p4_review import digest, verify_sources
from tower.image_scan import DIGEST, evaluate

SUITE = "prospective-holdout-v1"
CONFIGURATIONS = {"temperature-0": 0, "temperature-0.5": 0.5}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, payload):
    with Path(path).open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2)
        output.write("\n")


def row_key(row):
    return row["config"], row["case_id"]


def packet(report_path, owner):
    report = load(report_path)
    fixtures = {name: request for name, request, _ in cases()}
    expected = {(config, name) for config in CONFIGURATIONS for name in fixtures}
    rows = report["results"]
    configs = report["configurations"]
    if (
        report.get("mode") != "live" or report.get("complete") is not True
        or report.get("suite") != SUITE or report.get("repeats") != 1
        or report.get("calls_attempted") != 4
        or report.get("protocol_sha256") != digest(PROTOCOL)
        or not DIGEST.fullmatch(report.get("release_id") or "")
        or report.get("source_sha256", {}).get("p4_holdout.py") != digest(PROTOCOL.parents[2] / "p4_holdout.py")
        or len(configs) != 2
        or {item["name"]: item["temperature"] for item in configs} != CONFIGURATIONS
        or len({item["model_id"] for item in configs}) != 1
        or len(rows) != len(expected) or {row_key(row) for row in rows} != expected
        or any(row.get("repeat") != 1 or row.get("model_called") is not
               (row["case_id"] in ANSWERED) for row in rows)
    ):
        raise ValueError("A complete live v1 holdout from this protocol is required")
    verify_sources(report)
    return {
        "report_sha256": digest(report_path),
        "protocol_sha256": digest(PROTOCOL),
        "evaluation_owner": owner,
        "image_id": report["release_id"],
        "reviewer": "",
        "rows": [
            {"config": row["config"], "case_id": row["case_id"],
             "sources": fixtures[row["case_id"]]["documents"],
             "draft": row["raw_model_text"], "judgment": None,
             "source_id": "", "rationale": ""}
            for row in rows if row["model_called"]
        ],
    }


def manifest(report_path, review_path, scan_path, image_id, owner, now):
    expected = packet(report_path, owner)
    report = load(report_path)
    review = load(review_path)
    if image_id != expected["image_id"]:
        raise ValueError("Image ID differs from the image registered for the evaluation")
    reviewer = review.get("reviewer", "").strip()
    if not reviewer or reviewer.casefold() == owner.strip().casefold():
        raise ValueError("Name an independent reviewer distinct from the evaluation owner")
    for field in ("report_sha256", "protocol_sha256", "evaluation_owner", "image_id"):
        if review.get(field) != expected[field]:
            raise ValueError("Reviewer packet does not match the evaluation")
    reviews = review["rows"]
    if len(reviews) != len(expected["rows"]) or {row_key(row) for row in reviews} != {
        row_key(row) for row in expected["rows"]
    }:
        raise ValueError("Review all four holdout drafts exactly once")
    saved = {row_key(row): row for row in reviews}
    for entry in expected["rows"]:
        scored = saved[row_key(entry)]
        if (
            scored.get("sources") != entry["sources"] or scored.get("draft") != entry["draft"]
            or scored.get("judgment") not in {"pass", "fail"}
            or scored.get("source_id") not in {doc["id"] for doc in entry["sources"]}
            or len(scored.get("rationale", "").strip()) < 20
        ):
            raise ValueError("Each draft needs a judgment, source ID, and substantive rationale")
    rows = report["results"]
    live = [row for row in rows if row["model_called"]]
    costs = [row.get("estimated_cost_usd") for row in live]
    times = [row.get("model_latency_ms") for row in live]
    valid_cost = all(type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in costs)
    scan_bytes = Path(scan_path).read_bytes()
    scan = evaluate(scan_bytes, image_id, now)
    gates = {
        "image_scan": scan["status"] == "pass",
        "holdout_contract": all(row["passed"] is True for row in rows),
        "independent_review": all(row["judgment"] == "pass" for row in reviews),
        "latency": all(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 15000 for value in times),
        "cost": valid_cost and sum(costs) <= 1,
    }
    return {
        "scope": "synthetic lab release only",
        "image_id": image_id,
        "model_id": report["configurations"][0]["model_id"],
        "evaluation_owner": owner,
        "independent_reviewer": reviewer,
        "identity_verification": "self-attested local reviewer names",
        "scan": scan,
        "gates": gates,
        "evidence_sha256": {
            "protocol": expected["protocol_sha256"], "live_holdout": expected["report_sha256"],
            "independent_review": digest(review_path), "trivy": digest(scan_path),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["packet", "manifest", "finalize"])
    parser.add_argument("--report", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--review")
    parser.add_argument("--scan")
    parser.add_argument("--image-id")
    parser.add_argument("--manifest")
    parser.add_argument("--approval")
    args = parser.parse_args()
    if args.action == "packet":
        write(args.output, packet(args.report, args.owner))
        return 0
    if not all((args.review, args.scan, args.image_id)):
        parser.error("Manifest and finalization require --review, --scan, and --image-id")
    current = manifest(args.report, args.review, args.scan, args.image_id, args.owner,
                       datetime.now(timezone.utc))
    if args.action == "manifest":
        write(args.output, current)
        print("Manifest SHA-256:", digest(args.output))
        return 0
    if not args.manifest or not args.approval:
        parser.error("Finalization requires --manifest and --approval")
    approval = load(args.approval)
    approver = approval.get("approver", "").strip()
    approved = (
        load(args.manifest) == current
        and approval.get("manifest_sha256") == digest(args.manifest)
        and approval.get("decision") == "approve"
        and bool(approver)
        and approver.casefold() != args.owner.strip().casefold()
    )
    eligible = approved and all(current["gates"].values())
    write(args.output, {
        **current, "manifest_sha256": digest(args.manifest), "approval_sha256": digest(args.approval),
        "approval": {"verified_binding": approved, "approver": approver,
                     "decision": approval.get("decision")},
        "status": "eligible_for_lab_release" if eligible else "blocked",
        "production_authorized": False,
    })
    return int(not eligible)


if __name__ == "__main__":
    raise SystemExit(main())
