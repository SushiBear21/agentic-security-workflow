"""Bind a tracker rehearsal decision to its source, image, smoke, scan, and SBOM."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from tower.image_scan import evaluate

ISSUES = [8, 9, 11]


def decision(scan, smoke, sbom):
    gates = {"image_scan": scan.get("status") == "pass",
             "workflow_smoke": smoke.get("passed") is True,
             "cyclonedx_inventory": sbom.get("bomFormat") == "CycloneDX"
             and bool(sbom.get("components"))}
    return {"gates": gates, "outcome": "eligible_for_review" if all(gates.values()) else "blocked"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("scan", "sbom", "browser", "baseline", "candidate", "recovery", "output"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--pull-request", type=int)
    args = parser.parse_args()

    inputs = {key: getattr(args, key).read_bytes() for key in ("scan", "sbom", "browser", "baseline", "candidate", "recovery")}
    scan = evaluate(inputs["scan"], args.image_id, datetime.now(timezone.utc), require_language=False)
    sbom = json.loads(inputs["sbom"])
    smoke = {key: json.loads(inputs[key]) for key in ("baseline", "candidate", "recovery")}
    smoke["recovery"]["passed"] = smoke["recovery"].get("passed") is True and smoke["recovery"].get("preserved_baseline") is True
    phases = {key: decision(scan, smoke[key], sbom)
              for key in ("baseline", "candidate", "recovery")}
    observed = [phases[key]["outcome"] for key in ("baseline", "candidate", "recovery")]
    browser_verified = json.loads(inputs["browser"]).get("passed") is True
    verified = browser_verified and observed == ["eligible_for_review", "blocked", "eligible_for_review"]
    args.output.write_text(json.dumps({
        "scope": "CI release rehearsal with injected runtime configuration failure",
        "repository": "SushiBear21/agentic-security-workflow", "commit": args.revision,
        "pull_request": args.pull_request, "issues": ISSUES, "image_id": args.image_id,
        "inputs_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in inputs.items()},
        "phases": phases, "scan_scope": "OS packages on a stdlib-only runtime", "scan": scan,
        "browser_acceptance": browser_verified, "rehearsal_passed": verified, "promotion_authorized": False,
    }, indent=2) + "\n", encoding="utf-8")
    return int(not verified)


if __name__ == "__main__":
    raise SystemExit(main())
