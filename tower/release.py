"""Offline customer-deployment rehearsal using the existing local control tower."""
import argparse
import importlib.metadata
import json
import sqlite3
import subprocess
import sys
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
from p4_finish import assess as assess_model_review
from p4_review import validate_report, validate_review, verify_sources
from tower.readiness_package import digest as file_digest

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

def dependency_evidence(out, components):
    raw = out / "dependency-audit.json"
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-r", str(ROOT / "requirements.txt"),
         "--format", "json", "--output", str(raw)],
        check=False,
    )
    expected = {(c["name"].lower().replace("_", "-"), c["version"]) for c in components}
    try:
        dependencies = json.loads(raw.read_text(encoding="utf-8"))["dependencies"]
        observed = [(row["name"].lower().replace("_", "-"), row["version"]) for row in dependencies]
        clean = (len(observed) == len(expected) and set(observed) == expected
                 and all(row["vulns"] == [] for row in dependencies))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        clean = False
    return {
        "status": "pass" if result.returncode == 0 and clean else "fail",
        "exit_code": result.returncode,
        "requirements_sha256": file_digest(ROOT / "requirements.txt"),
        "report_sha256": file_digest(raw) if raw.is_file() else None,
        "scope": "Pinned Python application dependencies",
    }


def review_evidence(comparison):
    if comparison is None:
        return {"status": "unmeasured", "reason": "Current live comparison and human review required"}
    comparison = Path(comparison)
    review_path = comparison.with_name("human-review.json")
    report = json.loads(comparison.read_text(encoding="utf-8-sig"))
    review = json.loads(review_path.read_text(encoding="utf-8-sig"))
    live = validate_report(report)
    verify_sources(report)
    report_sha256 = file_digest(comparison)
    validate_review(review, report_sha256, live)
    metrics, selected, cost = assess_model_review(report, review)
    return {
        "status": "pass" if selected else "fail", "selected_configuration": selected,
        "report_sha256": report_sha256, "review_sha256": file_digest(review_path),
        "metrics": metrics, "estimated_cost_usd": cost,
        "scope": "Source-linked, self-attested human review of a live synthetic comparison",
    }


def rehearse(destination, *, audit=False, comparison=None):
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
    inventory = sbom()
    scan = dependency_evidence(out, inventory["components"]) if audit else {"status": "unmeasured"}
    quality = review_evidence(comparison)
    reports = {"regression.json": regression, "access.json": access, "sbom.json": inventory,
               "dependency-gate.json": scan, "human-quality.json": quality,
               "adversarial.json": security, "canary.json": rollout, "adoption.json": adoption,
               "acceptance.json": {"scope": "synthetic local deployment rehearsal", "unapproved_denied": denied,
                "ticket_count": len(store.read()["tickets"]), "injected_candidate_health": "failed",
                "rollback_state_equal": True, "candidate_state_sha256": digest(store.read()),
                "restored_state_sha256": digest(restored.read()), "model_calls": 0}}
    for name, value in reports.items():
        (out / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
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
    package["gates"]["human_quality"] = {"status": quality["status"], "evidence": ["human-quality.json"]}
    audit_files = ["dependency-gate.json"]
    if scan.get("report_sha256"):
        package["evidence"]["dependency-audit.json"] = scan["report_sha256"]
        audit_files.append("dependency-audit.json")
    package["gates"]["dependency_scan"] = {"status": scan["status"], "evidence": audit_files}
    (out / "assessment.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    decision = assess(package, out, 106)
    (out / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    governance = governance_report(out, datetime.now(timezone.utc), regression, rollout, security, decision, package)
    (out / "governance.json").write_text(json.dumps(governance, indent=2) + "\n", encoding="utf-8")
    return decision

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", action="store_true", help="Run pip-audit and require a clean report")
    parser.add_argument("--comparison", type=Path, help="Live comparison.json with sibling human-review.json")
    args = parser.parse_args()
    decision = rehearse(args.output, audit=args.audit, comparison=args.comparison)
    print(json.dumps(decision, indent=2))
    required = {"security_tests", "regression_tests", "rollback"}
    if args.audit:
        required.add("dependency_scan")
    if args.comparison is not None:
        required.add("human_quality")
    return int(bool(required & set(decision["blocking_gates"])))

if __name__ == "__main__":
    raise SystemExit(main())
