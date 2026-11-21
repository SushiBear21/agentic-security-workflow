"""Workspace-scoped SQLite evidence workflows for the portfolio lab."""
import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from hmac import compare_digest
from uuid import UUID

from app.workflow import digest
from tower.core import event, verify
from tower.store import encode


@dataclass(frozen=True)
class Principal:
    workspace: str
    name: str
    role: str


def load_principals(path):
    """Tokens are provisioned outside the application and never exported."""
    with open(path, encoding="utf-8") as source:
        rows = json.load(source)
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty credential list")
    accounts = {}
    identities = set()
    for row in rows:
        token = row["token"]
        principal = Principal(row["workspace"], row["name"], row["role"])
        if (not isinstance(token, str) or not token.isascii() or not 32 <= len(token) <= 128
                or not token.isalnum() or token in accounts):
            raise ValueError("Tokens must be unique, 32–128 ASCII letters or digits")
        if (not all(isinstance(value, str) and value.isascii() and value.isalnum()
                    and len(value) <= 40 for value in (principal.workspace, principal.name))
                or principal.role not in {"contributor", "reviewer"}):
            raise ValueError("Invalid workspace, username or role")
        identity = (principal.workspace, principal.name)
        if identity in identities:
            raise ValueError("A workspace principal must have exactly one role")
        identities.add(identity)
        accounts[token] = principal
    return accounts


def authenticate(accounts, header):
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.isascii() or len(token) > 128:
        return None
    return next((principal for secret, principal in accounts.items()
                 if compare_digest(token, secret)), None)


def field(value, limit):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError(f"Expected text of 1–{limit} characters")
    return value.strip()


def require_schema(body, names):
    if not isinstance(body, dict) or set(body) != names:
        raise ValueError("Unexpected request fields")


def identifier(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("Expected a canonical UUID")
    return value


class Tracker:
    def __init__(self, path, clock=time.time):
        self.path = path
        self.clock = clock
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, body TEXT NOT NULL)")

    def run(self, principal, action, body=None):
        allowed = {"contributor": {"list", "submit"}, "reviewer": {"list", "review", "export"}}
        if action not in allowed.get(principal.role, set()):
            raise PermissionError("Role cannot perform this action")

        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            if action != "list":
                db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM workspaces WHERE id=?", (principal.workspace,)).fetchone()
            state = json.loads(row[0]) if row else {"items": {}, "events": []}
            verify({"events": state["events"], "proposals": {}})
            records = state["items"]
            if action == "list":
                return [item for item in records.values()
                        if principal.role == "reviewer" or item["submitted_by"] == principal.name]
            now = self.clock()
            if action == "export":
                event(state, "exported", principal.name, {"records_sha256": digest(records)}, now)
                item = {"schema_version": 1, "scope": "synthetic evidence lab",
                        "workspace": principal.workspace, "records": list(records.values()),
                        "events": state["events"], "exported_at": now}
            elif action == "submit":
                require_schema(body, {"id", "title", "note"})
                key = identifier(body["id"])
                payload = {"id": key, "title": field(body["title"], 100),
                           "note": field(body["note"], 2000), "submitted_by": principal.name}
                checksum = digest(payload)
                if key in records:
                    if records[key]["sha256"] == checksum:
                        return records[key]
                    raise ValueError("Submission ID is already in use")
                item = {**payload, "sha256": checksum, "status": "pending", "submitted_at": now}
                records[key] = item
                event(state, "submitted", principal.name, {"id": key, "sha256": checksum}, now)
            else:
                require_schema(body, {"id", "sha256", "decision", "reason"})
                key = identifier(body["id"])
                item = records[key]
                payload = {name: item[name] for name in ("id", "title", "note", "submitted_by")}
                if body["sha256"] != item["sha256"] or digest(payload) != item["sha256"]:
                    raise ValueError("Review digest does not match the evidence")
                decision = body["decision"]
                if decision not in ("approve", "reject"):
                    raise ValueError("Expected approve or reject")
                reason = field(body["reason"], 500)
                status = {"approve": "approved", "reject": "rejected"}[decision]
                if item["status"] != "pending":
                    if (item["status"], item["reviewed_by"], item["reason"]) == (status, principal.name, reason):
                        return item
                    raise ValueError("Evidence already reviewed")
                item.update(status=status, reviewed_by=principal.name, reason=reason, reviewed_at=now)
                event(state, "reviewed", principal.name,
                      {"id": key, "sha256": item["sha256"], "decision": decision,
                       "reason_sha256": digest(reason)}, now)

            db.execute("INSERT INTO workspaces VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                       (principal.workspace, encode(state)))
            return item
