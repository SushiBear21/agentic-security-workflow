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
            with self.assertRaises(ValueError): rehearse(out)
    def test_backup_will_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "existing"; target.write_text("retain")
            with self.assertRaises(ValueError): backup(Path(tmp) / "missing", target)
            self.assertEqual(target.read_text(), "retain")
