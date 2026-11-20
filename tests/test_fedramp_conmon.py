import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tower.fedramp_conmon import FIXTURE, OUTPUTS, analyze, build, verify


class ConMonTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_bytes())
        self.as_of = date(2026, 11, 20)

    def test_monthly_metrics_and_sla_boundaries(self):
        report, poam, mapping, evidence = analyze(self.fixture, self.as_of)
        metrics = report["metrics"]
        for key, expected in {
            "findings_total": 5, "open": 3, "overdue_open": 1, "late_closure": 1,
            "new_this_month": 4, "closed_this_month": 2, "assets_total": 3,
            "assets_with_current_fixture_observation": 1,
            "assets_with_stale_fixture_observation": 1,
            "assets_without_fixture_observation": 1,
            "control_mappings_with_all_sources": 6,
        }.items():
            self.assertEqual(metrics[key], expected, key)
        rows = {item["id"]: item for item in poam["items"]}
        self.assertEqual(rows["SYN-001"]["overdue_days"], 4)
        self.assertEqual(rows["SYN-002"]["due"], self.as_of.isoformat())
        self.assertFalse(rows["SYN-002"]["overdue"])
        self.assertEqual(rows["SYN-003"]["days_to_close"], 34)
        self.assertTrue(rows["SYN-003"]["late_closure"])
        self.assertFalse(rows["SYN-004"]["late_closure"])
        audit = next(row for row in mapping["controls"] if row["control"] == "AU-2")
        self.assertEqual(audit["synthetic_aws_observations"], {"logging": "unverified"})
        self.assertTrue(evidence["synthetic"])

    def test_scope_and_temporal_validation(self):
        cases = (
            ("synthetic", False, "synthetic fixture"),
            ("cloud_provider", "Azure", "AWS-only"),
            ("period", "2026-10", "as-of month"),
            ("aws_observations", {"logging": "verified"}, "observation set"),
        )
        for field, value, message in cases:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                analyze({**self.fixture, field: value}, self.as_of)
        self.fixture["findings"][0]["discovered"] = "2026-11-21"
        with self.assertRaisesRegex(ValueError, "Future finding"):
            analyze(self.fixture, self.as_of)

    def test_missing_sources_stay_visible(self):
        with tempfile.TemporaryDirectory() as empty:
            report, _, mapping, _ = analyze(self.fixture, self.as_of, root=empty)
        self.assertEqual(report["metrics"]["control_mappings_with_all_sources"], 0)
        self.assertTrue(all(row["status"] == "missing_source_evidence" for row in mapping["controls"]))

    def test_bundle_is_deterministic_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, second = (Path(temporary) / name for name in ("first", "second"))
            first_manifest = build(first, self.as_of.isoformat())
            self.assertEqual(first_manifest, build(second, self.as_of.isoformat()))
            self.assertEqual(set(first_manifest["files"]), set(OUTPUTS))
            self.assertTrue(verify(first))
            ssp = json.loads((first / "ssp.json").read_bytes())
            self.assertTrue(ssp["synthetic"])
            self.assertEqual(ssp["remediation_register"], "poam.json")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                build(first, self.as_of.isoformat())
            (first / "unexpected.txt").touch()
            with self.assertRaisesRegex(ValueError, "Unexpected"):
                verify(first)
            (first / "unexpected.txt").unlink()
            (first / "dashboard.html").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                verify(first)


if __name__ == "__main__":
    unittest.main()
