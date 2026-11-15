"""Validate selected-control synthetic SSP/POA&M and evidence freshness."""
import argparse
import json
from datetime import datetime, timezone, date
from pathlib import Path
from tower.readiness_package import safe_relative, digest

ROOT = Path(__file__).resolve().parents[1]
def validate_plan(plan, controls):
    if plan.get("schema_version") != 1 or plan.get("synthetic") is not True:
        raise ValueError("Synthetic versioned POA&M required")
    rows = plan["items"]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)): raise ValueError("Duplicate POA&M IDs")
    mapped = {r["control"] for r in controls}
    if {r["control"] for r in rows} != mapped: raise ValueError("Every selected control needs a tracked gap")
    for row in rows:
        for key in ("id", "owner", "weakness", "remediation", "validation"):
            if not isinstance(row.get(key), str) or not row[key].strip(): raise ValueError("Missing POA&M field: " + key)
        if row["risk"] not in {"low", "moderate", "high"} or row["status"] not in {"open", "in_progress", "closed"}:
            raise ValueError("Invalid risk/status")
        opened, due = date.fromisoformat(row["identified"]), date.fromisoformat(row["due"])
        if due < opened: raise ValueError("Due date precedes finding")
        if not isinstance(row["milestones"], list) or not row["milestones"]: raise ValueError("Milestones required")
        for milestone in row["milestones"]:
            if not milestone["description"].strip() or not opened <= date.fromisoformat(milestone["due"]) <= due:
                raise ValueError("Invalid milestone")
        if row["status"] == "closed" and not row.get("closure_evidence"):
            raise ValueError("Closure requires evidence")
    return {"scope": "selected-control synthetic exercise", "items": len(rows),
            "open": sum(r["status"] != "closed" for r in rows), "authorization": "none"}

def monitor(requirements, evidence, root, now):
    if now.tzinfo is None: raise ValueError("Aware current time required")
    if len({r["id"] for r in requirements}) != len(requirements): raise ValueError("Duplicate monitoring requirements")
    result = []
    for rule in requirements:
        if type(rule["max_age_hours"]) is not int or rule["max_age_hours"] <= 0: raise ValueError("Positive freshness period required")
        record = evidence.get(rule["id"])
        status = "missing"
        if record:
            try:
                measured = datetime.fromisoformat(record["measured_at"].replace("Z", "+00:00"))
                if measured.tzinfo is None: raise ValueError("Timezone required")
                age = (now - measured).total_seconds()
                base = Path(root).resolve()
                p = base / safe_relative(record["path"])
                if not p.resolve().is_relative_to(base) or p.is_symlink() or not p.is_file() or digest(p) != record["sha256"]:
                    status = "invalid_integrity"
                elif age < 0: status = "future_timestamp"
                elif age > rule["max_age_hours"] * 3600: status = "stale"
                elif record["outcome"] != "pass": status = "failed"
                else: status = "current"
            except (ValueError, KeyError, TypeError, OSError):
                status = "invalid_evidence"
        result.append({"id": rule["id"], "owner": rule["owner"], "status": status})
    return {"scope": "evidence freshness and reported outcomes, not continuous control effectiveness",
            "ready": bool(result) and all(r["status"] == "current" for r in result), "results": result}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--poam", default=str(ROOT / "docs/portfolio/poam.json"))
    p.add_argument("--monitoring-evidence")
    p.add_argument("--evidence-root", default=".")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    controls = json.loads((ROOT / "docs/portfolio/readiness-controls.json").read_text())
    result = {"poam": validate_plan(json.loads(Path(a.poam).read_text()), controls)}
    requirements = json.loads((ROOT / "docs/portfolio/monitoring-plan.json").read_text())
    evidence = json.loads(Path(a.monitoring_evidence).read_text()) if a.monitoring_evidence else {}
    result["monitoring"] = monitor(requirements, evidence, a.evidence_root, datetime.now(timezone.utc))
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Absence of operational evidence is represented, never replaced by a fixture.
    return 0 if result["monitoring"]["ready"] else 2

if __name__ == "__main__": raise SystemExit(main())
