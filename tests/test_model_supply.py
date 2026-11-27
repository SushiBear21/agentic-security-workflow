import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tower.model_supply import FIXTURES, Rejected, digest, rehearse, verify_bundle

LOCK = b"boto3==1.43.119\nbotocore==1.43.119\njmespath==1.1.0\npython-dateutil==2.9.0.post0\ns3transfer==0.19.3\nsix==1.17.0\nurllib3==2.8.0\n"


class ModelSupplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "candidate"
        shutil.copytree(FIXTURES / "candidate", self.root)

    def verify(self, release="candidate", lock=LOCK):
        return verify_bundle(self.root, release, lock)

    def mutate(self, f):
        path = self.root / "manifest.json"
        data = json.loads(path.read_text())
        f(data)
        path.write_text(json.dumps(data))

    def test_clean(self):
        self.assertEqual(self.verify()["status"], "pass")
        self.assertEqual(len(self.verify()["dependency_components"]), 7)

    def test_tampered_model(self):
        (self.root / "model.txt").write_bytes(b"benign changed fixture")
        with self.assertRaisesRegex(Rejected, "artifact_digest_mismatch"):
            self.verify()

    def test_tampered_embedding(self):
        (self.root / "embedding.txt").write_bytes(b"benign changed embedding")
        with self.assertRaisesRegex(Rejected, "artifact_digest_mismatch"):
            self.verify()

    def test_rehashed_candidate_still_denied(self):
        data = b"benign changed fixture"
        (self.root / "model.txt").write_bytes(data)
        self.mutate(lambda m: m["artifacts"][0].update(sha256=digest(data)))
        with self.assertRaisesRegex(Rejected, "manifest_not_in_policy"):
            self.verify()

    def test_unapproved_origin(self):
        self.mutate(lambda m: m.update(origin="urn:fictional:unapproved"))
        with self.assertRaisesRegex(Rejected, "unapproved_origin"):
            self.verify()

    def test_unapproved_dependency(self):
        with self.assertRaisesRegex(Rejected, "unapproved_dependency_lock"):
            self.verify(lock=LOCK + b"fictional-package==1.0\n")

    def test_rehashed_dependencies_still_denied(self):
        altered = LOCK.replace(b"1.43.119", b"1.43.118")
        self.mutate(lambda m: m.update(rag_lock_sha256=digest(altered)))
        with self.assertRaisesRegex(Rejected, "unapproved_dependency_lock"):
            self.verify(lock=altered)

    def test_missing_manifest(self):
        (self.root / "manifest.json").unlink()
        with self.assertRaisesRegex(Rejected, "missing_or_unsafe_file"):
            self.verify()

    def test_unknown_release(self):
        with self.assertRaisesRegex(Rejected, "unapproved_release"):
            self.verify(release="unknown")

    def test_duplicate_manifest_key(self):
        path = self.root / "manifest.json"
        path.write_text(path.read_text().replace('"release":', '"release":"stable","release":', 1))
        with self.assertRaisesRegex(Rejected, "duplicate_manifest_key"):
            self.verify()

    def test_symlink_artifact(self):
        path = self.root / "model.txt"
        path.unlink()
        try:
            path.symlink_to(FIXTURES / "candidate/model.txt")
        except OSError:
            self.skipTest("symlink creation not permitted")
        with self.assertRaisesRegex(Rejected, "missing_or_unsafe_file"):
            self.verify()

    def test_wrong_release_manifest(self):
        with self.assertRaisesRegex(Rejected, "manifest_not_in_policy"):
            self.verify(release="stable")

    def test_rollback(self):
        receipt = rehearse(LOCK)
        self.assertTrue(receipt["rollback_verified"])
        self.assertEqual(receipt["initial"], receipt["restored"])
        self.assertEqual(receipt["injected_failure"], "artifact_digest_mismatch")
        self.assertFalse(receipt["production_authorized"])


if __name__ == "__main__":
    unittest.main()
