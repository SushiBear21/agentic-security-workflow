"""Deterministic, synthetic-only agent action gate; no model holds approval authority.

This companion reuses the existing digest convention from app.workflow. It does not
replace production IAM, host sandboxing, or the legacy local-ticket demo.
"""
import hashlib
import hmac
import json
import secrets
import threading
import time
from copy import deepcopy

from app.workflow import digest


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


class Denied(ValueError):
    pass


class IntegrityGateway:
    """One-run authority boundary. Never accept model assertions as approval.

    The host owns the trust manifest, signing key, role map, policy/tool versions,
    nonce ledger and execution state. Context restoration cannot write these.
    """
    TOOL = "update_ticket"
    APPROVER = "lab-approver"
    EXECUTOR = "lab-executor"

    def __init__(self, *, manifest, policy_version="policy-v1", tool_version="tool-v1",
                 tenant="tenant-alpha", secret=None, clock=None, ttl=60):
        self.manifest = deepcopy(manifest)
        self.policy_version = policy_version
        self.tool_version = tool_version
        self.tenant = tenant
        self._key = secret if secret is not None else secrets.token_bytes(32)
        if not isinstance(self._key, bytes) or len(self._key) < 16:
            raise ValueError("host signing key must have at least 128 bits")
        self.clock = clock or time.time
        self.ttl = ttl
        self._lock = threading.RLock()
        self._phase = "INIT"
        self._evidence = None
        self._proposal = None
        self._generation = 0
        self._issued = {}
        self._consumed = set()
        self._effects = []
        self.audit = []

    def _record(self, operation, decision, *, actor="host", reason="", payload=None):
        row = {"seq": len(self.audit), "operation": operation, "decision": decision,
               "actor": actor, "reason": reason, "policy_version": self.policy_version,
               "tool_version": self.tool_version, "generation": self._generation,
               "payload_sha256": digest(payload) if payload is not None else None}
        self.audit.append(row)

    def _guard(self, operation, fn, *, actor="host", payload=None):
        with self._lock:
            try:
                value = fn()
            except (Denied, TypeError, KeyError, ValueError, OverflowError) as exc:
                self._record(operation, "denied", actor=actor, reason=str(exc), payload=payload)
                raise Denied(str(exc)) from exc
            self._record(operation, "allowed", actor=actor, payload=payload)
            return value

    def observe(self, item):
        """Validate content and identity against HOST-SUPPLIED ingest manifest."""
        def action():
            if self._phase != "INIT":
                raise Denied("evidence already observed")
            if not isinstance(item, dict) or set(item) != {"document_id", "uri", "audience", "text"}:
                raise Denied("exact evidence schema required")
            trusted = self.manifest.get(item["document_id"])
            if not isinstance(trusted, dict):
                raise Denied("source missing from trusted manifest")
            if (item["uri"] != trusted.get("uri") or item["audience"] != trusted.get("audience")
                    or digest(item["text"]) != trusted.get("content_sha256")):
                raise Denied("evidence provenance does not match trusted manifest")
            self._evidence = {"document_id": item["document_id"],
                              "content_sha256": digest(item["text"]), "authority": "evidence_only"}
            self._phase = "OBSERVED"
            return deepcopy(self._evidence)
        return self._guard("observe", action, payload=item)

    def validate(self, *, dependency_in_use=False):
        def action():
            if self._phase != "OBSERVED":
                raise Denied("evidence must be observed before validation")
            if dependency_in_use:
                raise Denied("target has active dependency")
            self._phase = "VALIDATED"
        return self._guard("validate", action)

    def _check_payload(self, payload):
        if not isinstance(payload, dict) or set(payload) != {"tool", "resource", "tenant", "arguments"}:
            raise Denied("exact action payload schema required")
        if (payload["tool"] != self.TOOL or payload["tenant"] != self.tenant or
                not isinstance(payload["resource"], str) or
                not payload["resource"].startswith(f"lab://{self.tenant}/tickets/") or
                not payload["resource"].split("/")[-1].startswith("INC-")):
            raise Denied("tool, tenant or resource outside host scope")
        if not isinstance(payload["arguments"], dict) or set(payload["arguments"]) != {"severity"}:
            raise Denied("exact tool arguments required")
        if payload["arguments"]["severity"] not in {"medium", "critical"}:
            raise Denied("invalid severity")

    def propose(self, payload):
        def action():
            if self._phase != "VALIDATED":
                raise Denied("validation must precede proposal")
            self._check_payload(payload)
            self._proposal = deepcopy(payload)
            self._phase = "PROPOSED"
            return digest(payload)
        return self._guard("propose", action, payload=payload)

    def approve(self, payload, *, actor=APPROVER):
        """Trusted out-of-band approver issues HMAC-bound, single-use approval."""
        def action():
            if actor != self.APPROVER or self._phase != "PROPOSED":
                raise Denied("independent approval of a proposed action required")
            self._check_payload(payload)
            if payload != self._proposal:
                raise Denied("proposed payload mismatch")
            nonce = secrets.token_hex(16)
            claims = {"nonce": nonce, "action_sha256": digest(payload),
                      "evidence": deepcopy(self._evidence), "policy_version": self.policy_version,
                      "tool_version": self.tool_version, "tenant": self.tenant,
                      "actor": self.EXECUTOR, "generation": self._generation,
                      "issued_at": self.clock(), "expires_at": self.clock() + self.ttl}
            signature = hmac.new(self._key, canonical(claims), hashlib.sha256).hexdigest()
            self._issued[nonce] = digest(claims)
            self._phase = "APPROVED"
            return {"claims": claims, "signature": signature}
        return self._guard("approve", action, actor=actor, payload=payload)

    def execute(self, payload, approval, *, actor=EXECUTOR):
        """Atomic one-shot decision + local mock effect. No production side effects."""
        def action():
            self._check_payload(payload)
            if actor != self.EXECUTOR or self._phase != "APPROVED":
                raise Denied("approved execution phase and executor role required")
            if not isinstance(approval, dict) or set(approval) != {"claims", "signature"}:
                raise Denied("malformed approval")
            claims = approval["claims"]
            if not isinstance(claims, dict) or not isinstance(approval["signature"], str):
                raise Denied("malformed approval claims")
            expected = hmac.new(self._key, canonical(claims), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, approval["signature"]):
                raise Denied("approval signature mismatch")
            nonce = claims.get("nonce")
            if (not isinstance(nonce, str) or nonce not in self._issued
                    or nonce in self._consumed or digest(claims) != self._issued[nonce]):
                raise Denied("approval missing, consumed or replayed")
            if (claims.get("policy_version") != self.policy_version or
                    claims.get("tool_version") != self.tool_version or
                    claims.get("tenant") != self.tenant or claims.get("actor") != actor or
                    claims.get("generation") != self._generation or
                    claims.get("action_sha256") != digest(payload) or
                    claims.get("evidence") != self._evidence):
                raise Denied("approval context or exact payload mismatch")
            timestamp = self.clock()
            if (not isinstance(claims.get("issued_at"), (int, float)) or
                    not isinstance(claims.get("expires_at"), (int, float)) or
                    not claims["issued_at"] <= timestamp < claims["expires_at"]):
                raise Denied("approval expired or invalid")
            # Consume before the mock effect; any interruption must require a new approval.
            self._consumed.add(nonce)
            self._phase = "EXECUTED"
            effect = {"kind": "mock_ticket_update", "resource": payload["resource"],
                      "arguments": deepcopy(payload["arguments"]), "authorized": True,
                      "payload_sha256": digest(payload)}
            self._effects.append(effect)
            return deepcopy(effect)
        return self._guard("execute", action, actor=actor, payload=payload)

    def compact_context(self, untrusted_summary):
        """Context may be restored for the model, but never grants authority."""
        if not isinstance(untrusted_summary, str) or len(untrusted_summary) > 2048:
            raise Denied("invalid context summary")
        self._record("compact_context", "allowed")
        return {"summary": untrusted_summary, "authorization": "not_serialized"}

    def rollback(self):
        """Invalidate all outstanding approvals; do not roll back replay ledger."""
        with self._lock:
            self._generation += 1
            self._phase = "INIT"
            self._evidence = None
            self._proposal = None
            self._record("rollback", "allowed")

    def change_versions(self, *, policy_version=None, tool_version=None):
        with self._lock:
            if policy_version is not None:
                self.policy_version = policy_version
            if tool_version is not None:
                self.tool_version = tool_version
            self._record("version_change", "allowed")

    @property
    def effects(self):
        return deepcopy(self._effects)

    @property
    def complete_audit(self):
        return all(row["seq"] == i and row["decision"] in {"allowed", "denied"}
                   and row["policy_version"] and row["tool_version"]
                   for i, row in enumerate(self.audit))
