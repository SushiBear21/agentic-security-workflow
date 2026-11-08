import json
import tempfile
import unittest
from pathlib import Path
from tower.readiness_package import ROOT, build, verify, safe_relative

class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'evidence'

    def test_pack_and_verify(self):
        manifest = build(self.out)
        self.assertTrue(verify(self.out))
        self.assertIn('Not FedRAMP', manifest['assertion'])

    def test_changed_evidence_rejected(self):
        build(self.out)
        (self.out / 'tower/core.py').write_text('changed')
        with self.assertRaises(ValueError): verify(self.out)

    def test_missing_evidence_rejected(self):
        build(self.out)
        (self.out / 'tower/core.py').unlink()
        with self.assertRaises(ValueError): verify(self.out)

    def test_extra_file_rejected(self):
        build(self.out)
        (self.out / 'unexpected.txt').write_text('extra')
        with self.assertRaises(ValueError): verify(self.out)

    def test_existing_directory_not_overwritten(self):
        build(self.out)
        with self.assertRaises(ValueError): build(self.out)

    def test_mapping_evidence_exists_and_gaps_are_explicit(self):
        records = json.loads((ROOT / 'docs/portfolio/readiness-controls.json').read_text())
        self.assertEqual(len({r['control'] for r in records}), len(records))
        for row in records:
            self.assertEqual(row['status'], 'partial_synthetic_demonstration')
            self.assertTrue(row['gap'])
            for name in row['evidence']:
                self.assertTrue((ROOT / safe_relative(name)).is_file(), name)

    def test_path_traversal_rejected(self):
        for name in ('../secret', '/etc/passwd', 'C:\\secret', 'a/../../b'):
            with self.assertRaises(ValueError): safe_relative(name)
