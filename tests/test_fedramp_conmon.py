import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

from tower.fedramp_conmon import FIXTURE, OUTPUTS, analyze, build, canonical, verify


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

    def test_si2_retest_links_distinct_observations_in_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            build(output, self.as_of.isoformat())
            self.assertTrue(verify(output))
            poam = json.loads((output / "poam.json").read_bytes())
            index = json.loads((output / "evidence-index.json").read_bytes())

        finding = next(row for row in poam["items"] if row["id"] == "SYN-003")
        links = finding["retest_evidence_ids"]
        self.assertEqual(links, {"before": "SYN-003-BEFORE", "after": "SYN-003-RETEST"})
        self.assertEqual(finding["closure_reference"], links["after"])
        self.assertEqual(set(index["remediation_retests"]), set(links.values()))
        for stage, wanted in (("before", "fail"), ("after", "pass")):
            record = index["remediation_retests"][links[stage]]
            self.assertEqual(record["id"], links[stage])
            self.assertEqual(record["finding_id"], finding["id"])
            self.assertEqual(record["asset_id"], finding["asset_id"])
            self.assertEqual(record["control"], "SI-2")
            self.assertEqual(record["stage"], stage)
            self.assertEqual(record["outcome"], wanted)
            self.assertTrue(record["synthetic"])
            self.assertTrue(record["expected"])
            self.assertIs(record["observed"], wanted == "pass")
            digest = record.pop("sha256")
            self.assertEqual(digest, hashlib.sha256(canonical(record).encode("utf-8")).hexdigest())
        self.assertEqual(poam["approval_status"], "not_reviewed")

    def test_si2_closure_rejects_invalid_retest(self):
        cases = (
            (lambda item: item.pop("retest"), "requires before/after"),
            (lambda item: item.update(closure_reference="SYN-003-BEFORE"), "reference the passing"),
            (lambda item: item["retest"]["after"].update(id="SYN-003-BEFORE"), "Distinct"),
            (lambda item: item["retest"]["after"].update(remediation_confirmed=False), "fail then pass"),
            (lambda item: item["retest"]["before"].update(remediation_confirmed=True), "fail then pass"),
            (lambda item: item["retest"]["after"].update(observed_at="2026-10-03T13:00:00Z"), "ordered"),
            (lambda item: item["retest"]["after"].update(observed_at="2026-11-07T14:00:00Z"), "ordered"),
            (lambda item: item["retest"]["before"].update(observed_at="2026-10-02T14:00:00Z"), "ordered"),
            (lambda item: item["retest"]["after"].update(observed_at="2026-11-06T14:00:00"), "UTC"),
        )
        for mutate, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                fixture = deepcopy(self.fixture)
                finding = next(row for row in fixture["findings"] if row["id"] == "SYN-003")
                mutate(finding)
                analyze(fixture, self.as_of)

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
