import concurrent.futures
import unittest
from tower.access_demo import AccessLab, verify_audit

class AccessExtensionTests(unittest.TestCase):
    def setUp(self):
        self.lab = AccessLab()
        self.request = self.lab.run("request", {"id": "scope", "action": "read_synthetic_evidence", "resource": "lab://evidence/SEC-001", "ttl_seconds": 60, "reason": "review"}, "lab-requester", 100)
        self.lab.run("approve", self.request, "lab-approver", 101)
    def test_revoke_prevents_execution(self):
        self.assertEqual(self.lab.run("revoke", self.request, "lab-approver", 102), "REVOKED")
        with self.assertRaises(ValueError): self.lab.run("execute", self.request, "lab-executor", 103)
        self.assertTrue(verify_audit(self.lab.snapshot()))
    def test_requester_cannot_revoke_or_expand_scope(self):
        with self.assertRaises(ValueError): self.lab.run("revoke", self.request, "lab-requester", 102)
        with self.assertRaises(ValueError): self.lab.run("execute", dict(self.request, resource="lab://other"), "lab-executor", 103)
    def test_concurrent_single_use(self):
        def execute(_):
            try: self.lab.run("execute", self.request, "lab-executor", 102); return True
            except ValueError: return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(execute, range(16))), 1)
        self.assertTrue(verify_audit(self.lab.snapshot()))
