"""Build AI RMF evidence from the same artifacts used in the release assessment."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from tower.compliance import monitor
from tower.readiness_package import digest

CONTROLS = {
    "GOVERN": "Record owners and enforce time-bounded exceptions through the release assessment.",
    "MAP": "Inventory model profiles and datasets and record intended use and risk owners.",
    "MEASURE": "Track boundary checks, versioned regression and freshness of evidence.",
    "MANAGE": "Block release on unmet gates and rehearse candidate rollback.",
}

RISKS = [
    {"id": "AI-01", "risk": "Unsafe or unsupported draft", "owner": "AI review lead",
     "gate": "human_quality"},
    {"id": "AI-02", "risk": "Untrusted content or unauthorized action", "owner": "Security lead",
     "gate": "security_tests"},
    {"id": "AI-03", "risk": "Candidate quality or routing regression", "owner": "Release lead",
     "gate": "rollback"},
]

EVIDENCE = (
    ("regression_tests", "regression.json", "Evaluation lead"),
    ("security_tests", "adversarial.json", "Security lead"),
    ("rollback", "canary.json", "Release lead"),
)


def report(root, generated_at, regression, canary, security, decision, assessment, *, now=None):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    result = {
        "regression_tests": regression["passed"] == regression["total"],
        "security_tests": security["passed"] == security["total"],
        "rollback": canary["rollback"],
    }
    rules, evidence = [], {}
    for gate, filename, owner in EVIDENCE:
        rules.append({"id": gate, "owner": owner, "max_age_hours": 48})
        path = root / filename
        if path.is_file():
            evidence[gate] = {"path": filename, "sha256": assessment["evidence"][filename],
                              "measured_at": generated_at.isoformat(),
                              "outcome": "pass" if result[gate] else "fail"}

    return {
        "synthetic": True, "standard": "NIST AI RMF 1.0", "mapping": CONTROLS,
        "generated_at": generated_at.isoformat(),
        "model_inventory": {
            "intended_use": "Synthetic advisory asset review",
            "owner": "AI review lead", "scope": "Fixture profiles used in this rehearsal",
            "profiles": canary["profiles"], "prompt_version": canary["prompt_version"],
            "prompt_sha256": canary["prompt_sha256"],
        },
        "dataset_inventory": [
            {"version": regression["dataset_version"], "sha256": regression["dataset_sha256"],
             "owner": "Evaluation lead", "provenance": "Repository synthetic regression fixtures"},
            {"version": security["fixture_version"], "sha256": digest(root / "adversarial.json"),
             "owner": "Security lead", "provenance": "Repository synthetic model-boundary scenarios",
             "hash_scope": "generated report"},
        ],
        "risk_register": [{**risk, "status": "open" if risk["gate"] in decision["blocking_gates"]
                           else "fixture_control_exercised"} for risk in RISKS],
        "exceptions": decision["exceptions"],
        "monitoring_rules": rules, "evidence_inventory": evidence,
        "monitoring": monitor(rules, evidence, root, now),
        "release_status": decision["status"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_directory", type=Path)
    args = parser.parse_args()
    root = args.evidence_directory
    manifest = json.loads((root / "governance.json").read_text(encoding="utf-8"))
    result = monitor(manifest["monitoring_rules"], manifest["evidence_inventory"],
                     root, datetime.now(timezone.utc))
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
