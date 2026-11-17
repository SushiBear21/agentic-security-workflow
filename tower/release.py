"""Offline customer-deployment rehearsal using the existing local control tower."""
import argparse
import importlib.metadata
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from app.workflow import digest
from tower.store import LocalStore
from tower.report import export, verify_package
from tower.access_demo import demo, verify_audit
from tower.readiness_package import build, verify
from tower.assurance import assess, REQUIRED_GATES
from tower.adoption import measure
from tower.core import metrics
from tower.governance import report as governance_report
from tower.llmops import canary, evaluate_boundary
from p4_regression import evaluate

ROOT = Path(__file__).resolve().parents[1]

def backup(source, destination):
    if Path(destination).exists(): raise ValueError("Backup destination must be new")
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)

def sbom():
    # Inventory pinned application dependencies, not the entire operator environment.
    components = []
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"): continue
        name, pinned = line.split("==", 1)
        installed = importlib.metadata.version(name)
        if installed != pinned:
            raise ValueError("Installed dependency differs from pin: " + name)
        components.append({"type": "library", "name": name, "version": installed,
                           "purl": "pkg:pypi/" + name.lower() + "@" + installed})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "components": components,
            "metadata": {"properties": [{"name": "scope", "value": "Pinned Python application dependencies only; not OS/container inventory or vulnerability scan"}]}}

def rehearse(destination):
    out = Path(destination)
    if out.exists(): raise ValueError("Use a new rehearsal directory")
    out.mkdir(parents=True)
    store = LocalStore(out / "program.sqlite")
    fixtures = json.loads((ROOT / "tower/fixtures.json").read_text())
    store.run("ingest", {"findings": fixtures}, "synthetic-operator", 100)
    baseline = store.read()
    backup(out / "program.sqlite", out / "baseline.sqlite")
    key = store.run("propose", {"id": "SEC-001", "draft": "Synthetic deployment acceptance review", "provider": "reference_fixture"}, "synthetic-operator", 101)
    try:
        store.run("execute", {"id": key}, "synthetic-operator", 102)
    except ValueError: denied = True
    else: raise ValueError("Unapproved action unexpectedly succeeded")
    store.run("approve", {"id": key, "sha256": key, "effort_seconds": 5}, "synthetic-reviewer", 103)
    store.run("execute", {"id": key}, "synthetic-operator", 104)
    if store.run("execute", {"id": key}, "synthetic-operator", 105) != "already_executed":
        raise ValueError("Idempotency check failed")
    export(store.read(), out / "candidate")
    verify_package(out / "candidate/evidence.zip")
    # Inject failed release health, then restore a NEW instance from the pre-release backup.
    # Preserve candidate evidence and avoid overwriting an active database.
    backup(out / "baseline.sqlite", out / "restored.sqlite")
    restored = LocalStore(out / "restored.sqlite")
    if restored.read() != baseline: raise ValueError("Rollback snapshot differs")
    access = demo()
    verify_audit(access)
    dataset = json.loads((ROOT / "tests/fixtures/p4-regression-v1.json").read_text())
    regression = evaluate(dataset)
    if regression["passed"] != regression["total"]: raise ValueError("Regression failed")
    build(out / "readiness")
    verify(out / "readiness")
    security = evaluate_boundary()
    rollout = canary()
    adoption_fixture = json.loads((ROOT / "tests/fixtures/adoption-v1.json").read_text())
    adoption = measure(adoption_fixture)
    adoption["workflow_rehearsal"] = metrics(store.read())
    adoption["model_cost_scenario"] = {
        "scope": "Separate 30-request fixture replay with assumed token counts and rates",
        "estimated_usd": sum(lane["estimated_cost_usd"] for lane in rollout["lanes"].values()),
        "live_model_calls": 0,
    }
    reports = {"regression.json": regression, "access.json": access, "sbom.json": sbom(),
               "adversarial.json": security, "canary.json": rollout, "adoption.json": adoption,
               "acceptance.json": {"scope": "synthetic local deployment rehearsal", "unapproved_denied": denied,
                "ticket_count": len(store.read()["tickets"]), "injected_candidate_health": "failed",
                "rollback_state_equal": True, "candidate_state_sha256": digest(store.read()),
                "restored_state_sha256": digest(restored.read()), "model_calls": 0}}
    for name, value in reports.items():
        (out / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    from tower.readiness_package import digest as file_digest
    package = {"schema_version": 1, "synthetic": True,
               "model_risk": {"intended_use": "advisory synthetic reviews", "failure_impact": "incorrect recommendation",
                              "owner": "lab operator", "boundary": "local SQLite; no cloud remediation or authenticated personas"},
               "evidence": {name: file_digest(out / name) for name in reports},
               "gates": {g: {"status": "unmeasured", "evidence": ["acceptance.json"]} for g in REQUIRED_GATES},
               "exceptions": []}
    package["gates"]["regression_tests"] = {"status": "pass", "evidence": ["regression.json"]}
    package["gates"]["security_tests"] = {
        "status": "pass" if security["passed"] == security["total"] else "fail",
        "evidence": ["adversarial.json"],
    }
    canary_ok = (rollout["rollback"] and rollout["lanes"]["reference-candidate"]["requests"] == 2
                 and rollout["lanes"]["reference-stable"]["accepted"] == 28)
    package["gates"]["rollback"] = {
        "status": "pass" if canary_ok else "fail", "evidence": ["acceptance.json", "canary.json"],
    }
    # Unit tests and a vulnerability scan are not executed by this command.
    # Existing failed live human review remains blocked, never inferred from offline checks.
    package["gates"]["human_quality"] = {"status": "fail", "evidence": ["regression.json"]}
    (out / "assessment.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    decision = assess(package, out, 106)
    (out / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    governance = governance_report(out, datetime.now(timezone.utc), regression, rollout, security, decision, package)
    (out / "governance.json").write_text(json.dumps(governance, indent=2) + "\n", encoding="utf-8")
    return decision

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    decision = rehearse(args.output)
    print(json.dumps(decision, indent=2))
    return int(bool({"security_tests", "regression_tests", "rollback"} & set(decision["blocking_gates"])))

if __name__ == "__main__":
    raise SystemExit(main())
