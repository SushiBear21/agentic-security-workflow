"""Fail-closed laboratory readiness decisions; no deployment or compliance authority."""
import math
from pathlib import Path
from app.workflow import digest
from tower.readiness_package import safe_relative, digest as file_digest

HARD_GATES = {"security_tests", "regression_tests", "human_quality", "rollback"}
REQUIRED_GATES = HARD_GATES | {"dependency_scan"}
def assess(package, root, now):
    if type(now) not in (int, float) or not math.isfinite(now):
        raise ValueError("Finite timestamp required")
    if package.get("schema_version") != 1 or package.get("synthetic") is not True:
        raise ValueError("Synthetic versioned assessment required")
    if not isinstance(package.get("model_risk"), dict) or not all(
        isinstance(package["model_risk"].get(k), str) and package["model_risk"][k].strip()
        for k in ("intended_use", "failure_impact", "owner", "boundary")
    ):
        raise ValueError("Model-risk assessment incomplete")
    root = Path(root).resolve()
    evidence = package.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        raise ValueError("Evidence inventory required")
    for name, expected in evidence.items():
        path = root / safe_relative(name)
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file() or file_digest(path) != expected:
            raise ValueError("Missing, unsafe or changed evidence: " + name)
    gates = package.get("gates")
    if not isinstance(gates, dict) or set(gates) != REQUIRED_GATES:
        raise ValueError("Exact gate inventory required")
    for gate in gates.values():
        if set(gate) != {"status", "evidence"} or gate["status"] not in {"pass", "fail", "unmeasured"}:
            raise ValueError("Invalid gate")
        if not isinstance(gate["evidence"], list) or not gate["evidence"] or not set(gate["evidence"]) <= set(evidence):
            raise ValueError("Gate needs inventoried evidence")
    exceptions = package.get("exceptions", [])
    if not isinstance(exceptions, list):
        raise ValueError("Exceptions must be a list")
    waived = set()
    for exception in exceptions:
        if set(exception) != {"gate", "owner", "rationale", "expires_at"}:
            raise ValueError("Invalid exception schema")
        gate = exception["gate"]
        expiry = exception["expires_at"]
        if gate not in REQUIRED_GATES or gate in HARD_GATES or gate in waived:
            raise ValueError("Unknown, duplicate or non-waivable gate")
        if type(expiry) not in (int, float) or not math.isfinite(expiry) or expiry <= now:
            raise ValueError("Expired exception")
        if any(not isinstance(exception[k], str) or not exception[k].strip() for k in ("owner", "rationale")):
            raise ValueError("Exception requires owner and rationale")
        waived.add(gate)
    blocked = [name for name, gate in gates.items() if gate["status"] != "pass" and name not in waived]
    return {"assessment_sha256": digest(package), "scope": "synthetic lab only",
            "status": "blocked" if blocked else "eligible_for_lab_review",
            "blocking_gates": sorted(blocked), "exceptions": exceptions,
            "production_authorized": False}
