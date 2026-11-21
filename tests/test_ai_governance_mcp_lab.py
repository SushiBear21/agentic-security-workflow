"""Tests for local-only AI RMF and defensive MCP identity lab."""
import json
import tempfile
import unittest
from pathlib import Path
from tower.ai_governance_evidence import (MAPPING, RISK_REGISTER, SYSTEM_CARD, build,
    decision, evaluate_offline, monitoring, sha256_file)
from tower.mcp_identity_lab import AccessError, MCPIdentityLab, demonstration


class MCPIdentityTests(unittest.TestCase):
    def setUp(self):
        self.s = MCPIdentityLab(secret=b"x" * 32)
        self.writer = self.s.issue_credential("lab-executor", ["ticket:create"], now=100, ttl_seconds=60)
        self.reader = self.s.issue_credential("lab-requester", ["evidence:read"], now=100, ttl_seconds=60)
        self.approver = self.s.issue_credential("lab-approver", ["approval:grant"], now=100, ttl_seconds=60)
        self.args = {"request_id":"REQ-42","finding_id":"SEC-001","summary":"Review synthetic alert"}

    def test_allowed_read_and_denied_unknown_resource(self):
        self.assertTrue(self.s.call_tool("evidence.read", {"evidence_id":"SEC-001"}, self.reader, now=101)["synthetic"])
        with self.assertRaises(AccessError):
            self.s.call_tool("evidence.read", {"evidence_id":"UNLISTED"}, self.reader, now=101)

    def test_denied_wrong_role_and_scope(self):
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create", self.args, self.reader, now=101)
        with self.assertRaises(AccessError):
            self.s.call_tool("evidence.read", {"evidence_id":"SEC-001"}, self.writer, now=101)
        self.assertFalse(self.s.tickets())

    def test_expired_credential(self):
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create", self.args, self.writer, now=160)

    def test_unapproved_then_approved_then_replayed(self):
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create", self.args, self.writer, now=101)
        approval_id = self.s.approve(self.approver, "lab-executor", "ticket.create", self.args, now=102)
        self.assertTrue(self.s.call_tool("ticket.create", self.args, self.writer, approval_id, now=103)["synthetic"])
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create", self.args, self.writer, approval_id, now=104)
        self.assertEqual(len(self.s.tickets()),1)

    def test_exact_request_and_expired_approval(self):
        aid = self.s.approve(self.approver, "lab-executor", "ticket.create", self.args, now=101)
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create",dict(self.args,summary="changed"),self.writer,aid,now=102)
        self.assertFalse(self.s.tickets())
        self.s.call_tool("ticket.create",self.args,self.writer,aid,now=103)
        other_args = dict(self.args,request_id="REQ-43")
        short = self.s.approve(self.approver,"lab-executor","ticket.create",other_args,now=104,ttl_seconds=1)
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create",other_args,self.writer,short,now=105)

    def test_separation_of_duties(self):
        with self.assertRaises(AccessError):
            self.s.approve(self.reader,"lab-executor","ticket.create",self.args,now=101)
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create",self.args,self.approver,now=101)

    def test_wrong_audience_bad_signature_and_unknown_tool(self):
        wrong = self.s.issue_credential("lab-executor",["ticket:create"],now=100,audience="wrong")
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create",self.args,wrong,now=101)
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create",self.args,self.writer[:-3]+"AAA",now=101)
        with self.assertRaises(AccessError):
            self.s.call_tool("fs.delete",{},self.writer,now=101)

    def test_strict_schema_and_no_secret_in_audit(self):
        with self.assertRaises(AccessError):
            self.s.call_tool("ticket.create",dict(self.args,role="admin"),self.writer,now=101)
        self.s.call_tool("evidence.read",{"evidence_id":"SEC-001"},self.reader,now=101)
        audit=json.dumps(self.s.audit())
        for secret in (self.writer,self.reader,self.approver):
            self.assertNotIn(secret,audit)
        self.assertTrue(all("authorization_decision" in e and "result" in e for e in self.s.audit()))

    def test_stdio_mcp_methods(self):
        initial = self.s.handle_jsonrpc({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}},now=101)
        self.assertEqual(initial["result"]["serverInfo"]["name"],"defensive-local-fixture")
        tools = self.s.handle_jsonrpc({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}},now=101)
        self.assertEqual({t["name"] for t in tools["result"]["tools"]},{"evidence.read","ticket.create"})
        self.assertIsNone(self.s.handle_jsonrpc({"jsonrpc":"2.0","method":"notifications/initialized"},now=101))
        request={"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"evidence.read",
          "arguments":{"evidence_id":"SEC-001"},"_meta":{"lab_credential":self.reader}}}
        reply=self.s.handle_jsonrpc(request,now=101)
        self.assertFalse(reply["result"]["isError"])
        self.assertNotIn(self.reader,json.dumps(reply))
        request["params"]["_meta"]={}
        self.assertTrue(self.s.handle_jsonrpc(request,now=101)["result"]["isError"])


