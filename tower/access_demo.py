"""Synthetic, in-memory privileged-access lab. Not an IAM or identity provider."""
import json
import math
import re
from copy import deepcopy
from threading import RLock

from app.workflow import digest
from tower.core import event

# Fixed server-owned policy: the client cannot supply its own roles or scope.
PRINCIPALS = {"lab-requester": "requester", "lab-approver": "approver", "lab-executor": "executor"}
ALLOWED = {( "read_synthetic_evidence", "lab://evidence/SEC-001")}
MAX_TTL = 300


def timestamp(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("invalid timestamp")
    return value


class AccessLab:
    """Single-process simulation; supplied actor names are NOT authenticated."""
    def __init__(self):
        self._requests = {}
        self._events = []
        self._lock = RLock()

    def snapshot(self):
        with self._lock:
            return deepcopy({"synthetic": True, "requests": self._requests, "events": self._events})

    def _audit(self, kind, actor, details, now):
        event({"events": self._events}, kind, actor if isinstance(actor, str) and actor else "invalid-actor", details, now)

    def _deny(self, reason):
        raise ValueError(reason)

    def run(self, command, args, actor, now):
        """Each accepted transition/denial is audited; no external side effects."""
        with self._lock:
            now = timestamp(now)
            try:
                result = self._transition(command, args, actor, now)
            except (ValueError, KeyError, TypeError) as exc:
                self._audit("access_denied", actor, {"command": str(command), "reason": str(exc)}, now)
                raise ValueError(str(exc)) from exc
            self._audit("access_" + command, actor, {"request_id": args.get("id"), "result": result}, now)
            return deepcopy(result)

    def _transition(self, command, args, actor, now):
        if not isinstance(args, dict):
            self._deny("arguments must be a dictionary")
        role = PRINCIPALS.get(actor)
        required = {"request": "requester", "approve": "approver", "reject": "approver", "revoke": "approver", "execute": "executor"}.get(command)
        if required is None or role != required:
            self._deny("principal not permitted for command")
        if command == "request":
            if set(args) != {"id", "action", "resource", "ttl_seconds", "reason"}:
                self._deny("exact request schema required")
            key = args["id"]
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key):
                self._deny("invalid request id")
            if key in self._requests:
                self._deny("request id already used")
            if (args["action"], args["resource"]) not in ALLOWED:
                self._deny("action/resource outside allowlist")
            ttl = args["ttl_seconds"]
            if type(ttl) is not int or not 1 <= ttl <= MAX_TTL:
                self._deny("ttl must be 1..300 seconds")
            if not isinstance(args["reason"], str) or not 1 <= len(args["reason"].strip()) <= 300:
                self._deny("invalid reason")
            payload = {**args, "requester": actor, "synthetic": True, "created_at": now, "expires_at": now + ttl}
            self._requests[key] = {"payload": deepcopy(payload), "sha256": digest(payload), "state": "PENDING", "approval": None}
            return {"id": key, "sha256": digest(payload)}
        if set(args) != {"id", "sha256"}:
            self._deny("exact decision/execution schema required")
        record = self._requests[args["id"]]
        payload = record["payload"]
        if digest(payload) != record["sha256"] or args["sha256"] != record["sha256"]:
            self._deny("payload digest mismatch")
        if not payload["created_at"] <= now < payload["expires_at"]:
            self._deny("request not yet valid or expired")
        if (payload["action"], payload["resource"]) not in ALLOWED:
            self._deny("action/resource outside allowlist")
        if command == "revoke":
            if record["state"] != "APPROVED":
                self._deny("only approved unused requests can be revoked")
            record["state"] = "REVOKED"
            return "REVOKED"
        if command in {"approve", "reject"}:
            if actor == payload["requester"] or record["state"] != "PENDING":
                self._deny("independent pending decision required")
            record["state"] = "APPROVED" if command == "approve" else "REJECTED"
            record["approval"] = {"actor": actor, "sha256": record["sha256"], "at": now, "decision": command}
            return record["state"]
        approval = record["approval"]
        if record["state"] != "APPROVED" or not approval or approval["decision"] != "approve":
            self._deny("unused approval required")
        if (approval["sha256"] != digest(payload) or PRINCIPALS.get(approval["actor"]) != "approver"
                or approval["actor"] == payload["requester"] or not payload["created_at"] <= approval["at"] <= now):
            self._deny("invalid independent approval")
        record["state"] = "EXECUTED"
        return {"synthetic": True, "resource": payload["resource"], "evidence": "Synthetic fixture: SEC-001 administrative exposure review"}


def verify_audit(snapshot):
    """Detect edits to existing chain; not protection against full rewrite/truncation."""
    previous = "0" * 64
    for index, entry in enumerate(snapshot["events"]):
        body = {k: v for k, v in entry.items() if k != "sha256"}
        if entry["sequence"] != index or entry["previous"] != previous or digest(body) != entry["sha256"]:
            raise ValueError("audit integrity mismatch")
        previous = entry["sha256"]
    return True


def demo():
    lab = AccessLab()
    request = lab.run("request", {"id": "DEMO-001", "action": "read_synthetic_evidence", "resource": "lab://evidence/SEC-001", "ttl_seconds": 60, "reason": "Synthetic evidence review"}, "lab-requester", 100)
    for command, actor, now in [("execute", "lab-executor", 101), ("approve", "lab-approver", 102), ("execute", "lab-executor", 103), ("execute", "lab-executor", 104)]:
        try:
            lab.run(command, request, actor, now)
        except ValueError:
            pass
    return lab.snapshot()


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
