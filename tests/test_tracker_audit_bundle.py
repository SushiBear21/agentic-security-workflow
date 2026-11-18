import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tracker.audit_bundle import INPUT_FILES, REPOSITORY, sha, verify_bundle
from tracker.release import ISSUES, decision


class AuditBundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.artifact = Path(temp.name) / "fixture.zip"
        self.image = "sha256:" + "1" * 64
        self.source = {
            "repository": REPOSITORY, "checkout_sha": "2" * 40, "pull_request": 13,
            "artifact_created_at": "2026-11-18T06:14:08Z",
        }
        self.scan = {"status": "pass", "image_id": self.image, "blocking_findings": 0,
                     "scanned_at": "2026-11-18T06:13:55+00:00"}
        self.inputs = {
            "scan": {"CreatedAt": self.scan["scanned_at"], "Metadata": {"ImageID": self.image},
                     "ArtifactType": "container_image", "Results": [{"Class": "os-pkgs"}]},
            "sbom": {"bomFormat": "CycloneDX", "components": [{"name": "synthetic"}]},
            "browser": {"passed": True, "checks": ["submit", "review", "download"]},
            "baseline": {"passed": True, "checks": ["authentication"]},
            "candidate": {"passed": False},
            "recovery": {"passed": True, "preserved_baseline": True},
        }

    def package(self, *, receipt_updates=None, changed_file=None):
        raw = {key: json.dumps(data).encode() for key, data in self.inputs.items()}
        receipt = {
            "repository": REPOSITORY, "commit": self.source["checkout_sha"], "pull_request": 13,
            "issues": ISSUES, "image_id": self.image, "scan": self.scan,
            "browser_acceptance": True, "rehearsal_passed": True, "promotion_authorized": False,
            "inputs_sha256": {key: sha(value) for key, value in raw.items()},
            "phases": {stage: decision(self.scan, self.inputs[stage], self.inputs["sbom"])
                       for stage in ("baseline", "candidate", "recovery")},
        }
        receipt.update(receipt_updates or {})
        if changed_file:
            raw[changed_file] = b'{"passed":true}'
        with ZipFile(self.artifact, "w") as bundle:
            for key, value in raw.items():
                bundle.writestr(INPUT_FILES[key], value)
            bundle.writestr("tracker-release.json", json.dumps(receipt))
        self.source["artifact_sha256"] = "sha256:" + sha(self.artifact.read_bytes())

    def test_original_reperforms_and_modified_artifact_is_rejected(self):
        self.package()
        result = verify_bundle(self.artifact, self.source)
        self.assertEqual(result["phase_outcomes"]["candidate"], "blocked")
        self.assertFalse(result["promotion_authorized"])
        self.artifact.write_bytes(self.artifact.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "Artifact digest mismatch"):
            verify_bundle(self.artifact, self.source)

    def test_inner_change_and_promotion_claim_are_rejected(self):
        self.package(changed_file="candidate")
        with self.assertRaisesRegex(ValueError, "Input digest mismatch"):
            verify_bundle(self.artifact, self.source)
        self.package(receipt_updates={"promotion_authorized": True})
        with self.assertRaisesRegex(ValueError, "Unexpected release promotion claim"):
            verify_bundle(self.artifact, self.source)

    def test_stale_scan_and_missing_preservation_are_rejected(self):
        self.package()
        self.source["artifact_created_at"] = "2026-11-20T06:14:08Z"
        with self.assertRaisesRegex(ValueError, "Historical image scan did not reperform"):
            verify_bundle(self.artifact, self.source)
        self.source["artifact_created_at"] = "2026-11-18T06:14:08Z"
        self.inputs["recovery"]["preserved_baseline"] = False
        self.package()
        with self.assertRaisesRegex(ValueError, "Recovery did not preserve"):
            verify_bundle(self.artifact, self.source)
