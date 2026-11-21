"""Local, defensive MCP stdio identity/authorization exercise using harmless fixtures.

No network, cloud, data exfiltration, or production credential handling.
The trusted harness issues demonstration credentials; agents cannot mint approvals.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import math
import secrets
import sys
import time
from copy import deepcopy
from pathlib import Path
from threading import RLock

from app.workflow import digest  # Reuse exact-payload canonical hashing.
from tower.access_demo import MAX_TTL, PRINCIPALS  # Reuse fixture role assignments.

AUDIENCE = "local-mcp-identity-lab"
TOOL_PERMISSIONS = {
    "evidence.read": {"roles": {"requester", "executor"}, "scope": "evidence:read", "approval": False},
    "ticket.create": {"roles": {"executor"}, "scope": "ticket:create", "approval": True},
}
FIXTURES = {"SEC-001": {"title": "Synthetic endpoint alert", "risk": "low", "synthetic": True}}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def b64(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def unb64(text):
    return base64.urlsafe_b64decode(text + ("=" * (-len(text) % 4)))


class AccessError(Exception):
    """Expected denial; errors never echo secrets."""


class MCPIdentityLab:
    """In-memory authorization server + MCP tool server for local study only.

    The trusted fixture runner calls issue_credential/approve *out of band*.
    Neither method is an MCP tool. Tokens are signed but never persisted.
    """

    def __init__(self, secret=None):
        self._secret = secret if secret is not None else secrets.token_bytes(32)
        if not isinstance(self._secret, bytes) or len(self._secret) < 32:
            raise ValueError("Strong local signing secret required")
        self._lock = RLock()
        self._approvals = {}
        self._tickets = {}
        self._audit = []
        self._sequence = 0

    def issue_credential(self, actor, scopes, now=None, ttl_seconds=60, audience=AUDIENCE):
        """Trusted harness only. No MCP endpoint issues credentials."""
        now = time.time() if now is None else now
        if actor not in PRINCIPALS or not isinstance(scopes, (list, tuple)) or not scopes:
            raise ValueError("Invalid test principal/scopes")
        if any(s not in {"evidence:read", "ticket:create", "approval:grant"} for s in scopes):
            raise ValueError("Invalid test scope")
        if type(ttl_seconds) is not int or not 0 < ttl_seconds <= min(MAX_TTL, 300):
            raise ValueError("TTL outside test bounds")
        if type(now) not in (float, int) or not math.isfinite(now):
            raise ValueError("Invalid time")
        claims = {"aud": audience, "sub": actor, "scope": sorted(set(scopes)), "iat": now, "exp": now + ttl_seconds,
                  "jti": secrets.token_hex(8), "synthetic": True}
        body = b64(canonical(claims).encode("utf-8"))
        mac = b64(hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).digest())
        return body + "." + mac

    def _identity(self, credential, now):
        if not isinstance(credential, str) or len(credential) > 2048:
            raise AccessError("missing or malformed credential")
        try:
            payload, signature = credential.split(".", 1)
            expected = hmac.new(self._secret, payload.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, unb64(signature)):
                raise AccessError("credential signature invalid")
            claims = json.loads(unb64(payload))
            actor = claims["sub"]
            if (claims.get("aud") != AUDIENCE or claims.get("synthetic") is not True or
                actor not in PRINCIPALS or type(claims.get("iat")) not in (int, float) or
                type(claims.get("exp")) not in (int, float) or claims["iat"] > now or
                claims["exp"] <= now or claims["exp"] - claims["iat"] > MAX_TTL or
                not isinstance(claims.get("scope"), list) or
                any(s not in {"evidence:read", "ticket:create", "approval:grant"} for s in claims["scope"])):
                raise AccessError("credential expired or invalid audience/claims")
            return actor, set(claims["scope"])
        except (TypeError, ValueError, KeyError, UnicodeError, OverflowError, binascii.Error) as exc:
            raise AccessError("invalid credential") from None

    def _log(self, actor, tool, decision, approval_id=None, result=None, request_hash=None):
        self._sequence += 1
        self._audit.append({"seq": self._sequence, "synthetic": True, "actor": actor, "tool": tool,
                            "authorization_decision": decision, "approval_id": approval_id,
                            "request_sha256": request_hash, "result": result})

    @staticmethod
    def _validate(tool, args):
        if not isinstance(args, dict):
            raise AccessError("tool arguments must be an object")
        if tool == "evidence.read":
            if set(args) != {"evidence_id"} or args["evidence_id"] not in FIXTURES:
                raise AccessError("evidence access outside allowlist")
        elif tool == "ticket.create":
            if set(args) != {"request_id", "finding_id", "summary"}:
                raise AccessError("exact ticket schema required")
            if (not isinstance(args["request_id"], str) or
                not args["request_id"].startswith("REQ-") or len(args["request_id"]) > 50 or
                args["finding_id"] not in FIXTURES or
                not isinstance(args["summary"], str) or
                not 1 <= len(args["summary"]) <= 120):
                raise AccessError("ticket content outside fixture policy")
        else:
            raise AccessError("tool not in server policy")

    def request_hash(self, actor, tool, args):
        self._validate(tool, args)
        return digest({"actor": actor, "tool": tool, "arguments": args})

    def approve(self, approver_credential, actor, tool, args, now=None, ttl_seconds=60):
        """Offline human-simulator action. Strict maker-checker; not MCP-exposed."""
        now = time.time() if now is None else now
        with self._lock:
            who, scopes = self._identity(approver_credential, now)
            if PRINCIPALS[who] != "approver" or who == actor or "approval:grant" not in scopes:
                raise AccessError("independent approver identity required")
            if tool != "ticket.create" or actor not in PRINCIPALS or PRINCIPALS[actor] != "executor":
                raise AccessError("approval may cover only permitted high-impact tool")
            h = self.request_hash(actor, tool, args)
            if type(ttl_seconds) is not int or not 0 < ttl_seconds <= 300:
                raise AccessError("approval expiry invalid")
            ident = "APP-" + secrets.token_hex(6)
            self._approvals[ident] = {"actor": actor, "approver": who, "tool": tool,
                                      "request_sha256": h, "expires": now + ttl_seconds, "used": False}
            self._log(who, tool, "APPROVED_OUT_OF_BAND", ident, "recorded", h)
            return ident

    def call_tool(self, tool, args, credential, approval_id=None, now=None):
        now = time.time() if now is None else now
        with self._lock:
            actor = "unauthenticated"
            h = None
            try:
                actor, scopes = self._identity(credential, now)
                policy = TOOL_PERMISSIONS.get(tool)
                if policy is None or PRINCIPALS[actor] not in policy["roles"] or policy["scope"] not in scopes:
                    raise AccessError("server-side tool permission denied")
                self._validate(tool, args)
                h = self.request_hash(actor, tool, args)
                if policy["approval"]:
                    approval = self._approvals.get(approval_id) if isinstance(approval_id, str) else None
                    if (not approval or approval["actor"] != actor or approval["tool"] != tool or
                        approval["request_sha256"] != h or approval["expires"] <= now or approval["used"]):
                        raise AccessError("valid unused exact-request human approval required")
                    approval["used"] = True  # consumed before side effect under lock
                    rid = args["request_id"]
                    if rid in self._tickets:
                        raise AccessError("request id already executed")
                    self._tickets[rid] = {"id": "TICKET-" + rid, "finding_id": args["finding_id"],
                                          "summary": args["summary"], "synthetic": True}
                    result = deepcopy(self._tickets[rid])
                else:
                    result = deepcopy(FIXTURES[args["evidence_id"]])
                self._log(actor, tool, "ALLOW", approval_id if policy["approval"] else None, "SUCCESS", h)
                return result
            except AccessError as exc:
                self._log(actor, str(tool)[:80], "DENY", approval_id if isinstance(approval_id,str) else None,
                          str(exc), h)
                raise

    def audit(self):
        return deepcopy(self._audit)

    def tickets(self):
        return deepcopy(self._tickets)

    def handle_jsonrpc(self, request, now=None):
        """STDIO MCP subset: initialize, tools/list, tools/call, ping; no network."""
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
        ident = request.get("id")
        method = request.get("method")
        if ident is None:  # Client notifications, including notifications/initialized.
            return None
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": ident, "result": {"protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}}, "serverInfo": {"name": "defensive-local-fixture", "version": "1.0.0"}}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": ident, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": ident, "result": {"tools": [
                {"name": "evidence.read", "description": "Read one fictional security item",
                 "inputSchema": {"type": "object", "properties": {"evidence_id": {"type": "string"}}, "required": ["evidence_id"], "additionalProperties": False}},
                {"name": "ticket.create", "description": "Add a fictional ticket only with external, exact-request human approval",
                 "inputSchema": {"type": "object", "properties": {"request_id": {"type": "string"},
                        "finding_id": {"type": "string"}, "summary": {"type": "string"}},
                        "required": ["request_id", "finding_id", "summary"], "additionalProperties": False}}
            ]}}
        if method == "tools/call":
            params = request.get("params", {})
            if not isinstance(params, dict):
                params = {}
            meta = params.get("_meta", {})
            if not isinstance(meta, dict):
                meta = {}
            # Credentials in fixture-only metadata. Never record, echo or persist them.
            try:
                output = self.call_tool(params.get("name"), params.get("arguments", {}),
                    meta.get("lab_credential"), meta.get("lab_approval_id"), now=now)
                return {"jsonrpc": "2.0", "id": ident, "result": {"content": [{"type": "text", "text":canonical(output)}], "isError": False}}
            except AccessError as exc:
                return {"jsonrpc": "2.0", "id": ident, "result": {"content": [{"type": "text", "text":str(exc)}], "isError": True}}
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "Method not found"}}


def demonstration():
    lab = MCPIdentityLab()
    analyst = lab.issue_credential("lab-requester", ["evidence:read"], now=100)
    executor = lab.issue_credential("lab-executor", ["ticket:create"], now=100)
    approver = lab.issue_credential("lab-approver", ["approval:grant"], now=100)
    args = {"request_id": "REQ-001", "finding_id": "SEC-001", "summary": "Review synthetic alert"}
    observations = {}
    def outcome(name, fn):
        try:
            observations[name] = {"outcome": "ALLOW", "response": fn()}
        except AccessError as exc:
            observations[name] = {"outcome": "DENY", "reason": str(exc)}
    outcome("allowed_read", lambda:lab.call_tool("evidence.read", {"evidence_id":"SEC-001"}, analyst, now=101))
    outcome("denied_wrong_role", lambda:lab.call_tool("ticket.create", args, analyst, now=102))
    outcome("expired_credential", lambda:lab.call_tool("ticket.create", args, executor, now=161))
    outcome("unapproved", lambda:lab.call_tool("ticket.create", args, executor, now=103))
    approval_id = lab.approve(approver, "lab-executor", "ticket.create", args, now=104)
    outcome("approved", lambda:lab.call_tool("ticket.create", args, executor, approval_id, now=105))
    outcome("replayed_approval", lambda:lab.call_tool("ticket.create", args, executor, approval_id, now=106))
    return {"synthetic": True, "transport": "local stdio JSON-RPC / MCP tools", "observations": observations,
            "audit": lab.audit(), "tickets": lab.tickets(),
            "limitations": "Fixture identities and self-attested human approval; not OAuth, real IdP or production authorization"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stdio", action="store_true", help="Run MCP server over local stdio")
    p.add_argument("--output", type=Path, default=None, help="Export harmless deterministic scenario audit")
    args = p.parse_args()
    if args.stdio:
        lab = MCPIdentityLab()
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = lab.handle_jsonrpc(request)
                if response is not None:
                    sys.stdout.write(canonical(response) + "\n")
                    sys.stdout.flush()
            except (json.JSONDecodeError, UnicodeError):
                sys.stdout.write(canonical({"jsonrpc":"2.0", "id":None,
                    "error":{"code":-32700,"message":"Parse error"}}) + "\n")
                sys.stdout.flush()
        return
    report = demonstration()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered)


if __name__ == "__main__":
    main()
