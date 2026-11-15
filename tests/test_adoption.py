import copy
import json
import unittest
from pathlib import Path
from tower.adoption import measure

class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).parent / "fixtures/adoption-v1.json").read_text())
    def test_denominators_and_negative_savings(self):
        r = measure(self.data)
        self.assertAlmostEqual(r["activation_rate"], 2/3)
        self.assertAlmostEqual(r["completion_rate"], 2/3)
        self.assertEqual(r["retention_rate"], .5)
        self.assertEqual(r["draft_acceptance_rate"], .5)
        self.assertEqual(r["mean_seconds_saved"], 10)
        self.assertTrue(r["synthetic"])
    def test_no_data_is_unknown(self):
        self.data.update(eligible_users=[], prior_active_users=[], events=[], timing_pairs=[])
        r = measure(self.data)
        for k in ("activation_rate", "retention_rate", "completion_rate", "draft_acceptance_rate", "mean_seconds_saved"):
            self.assertIsNone(r[k])
    def test_invalid_event_rejected(self):
        for field, value in [("at", "2026-11-08T00:00:00Z"), ("at", "2026-11-02T10:00:00"), ("user_id", "outsider"), ("kind", "made_up")]:
            d = copy.deepcopy(self.data); d["events"][0][field] = value
            with self.assertRaises(ValueError): measure(d)
    def test_duplicate_event_and_nonfinite_duration_rejected(self):
        self.data["events"].append(self.data["events"][0])
        with self.assertRaises(ValueError): measure(self.data)
        self.data["events"].pop()
        self.data["timing_pairs"][0]["manual_seconds"] = float("nan")
        with self.assertRaises(ValueError): measure(self.data)
