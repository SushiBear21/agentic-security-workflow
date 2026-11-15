"""Pure transitions. Storage commits payload, ticket, and audit atomically."""
import json
import math
import re
import time
from copy import deepcopy
from datetime import date
from app.workflow import digest

CONTROLS = {
    "public_admin_port": (["SC-7", "CM-6"], "Verify exposure; restrict administrative ingress; retain before/after evidence."),
    "unpatched_component": (["SI-2", "RA-5"], "Verify applicability; test patch and rollback; record validation."),
    "vendor_assurance_gap": (["SR-6", "SA-9"], "Request vendor assurance evidence; document gaps and risk-owner disposition."),
    "benign": (["CA-7"], "Review classification and retain supporting evidence."),
}


def empty():
    return {"schema": 1, "findings": {}, "proposals": {}, "tickets": {}, "events": [], "attempts": []}


def text(value, maximum=200):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("Invalid text field")
    return value


def validate_finding(f):
    fields = {"id", "synthetic", "kind", "category", "title", "owner", "likelihood", "impact", "milestone", "due", "dependencies", "evidence", "expected_positive"}
    if not isinstance(f, dict) or set(f) != fields or f["synthetic"] is not True:
        raise ValueError("Exact synthetic finding schema required")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", text(f["id"])):
        raise ValueError("Invalid ID")
    if f["kind"] not in {"security", "vendor"} or f["category"] not in CONTROLS:
        raise ValueError("Unknown finding kind/category")
    if (f["category"] == "vendor_assurance_gap") != (f["kind"] == "vendor"):
        raise ValueError("Category/kind mismatch")
    for k in ("title", "owner", "milestone"):
        text(f[k])
    text(f["evidence"], 3000)
    date.fromisoformat(f["due"])
    for k in ("likelihood", "impact"):
        if type(f[k]) is not int or not 1 <= f[k] <= 5:
            raise ValueError("Risk inputs must be integers 1..5")
    if type(f["expected_positive"]) is not bool:
        raise ValueError("Ground truth must be boolean")
    d = f["dependencies"]
    if not isinstance(d, list) or len(d) > 20 or any(not isinstance(x, str) for x in d) or len(set(d)) != len(d) or f["id"] in d:
        raise ValueError("Invalid dependencies")


def event(s, kind, actor, details, now):
    e = {"sequence": len(s["events"]), "at": now, "kind": kind, "actor": text(actor), "details": details,
         "previous": s["events"][-1]["sha256"] if s["events"] else "0" * 64}
    e["sha256"] = digest(e)
    s["events"].append(e)


def verify(s):
    previous = "0" * 64
    for i, e in enumerate(s["events"]):
        body = {k: v for k, v in e.items() if k != "sha256"}
        if e["sequence"] != i or e["previous"] != previous or digest(body) != e["sha256"]:
            raise ValueError("Audit chain mismatch")
        previous = e["sha256"]
    for p in s["proposals"].values():
        if digest(p["payload"]) != p["sha256"] or digest(s["findings"][p["payload"]["finding_id"]]) != p["payload"]["finding_sha256"]:
            raise ValueError("Proposal/evidence integrity mismatch")


