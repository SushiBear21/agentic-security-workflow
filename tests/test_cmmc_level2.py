import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from labs.cmmc_level2 import assessment

class CMMCLabTests(unittest.TestCase):
    def test_full_catalog(self):
        requirements, scenario = assessment.load()
        self.assertEqual(len(requirements), 110)
        self.assertEqual(len({r["id"] for r in requirements}), 110)
        self.assertEqual(len({r["family"] for r in requirements}), 14)
        self.assertTrue(scenario["synthetic"])

    def test_generation_and_no_false_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(assessment, "OUT", Path(directory)):
                counts = assessment.build()
                self.assertEqual(sum(counts.values()), 110)
                self.assertGreater(counts["NOT_EVALUATED"], 0)
                rows = list(csv.DictReader((Path(directory)/"evidence_tracker.csv").open()))
                self.assertEqual(len(rows),110)
                self.assertTrue(all(r["evidence_reviewed"] == "False" for r in rows))
                self.assertIn("NOT A CMMC ASSESSMENT", (Path(directory)/"management_report.md").read_text())
                self.assertIn("NO-GO", (Path(directory)/"management_report.md").read_text())
                self.assertEqual(len(list(csv.DictReader((Path(directory)/"poam.csv").open()))),counts["NOT_MET"])

if __name__ == "__main__":
    unittest.main()
