import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tower.compliance import validate_plan, monitor
from tower.readiness_package import digest

ROOT = Path(__file__).resolve().parents[1]
class ComplianceTests(unittest.TestCase):
    def test_poam_covers_all_selected_controls(self):
        plan=json.loads((ROOT/"docs/portfolio/poam.json").read_text())
        controls=json.loads((ROOT/"docs/portfolio/readiness-controls.json").read_text())
        self.assertEqual(validate_plan(plan,controls)["open"],10)
        plan["items"].pop()
        with self.assertRaises(ValueError): validate_plan(plan,controls)
    def test_cannot_close_without_evidence(self):
        plan=json.loads((ROOT/"docs/portfolio/poam.json").read_text())
        controls=json.loads((ROOT/"docs/portfolio/readiness-controls.json").read_text())
        plan["items"][0]["status"]="closed"
        with self.assertRaises(ValueError): validate_plan(plan,controls)
    def test_missing_stale_tampered_future_and_failed_evidence(self):
        rules=[{"id":"scan","owner":"security","max_age_hours":24}]
        now=datetime(2026,11,15,12,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/"scan.json").write_text("{}")
            self.assertFalse(monitor(rules,{},root,now)["ready"])
            record={"path":"scan.json","sha256":digest(root/"scan.json"),"measured_at":"2026-11-15T11:00:00Z","outcome":"pass"}
            self.assertTrue(monitor(rules,{"scan":record},root,now)["ready"])
            for field,value,expected in [("sha256","wrong","invalid_integrity"),("measured_at","2026-11-13T11:00:00Z","stale"),("measured_at","2026-11-16T11:00:00Z","future_timestamp"),("outcome","fail","failed"),("path","../escape","invalid_evidence")]:
                changed=dict(record); changed[field]=value
                result=monitor(rules,{"scan":changed},root,now)
                self.assertEqual(result["results"][0]["status"],expected)
    def test_empty_monitoring_is_not_ready(self):
        self.assertFalse(monitor([],{},ROOT,datetime.now(timezone.utc))["ready"])
