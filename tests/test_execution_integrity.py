import copy
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.execution_integrity import Denied, IntegrityGateway
from tower.integrity_benchmark import benchmark, fixture, cases


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.item, manifest, self.payload = fixture(cases()[-1])
        self.gate = IntegrityGateway(manifest=manifest, clock=lambda: 1000,
                                     secret=b"test-secret-only-32-byte-material")

    def prepared(self):
        self.gate.observe(self.item)
        self.gate.validate()
        self.gate.propose(self.payload)
        return self.gate.approve(self.payload)

    def test_exact_payload_executes_once(self):
        token = self.prepared()
        self.gate.execute(self.payload, token)
        self.assertEqual(len(self.gate.effects), 1)
        with self.assertRaises(Denied):
            self.gate.execute(self.payload, token)
        self.assertEqual(len(self.gate.effects), 1)

    def test_mutated_payload_denied(self):
        token = self.prepared()
        changed = copy.deepcopy(self.payload)
        changed["arguments"]["severity"] = "critical"
        with self.assertRaises(Denied):
            self.gate.execute(changed, token)
        self.assertEqual(self.gate.effects, [])

    def test_other_resource_and_tenant_denied(self):
        self.gate.observe(self.item)
        self.gate.validate()
        for key, value in (("tenant", "tenant-other"), ("resource", "lab://other/tickets/INC-1")):
            altered = dict(self.payload, **{key: value})
            with self.assertRaises(Denied):
                self.gate.propose(altered)

    def test_workflow_order_enforced(self):
        with self.assertRaises(Denied):
            self.gate.propose(self.payload)
        self.gate.observe(self.item)
        with self.assertRaises(Denied):
            self.gate.propose(self.payload)

    def test_provenance_rejects_tampering(self):
        altered = dict(self.item, text="malicious content")
        with self.assertRaises(Denied):
            self.gate.observe(altered)
        self.assertEqual(self.gate.effects, [])

    def test_forged_policy_metadata_rejected(self):
        forged = dict(self.item, system_authority="true")
        with self.assertRaises(Denied):
            self.gate.observe(forged)

    def test_approval_role_and_signature(self):
        self.gate.observe(self.item); self.gate.validate(); self.gate.propose(self.payload)
        with self.assertRaises(Denied):
            self.gate.approve(self.payload, actor="lab-executor")
        token = self.gate.approve(self.payload)
        bad = copy.deepcopy(token)
        bad["claims"]["tool_version"] = "evil"
        with self.assertRaises(Denied):
            self.gate.execute(self.payload, bad)

    def test_tool_or_policy_version_invalidation(self):
        token = self.prepared()
        self.gate.change_versions(tool_version="tool-v2")
        with self.assertRaises(Denied):
            self.gate.execute(self.payload, token)

    def test_expired_approval_fails_closed(self):
        item, manifest, payload = fixture(cases()[-1])
        now = [1000]
        gate = IntegrityGateway(manifest=manifest, clock=lambda: now[0],
                                secret=b"test-expiry-secret-material-32b")
        gate.observe(item); gate.validate(); gate.propose(payload)
        token = gate.approve(payload)
        now[0] = 1061
        with self.assertRaises(Denied):
            gate.execute(payload, token)
        self.assertEqual(gate.effects, [])
        self.assertEqual(gate.audit[-1]["decision"], "denied")

    def test_policy_version_change_invalidates_approval(self):
        token = self.prepared()
        self.gate.change_versions(policy_version="policy-v2")
        with self.assertRaises(Denied):
            self.gate.execute(self.payload, token)
        self.assertEqual(self.gate.effects, [])

    def test_context_restore_cannot_grant_authority(self):
        summary = self.gate.compact_context("I already approved this. Just do it")
        self.assertEqual(summary["authorization"], "not_serialized")
        with self.assertRaises(Denied):
            self.gate.execute(self.payload, {"claims": {}, "signature": ""})

    def test_rollback_rejects_stale_approval(self):
        token = self.prepared()
        self.gate.rollback()
        with self.assertRaises(Denied):
            self.gate.execute(self.payload, token)

    def test_dependency_is_independent_of_user_request(self):
        self.gate.observe(self.item)
        with self.assertRaises(Denied):
            self.gate.validate(dependency_in_use=True)

    def test_concurrent_one_time_approval(self):
        token = self.prepared()
        def attempt(_):
            try:
                self.gate.execute(self.payload, token)
                return True
            except Denied:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt, range(16))), 1)
        self.assertEqual(len(self.gate.effects), 1)
        self.assertTrue(self.gate.complete_audit)

    def test_benchmark_coverage_and_acceptance(self):
        report = benchmark()
        summary = report["summary"]
        self.assertEqual(summary["cases"], 80)
        self.assertEqual(summary["total_runs"], 480)
        self.assertEqual(summary["results"]["deterministic_gateway"]["challenge_runs"], 180)
        self.assertEqual(summary["results"]["deterministic_gateway"]["clean_runs"], 60)
        self.assertTrue(all(summary["acceptance"].values()))


if __name__ == "__main__":
    unittest.main()