def transition(state, command, args, actor, now=None):
    now = time.time() if now is None else now
    s = deepcopy(state)
    verify(s)
    result = None
    if command == "ingest":
        batch = args["findings"]
        if not isinstance(batch, list) or not 1 <= len(batch) <= 50:
            raise ValueError("Expected 1..50 findings")
        ids = []
        for f in batch:
            validate_finding(f)
            if f["id"] in ids:
                raise ValueError("Duplicate batch ID")
            ids.append(f["id"])
            if f["id"] in s["findings"] and s["findings"][f["id"]] != f:
                raise ValueError("Conflicting immutable finding")
            s["findings"][f["id"]] = deepcopy(f)
        def visit(key, path):
            if key in path or key not in s["findings"]:
                raise ValueError("Dependency cycle or missing dependency")
            for dep in s["findings"][key]["dependencies"]:
                visit(dep, path | {key})
        for key in s["findings"]:
            visit(key, set())
        result = ids
    elif command == "propose":
        f = s["findings"][args["id"]]
        draft = text(args["draft"], 1500)
        provider = args["provider"]
        if provider not in {"reference_fixture", "bedrock_unverified"}:
            raise ValueError("Unsupported draft provider")
        controls, requirement = CONTROLS[f["category"]]
        payload = {"action": "create_synthetic_remediation_ticket", "synthetic": True,
                   "finding_id": f["id"], "finding_sha256": digest(f), "owner": f["owner"],
                   "controls": controls, "requirement": requirement, "risk_score": f["likelihood"] * f["impact"],
                   "dependencies": f["dependencies"], "milestone": f["milestone"], "due": f["due"],
                   "draft": draft, "provider": provider, "ai_quality_gate": "BLOCKED_PENDING_NEW_EVALUATION"}
        key = digest(payload)
        if key not in s["proposals"]:
            s["proposals"][key] = {"payload": payload, "sha256": key, "state": "PENDING", "created_at": now, "approval": None}
        result = key
    elif command in {"approve", "reject"}:
        p = s["proposals"][args["id"]]
        if p["state"] != "PENDING" or args["sha256"] != p["sha256"]:
            raise ValueError("Pending exact-payload decision required")
        effort = args["effort_seconds"]
        if type(effort) not in (int, float) or not math.isfinite(effort) or effort < 0:
            raise ValueError("Invalid self-reported effort")
        p["state"] = "APPROVED" if command == "approve" else "REJECTED"
        p["approval"] = {"sha256": p["sha256"], "actor": actor, "at": now, "expires": now + 600,
                         "effort_seconds": effort, "decision": command}
        result = p["state"]
    elif command == "execute":
        p = s["proposals"][args["id"]]
        a = p["approval"]
        if p["state"] == "EXECUTED":
            ticket = s["tickets"].get(p["sha256"])
            if not ticket or ticket["payload"] != p["payload"]:
                raise ValueError("Completed ticket mismatch")
            return s, "already_executed"
        if p["state"] != "APPROVED" or not a or a["decision"] != "approve" or a["sha256"] != p["sha256"] or not a["at"] <= now < a["expires"]:
            raise ValueError("Approval missing, invalid, or expired")
        if p["payload"]["action"] != "create_synthetic_remediation_ticket":
            raise ValueError("Unsupported action")
        # One atomic state commit: no network remediation and no dual-write uncertainty.
        s["tickets"][p["sha256"]] = {"payload": deepcopy(p["payload"]), "status": "OPEN", "created_at": now, "closure_evidence": None}
        p["state"] = "EXECUTED"
        result = "executed"
    elif command == "status":
        t = s["tickets"][args["id"]]
        status = args["status"]
        if status not in {"IN_PROGRESS", "BLOCKED", "DONE"} or t["status"] == "DONE":
            raise ValueError("Invalid status transition")
        if status == "DONE":
            done = {v["payload"]["finding_id"] for v in s["tickets"].values() if v["status"] == "DONE"}
            if not set(t["payload"]["dependencies"]) <= done:
                raise ValueError("Unresolved dependencies")
            t["closure_evidence"] = text(args["evidence"], 2000)
        t["status"] = status
        result = status
    else:
        raise ValueError("Unknown command")
    event(s, command, actor, {"result": result, "target": args.get("id")}, now)
    return s, result


def metrics(s):
    findings = list(s["findings"].values())
    pairs = [(f["category"] != "benign", f["expected_positive"]) for f in findings]
    tp = sum(p and y for p, y in pairs); fp = sum(p and not y for p, y in pairs)
    tn = sum(not p and not y for p, y in pairs); fn = sum(not p and y for p, y in pairs)
    reviews = [p for p in s["proposals"].values() if p["approval"]]
    attempts = s["attempts"]
    return {"classification_basis": "synthetic category routing versus supplied fixture labels; not model accuracy",
            "sample_size": len(pairs), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "accuracy": (tp + tn) / len(pairs) if pairs else None,
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "workflow_attempts": len(attempts), "workflow_successes": sum(a["success"] for a in attempts),
            "workflow_reliability": sum(a["success"] for a in attempts) / len(attempts) if attempts else None,
            "review_count": len(reviews), "mean_review_elapsed_seconds": sum(p["approval"]["at"] - p["created_at"] for p in reviews) / len(reviews) if reviews else None,
            "review_effort_seconds_self_reported": sum(p["approval"]["effort_seconds"] for p in reviews),
            "operational_effort_savings": None}
