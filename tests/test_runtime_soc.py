import json
import unittest

from tower.runtime_soc import (FIXTURES, MCP_PIN, collect, correlate, evaluate,
                               event, integrity_event, mcp_event, response)

REV = "a" * 40


class RuntimeSocTests(unittest.TestCase):
    def test_metrics(self):
        report = evaluate(REV)
        m = report["metrics"]
        self.assertEqual((m["tp"], m["fp"], m["fn"], m["tn"]), (6, 1, 2, 6))
        self.assertAlmostEqual(m["precision"], 6 / 7)
        self.assertAlmostEqual(m["recall"], 6 / 8)
        self.assertAlmostEqual(m["telemetry_coverage"], 14 / 15)
        self.assertEqual(m["missing"], ["LAB-0014"])
        self.assertEqual(m["rules_observed"], ["AI-01", "AI-02", "AI-03", "AI-04"])
        self.assertEqual(len(report["responses"]), 7)
        self.assertEqual(sum(r["mock_effect_count"] for r in report["responses"]), 6)

    def test_redaction_and_allowlist(self):
        sentinel = "NEVER-EXPORT-synthetic-secret"
        row = {"actor": sentinel, "authorization_decision": "DENY",
               "tool": sentinel, "result": sentinel, "credential_ref": sentinel,
               "approval_id": sentinel, "request_sha256": sentinel, "payload": sentinel}
        ev = mcp_event(1, row, 0)
        self.assertEqual(ev["role"], "unknown")
        self.assertEqual(ev["source_revision"], MCP_PIN)
        self.assertNotIn(sentinel, json.dumps(ev))
        other = integrity_event(2, {"actor": sentinel, "decision": "denied",
                                    "reason": sentinel, "payload_sha256": sentinel}, 0)
        self.assertNotIn(sentinel, json.dumps(other))
        self.assertNotIn(sentinel, json.dumps(collect(3, "egress", sentinel, REV)))
        for _, value, _, _ in FIXTURES:
            if len(value) > 20:
                self.assertNotIn(value, json.dumps(evaluate(REV)))
        with self.assertRaises(ValueError):
            event(1, "rag-fixture", sentinel, "prompt_policy", "deny", "clean", REV)

    def test_actual_mcp_boundary(self):
        for variant in ("wrong-role", "unknown-resource"):
            records = collect(1, "tool", variant, REV)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["decision"], "deny")
        self.assertEqual(collect(1, "tool", "read", REV)[0]["decision"], "allow")

    def test_duplicate_and_conflicting_delivery(self):
        records = collect(1, "prompt", "LAB_OVERRIDE: test", REV)
        self.assertEqual(correlate(records), correlate(records + records))
        conflict = dict(records[0], decision="allow")
        with self.assertRaises(ValueError):
            correlate(records + [conflict])

    def test_response_denial_and_simulated_maker_checker(self):
        record = {"case_id": "LAB-0001"}
        blocked = response(record)
        self.assertEqual(blocked["state"], "pending_approval")
        self.assertEqual(blocked["mock_effect_count"], 0)
        approved = response(record, approved=True)
        self.assertEqual(approved["state"], "closed")
        self.assertEqual(approved["approval_source"], "scripted_fixture_role")
        self.assertEqual(approved["mock_effect_count"], 1)
        self.assertIn("replay_denied", [r["stage"] for r in approved["timeline"]])
        self.assertEqual(approved["detection_to_response_seconds"], 5)

    def test_missing_receipt_is_not_true_negative(self):
        report = evaluate(REV)
        self.assertEqual(report["metrics"]["fn"], 2)
        self.assertNotIn("LAB-0014", [r["correlation_id"] for r in report["events"]])
