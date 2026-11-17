import concurrent.futures
import unittest
from tower.access_demo import AccessLab, demo, verify_audit


class AccessLabTests(unittest.TestCase):
    def setUp(self):
        self.lab = AccessLab()
        self.args = {"id": "REQ-1", "action": "read_synthetic_evidence", "resource": "lab://evidence/SEC-001", "ttl_seconds": 60, "reason": "Lab review"}
        self.key = self.lab.run("request", self.args, "lab-requester", 100)

    def approve(self):
        self.lab.run("approve", self.key, "lab-approver", 101)

    def test_happy_path(self):
        self.approve()
        result = self.lab.run("execute", self.key, "lab-executor", 102)
        self.assertTrue(result["synthetic"])
        self.assertTrue(verify_audit(self.lab.snapshot()))

    def test_unapproved_denial_audited(self):
        with self.assertRaises(ValueError): self.lab.run("execute", self.key, "lab-executor", 101)
        self.assertEqual(self.lab.snapshot()["events"][-1]["kind"], "access_denied")

    def test_roles_cannot_self_approve_or_execute(self):
        for command, actor in [("approve", "lab-requester"), ("execute", "lab-requester"), ("execute", "lab-approver"), ("approve", "unknown")]:
            with self.assertRaises(ValueError): self.lab.run(command, self.key, actor, 101)

    def test_scope_rejected(self):
        for change in [{"action": "admin"}, {"resource": "*"}, {"resource": "lab://evidence/SEC-002"}, {"role": "approver"}]:
            with self.assertRaises(ValueError): self.lab.run("request", {**self.args, "id": "OTHER", **change}, "lab-requester", 101)

    def test_ttl_bounds(self):
        for ttl in [0, 301, -1, True, 1.5]:
            with self.assertRaises(ValueError): self.lab.run("request", {**self.args, "id": "OTHER", "ttl_seconds": ttl}, "lab-requester", 101)

    def test_expiry_and_time_regression(self):
        self.approve()
        for now in [99, 100, 160, 161]:
            with self.assertRaises(ValueError): self.lab.run("execute", self.key, "lab-executor", now)

    def test_wrong_digest(self):
        with self.assertRaises(ValueError): self.lab.run("approve", {**self.key, "sha256": "bad"}, "lab-approver", 101)
        self.assertEqual(self.lab.snapshot()["requests"]["REQ-1"]["state"], "PENDING")

    def test_mutation_after_approval(self):
        self.approve()
        self.lab._requests["REQ-1"]["payload"]["reason"] = "changed"
        with self.assertRaises(ValueError): self.lab.run("execute", self.key, "lab-executor", 102)

    def test_rejection_terminal(self):
        self.lab.run("reject", self.key, "lab-approver", 101)
        for command, actor in [("approve", "lab-approver"), ("execute", "lab-executor")]:
            with self.assertRaises(ValueError): self.lab.run(command, self.key, actor, 102)

    def test_replay_and_duplicate_id(self):
        self.approve()
        self.lab.run("execute", self.key, "lab-executor", 102)
        with self.assertRaises(ValueError): self.lab.run("execute", self.key, "lab-executor", 103)
        with self.assertRaises(ValueError): self.lab.run("request", self.args, "lab-requester", 104)

    def test_concurrent_single_process_execution(self):
        self.approve()
        def execute(_):
            try:
                self.lab.run("execute", self.key, "lab-executor", 102)
                return True
            except ValueError: return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(execute, range(8))), 1)

    def test_copies_do_not_mutate_state(self):
        self.args["reason"] = "mutated input"
        snap = self.lab.snapshot(); snap["requests"]["REQ-1"]["payload"]["reason"] = "mutated output"
        self.assertEqual(self.lab.snapshot()["requests"]["REQ-1"]["payload"]["reason"], "Lab review")

    def test_audit_detects_mutation(self):
        snap = self.lab.snapshot(); snap["events"][0]["actor"] = "changed"
        with self.assertRaises(ValueError): verify_audit(snap)

    def test_invalid_schema_and_command(self):
        for cmd, args in [("shell", self.key), ("approve", {**self.key, "extra": True}), ("approve", {"id": "missing", "sha256": "bad"})]:
            with self.assertRaises(ValueError): self.lab.run(cmd, args, "lab-approver", 101)

    def test_demo_outcomes(self):
        snap = demo()
        self.assertEqual(snap["requests"]["DEMO-001"]["state"], "EXECUTED")
        self.assertEqual(sum(e["kind"] == "access_denied" for e in snap["events"]), 2)
        self.assertTrue(verify_audit(snap))


if __name__ == "__main__": unittest.main()


class AuthenticatedAccessTests(unittest.TestCase):
    def test_verified_credentials_separate_duties_and_deny_execution_replay(self):
        from tower.access_demo import AuthenticatedAccess

        now = 100
        lab = AuthenticatedAccess(clock=lambda: now)
        requester = lab.issue("lab-requester")
        approver = lab.issue("lab-approver")
        executor = lab.issue("lab-executor")
        request = lab.run("request", {
            "id": "auth-test", "action": "read_synthetic_evidence",
            "resource": "lab://evidence/SEC-001", "ttl_seconds": 60, "reason": "Review",
        }, requester)
        for credential in ("lab-approver", requester):
            with self.assertRaises(ValueError):
                lab.run("approve", request, credential)
        lab.run("approve", request, approver)
        lab.run("execute", request, executor)
        with self.assertRaises(ValueError):
            lab.run("execute", request, executor)
        now += 300
        with self.assertRaises(ValueError):
            lab.run("execute", request, executor)
        self.assertEqual(lab.snapshot()["events"][-1]["actor"], "unauthenticated")
