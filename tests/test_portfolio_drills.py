import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from app.workflow import digest
from tower.portfolio_drills import DEMO_TIME, assess_ksi, generate


class PortfolioDrillTests(unittest.TestCase):
    def test_evidence_from_guardrail_drift_to_retest_and_ai_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "evidence"
            records = generate(target)
            self.assertEqual({path.name for path in target.iterdir()}, set(records))
        landing = records["aws-landing-zone.json"]
        self.assertTrue(landing["attempt"]["explicit_deny"])
        self.assertFalse(landing["non_target_action_matched"])
        self.assertEqual(landing["drift"]["changed_keys"], ["archive_versioning"])
        self.assertTrue(landing["restored_matches_baseline"])

        decision = records["fedramp-decision-record.json"]
        states = {stage: [row["state"] for row in evidence["assessment"]["checks"]]
                  for stage, evidence in decision["evidence"].items()}
        self.assertEqual(states, {"baseline": ["pass", "pass"], "drift": ["fail", "pass"],
                                  "expired": ["fail", "fail"], "retest": ["pass", "pass"]})
        self.assertFalse(decision["authorization_granted"])

        incident = records["ai-model-incident.json"]
        self.assertTrue(incident["stable_route_verified"])
        self.assertFalse(incident["candidate_reenabled"])
        self.assertEqual(incident["live_model_calls"], 0)
        previous = None
        for event in incident["events"]:
            self.assertEqual(event["previous_sha256"], previous)
            previous = digest({key: value for key, value in event.items() if key != "sha256"})
            self.assertEqual(event["sha256"], previous)

    def test_future_and_missing_evidence_fail_closed(self):
        record = {"observed_at": (DEMO_TIME + timedelta(minutes=1)).isoformat(), "values": {}}
        checks = assess_ksi(record, DEMO_TIME)["checks"]
        self.assertTrue(all(check["state"] == "fail" for check in checks))
        self.assertTrue(all("stale_or_future_observation" in check["reasons"] for check in checks))
