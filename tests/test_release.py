import json
import tempfile
import unittest
from pathlib import Path
from tower.release import rehearse, backup

class ReleaseTests(unittest.TestCase):
    def test_rehearsal_preserves_blocked_quality_and_restores_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "release"
            decision = rehearse(out)
            self.assertEqual(decision["status"], "blocked")
            self.assertIn("human_quality", decision["blocking_gates"])
            self.assertIn("dependency_scan", decision["blocking_gates"])
            acceptance = json.loads((out / "acceptance.json").read_text())
            self.assertTrue(acceptance["rollback_state_equal"])
            self.assertEqual(acceptance["ticket_count"], 1)
            boundary = json.loads((out / "adversarial.json").read_text())
            self.assertEqual(boundary["passed"], 9)
            self.assertEqual(boundary["adversarial_boundary_failures"], 0)
            canary = json.loads((out / "canary.json").read_text())
            self.assertTrue(canary["rollback"])
            self.assertEqual([row["request"] for row in canary["requests"]
                              if row["route"] == "reference-candidate"], [0, 10])
            governance = json.loads((out / "governance.json").read_text())
            self.assertTrue(governance["monitoring"]["ready"])
            self.assertEqual(governance["release_status"], "blocked")
            adoption = json.loads((out / "adoption.json").read_text())
            self.assertEqual(adoption["workflow_rehearsal"]["review_count"], 1)
            self.assertAlmostEqual(adoption["model_cost_scenario"]["estimated_usd"], 0.006)
            with self.assertRaises(ValueError): rehearse(out)
    def test_backup_will_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "existing"; target.write_text("retain")
            with self.assertRaises(ValueError): backup(Path(tmp) / "missing", target)
            self.assertEqual(target.read_text(), "retain")
