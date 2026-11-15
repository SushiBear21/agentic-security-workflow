import json
import unittest
from pathlib import Path
from p4_regression import evaluate
from p4_context import run_context

class RegressionGateTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((Path(__file__).parent / "fixtures/p4-regression-v1.json").read_text())
    def test_reference_and_unknown_model_measurements(self):
        report = evaluate(self.dataset)
        self.assertEqual(report["passed"], report["total"])
        self.assertIsNone(report["model_tokens"])
        self.assertGreaterEqual(report["p95_ms"], report["median_ms"])
        self.assertEqual(report["model_calls"], 0)
    def test_broken_runner_is_detected(self):
        def broken(request):
            response = run_context(request)
            response["action"] = "quarantine"
            return response
        report = evaluate(self.dataset, broken)
        self.assertEqual(report["passed"], 0)
    def test_empty_and_duplicate_dataset_rejected(self):
        for cases in ([], self.dataset["cases"] * 2):
            with self.assertRaises(ValueError): evaluate(dict(self.dataset, cases=cases))
