import json
import unittest
from datetime import datetime, timedelta, timezone

from tower.image_scan import evaluate


class ImageScanTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 17, tzinfo=timezone.utc)
        self.image_id = "sha256:" + "a" * 64
        self.report = {
            "CreatedAt": self.now.isoformat(),
            "ArtifactType": "container_image",
            "Metadata": {"ImageID": self.image_id},
            "Results": [{"Class": "os-pkgs"}, {"Class": "lang-pkgs"}],
        }

    def result(self):
        return evaluate(json.dumps(self.report), self.image_id, self.now)["status"]

    def test_matching_clean_scan_passes(self):
        self.assertEqual(self.result(), "pass")

    def test_other_image_fails(self):
        self.report["Metadata"]["ImageID"] = "sha256:" + "b" * 64
        self.assertEqual(self.result(), "fail")

    def test_stale_scan_fails(self):
        self.report["CreatedAt"] = (self.now - timedelta(hours=25)).isoformat()
        self.assertEqual(self.result(), "fail")

    def test_missing_language_coverage_fails(self):
        self.report["Results"].pop()
        self.assertEqual(self.result(), "fail")

    def test_critical_finding_fails(self):
        self.report["Results"][0]["Vulnerabilities"] = [{"Severity": "CRITICAL"}]
        self.assertEqual(self.result(), "fail")
