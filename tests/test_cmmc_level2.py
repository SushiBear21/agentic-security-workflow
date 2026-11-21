from copy import deepcopy
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

    def test_all_objective_identifiers_are_ordered_and_complete(self):
        controls, _ = assessment.load()
        self.assertEqual(assessment.validate_requirements(controls), 320)
        identifiers = [o["id"] for r in controls for o in r["assessment_objectives"]]
        self.assertEqual(len(identifiers), 320)
        self.assertEqual(len(set(identifiers)), 320)
        normalized = next(r for r in controls if r["id"] == "3.2.1")
        self.assertEqual([o["id"] for o in normalized["assessment_objectives"]],
                         ["3.2.1[a]", "3.2.1[b]", "3.2.1[c]", "3.2.1[d]"])
        for r in controls:
            for o in r["assessment_objectives"]:
                self.assertFalse(o["criterion"].startswith(("ermine if", "1[", "Determine if")))

    def test_corruption_is_rejected_before_evidence_generation(self):
        controls, _ = assessment.load()
        for bad_id, bad_text in (("3.2.1 [.]", None), ("3.4.4[D]", "ermine if a decision exists."),
                                 ("3.4.4[c]", "Valid words but wrong index."), (None, "1[a] clipped objective.")):
            clone = deepcopy(controls)
            case = next(r for r in clone if r["id"] == ("3.2.1" if bad_id == "3.2.1 [.]" else "3.4.4"))
            if bad_id is not None:
                case["assessment_objectives"][0]["id"] = bad_id
            if bad_text is not None:
                case["assessment_objectives"][0]["criterion"] = bad_text
            with self.subTest(id=bad_id, text=bad_text):
                with self.assertRaises(ValueError):
                    assessment.validate_requirements(clone)

    def test_scoped_pr13_f001_is_not_assessment_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(assessment, "OUT", Path(temporary)):
                counts = assessment.build()
                trace = list(csv.DictReader((Path(temporary) / "scoped_case_trace.csv").open()))
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["objective_id"], "3.4.3[c]")
        self.assertEqual(trace[0]["finding_id"], "F-001")
        self.assertEqual(trace[0]["source_commit"], "9eeacafdf39bad4c72b4a486062a146f95d74126")
        self.assertEqual(trace[0]["assessment_outcome"], "NOT_EVALUATED")
        self.assertEqual(counts["NOT_EVALUATED"], 103)

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
