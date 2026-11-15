import tempfile
import unittest
from pathlib import Path
from tower.assurance import assess, REQUIRED_GATES
from tower.readiness_package import digest

class AssuranceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "evidence.txt").write_text("synthetic test evidence")
        self.package = {"schema_version": 1, "synthetic": True,
            "model_risk": dict(intended_use="advisory drafting", failure_impact="bad recommendation", owner="lab", boundary="no cloud actions"),
            "evidence": {"evidence.txt": digest(self.root / "evidence.txt")},
            "gates": {g: {"status": "pass", "evidence": ["evidence.txt"]} for g in REQUIRED_GATES}, "exceptions": []}
    def test_all_pass_only_allows_lab_review(self):
        r = assess(self.package, self.root, 100)
        self.assertEqual(r["status"], "eligible_for_lab_review")
        self.assertFalse(r["production_authorized"])
    def test_quality_failure_cannot_be_waived(self):
        self.package["gates"]["human_quality"]["status"] = "fail"
        self.assertEqual(assess(self.package, self.root, 100)["blocking_gates"], ["human_quality"])
        self.package["exceptions"] = [dict(gate="human_quality", owner="lab", rationale="deadline", expires_at=200)]
        with self.assertRaises(ValueError): assess(self.package, self.root, 100)
    def test_missing_measurement_blocks(self):
        self.package["gates"]["dependency_scan"]["status"] = "unmeasured"
        self.assertEqual(assess(self.package, self.root, 100)["status"], "blocked")
    def test_scoped_exception_and_expiry(self):
        self.package["gates"]["dependency_scan"]["status"] = "unmeasured"
        self.package["exceptions"] = [dict(gate="dependency_scan", owner="lab", rationale="offline rehearsal only", expires_at=200)]
        self.assertEqual(assess(self.package, self.root, 100)["status"], "eligible_for_lab_review")
        with self.assertRaises(ValueError): assess(self.package, self.root, 200)
    def test_tamper_and_path_escape_rejected(self):
        (self.root / "evidence.txt").write_text("changed")
        with self.assertRaises(ValueError): assess(self.package, self.root, 100)
        self.package["evidence"] = {"../escape": "0" * 64}
        with self.assertRaises(ValueError): assess(self.package, self.root, 100)
    def test_gate_cannot_omit_evidence(self):
        self.package["gates"]["rollback"]["evidence"] = []
        with self.assertRaises(ValueError): assess(self.package, self.root, 100)
