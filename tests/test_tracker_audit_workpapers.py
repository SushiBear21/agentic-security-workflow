import json
from copy import deepcopy
from unittest import TestCase

from tracker.audit_workpapers import EVIDENCE, build_packet, verify_samples


class TrackerAuditWorkpapersTests(TestCase):
    def test_verified_sample_packet_distinguishes_rehearsal_from_release(self):
        packet = build_packet()
        self.assertEqual({"ci_rehearsals": 3, "tagged_releases": 0, "deployments": 0,
                          "formal_reviews_on_sampled_prs": 0}, packet["population"])
        self.assertEqual(["CI-01", "CI-02", "CI-03"], [
            item["sample_id"] for item in packet["sample_workpapers"]
        ])
        for item in packet["samples"]:
            observed = item["observation"]
            self.assertFalse(observed["promotion_authorized"])
            self.assertEqual("blocked", observed["phase_outcomes"]["candidate"])
            self.assertTrue(observed["recovery_preserved_baseline_reported"])

    def test_evidence_request_paths_and_closure_are_explicit(self):
        packet = build_packet()
        requests = {item["id"]: item for item in packet["evidence_requests"]}
        self.assertEqual(("fulfilled", ["CI-01", "CI-02", "CI-03"]), (
            requests["ER-01"]["status"], requests["ER-01"]["sources"],
        ))
        self.assertEqual(("missing", "E-01"), (requests["ER-02"]["status"], requests["ER-02"]["finding"]))
        self.assertEqual(("insufficient", "E-02"), (requests["ER-03"]["status"], requests["ER-03"]["finding"]))
        self.assertEqual("E-03", requests["ER-05"]["finding"])
        self.assertTrue(packet["findings"]["ISO-F01"]["retest"].startswith("Passed in the lab"))
        self.assertEqual({"pending"}, {finding["closure"] for finding in packet["findings"].values()})
        self.assertIsNone(packet["reviewer_disposition"]["reviewer"])
        self.assertEqual("pending", packet["reviewer_disposition"]["decision"])

    def test_duplicate_and_out_of_period_samples_are_rejected(self):
        population = json.loads((EVIDENCE / "tracker-audit-population.json").read_bytes())
        duplicate = deepcopy(population)
        duplicate["samples"][1]["source"]["run_id"] = duplicate["samples"][0]["source"]["run_id"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            verify_samples(EVIDENCE, duplicate)
        population["samples"][0]["run_created_at"] = "2026-11-17T15:00:00Z"
        with self.assertRaisesRegex(ValueError, "outside observation window"):
            verify_samples(EVIDENCE, population)