class GovernanceEvidenceTests(unittest.TestCase):
    def test_all_rmf_functions_and_fictional_owners(self):
        self.assertEqual({row["function"] for row in MAPPING},{"GOVERN","MAP","MEASURE","MANAGE"})
        self.assertTrue(SYSTEM_CARD["synthetic"])
        self.assertTrue(all(r["owner"].startswith("Fictional") for r in RISK_REGISTER))

    def test_fixture_results_not_bedrock_results(self):
        d=evaluate_offline(demonstration())
        self.assertEqual((d["passed"],d["total"]),(6,6))
        self.assertEqual(d["model_calls"],0)
        self.assertIn("NOT verified",d["reference_only"]["holdout_6_of_6"])

    def test_fail_closed_and_hypothetical_lab_only_go(self):
        gates={x:True for x in ("offline_tests","model_holdout","independent_review",
                                 "security_scan","monitoring_fresh","identity_audit")}
        evidence_hash="a"*64
        pending=decision(gates,[],[],evidence_sha256=evidence_hash)
        self.assertEqual(pending["release_status"],"NO_GO")
        approval={"decision":"approve","manifest_sha256":pending["manifest_sha256"],
                  "approver":"Fictional separate approver","evaluation_owner":"Fictional evaluation owner",
                  "independent_identity_verified":True}
        go=decision(gates,[],[],approval,evidence_sha256=evidence_hash)
        self.assertEqual(go["release_status"],"LAB_GO")
        self.assertFalse(go["production_authorized"])
        self.assertEqual(decision(gates,[],[],approval)["release_status"],"NO_GO")
        self.assertEqual(decision(gates,[],[],approval,evidence_sha256="b"*64)["release_status"],"NO_GO")
        self.assertEqual(decision(dict(gates,security_scan=False),[],[],approval,evidence_sha256=evidence_hash)["release_status"],"NO_GO")
        self.assertEqual(decision(gates,RISK_REGISTER,[],approval,evidence_sha256=evidence_hash)["release_status"],"NO_GO")
        self.assertEqual(decision(gates,[],monitoring()["alerts"],approval,evidence_sha256=evidence_hash)["release_status"],"NO_GO")
        self.assertEqual(decision(gates,[],[],dict(approval,manifest_sha256="tampered"),evidence_sha256=evidence_hash)["release_status"],"NO_GO")

    def test_generated_manifest_and_unknown_scans(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"packet"
            status=build(output)
            self.assertEqual((status["decision"],status["offline_tests"]),("NO_GO","6/6"))
            manifest=json.loads((output/"evidence_manifest.json").read_text())
            self.assertEqual(manifest["artifact_count"],10)
            for row in manifest["artifacts"]:
                self.assertEqual(sha256_file(output/row["file"]),row["sha256"])
            dec=json.loads((output/"release_decision.json").read_text())
            self.assertFalse(dec["production_authorized"])
            self.assertIn("security_scan",dec["failed_gates"])
            self.assertIn("independent_review",dec["failed_gates"])
            scan=json.loads((output/"scan_results.json").read_text())
            self.assertFalse(scan["scanner_executed"])
            self.assertIn("INDEPENDENT SYNTHETIC",(output/"MANAGEMENT_REPORT.md").read_text())
            with self.assertRaises(ValueError):
                build(output)


if __name__ == "__main__":
    unittest.main()
