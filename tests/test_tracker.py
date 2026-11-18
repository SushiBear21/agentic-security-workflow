import json
import tempfile
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from tracker.assessment import FIXTURE_ID, exercise as assess
from tracker.release import decision
from tracker.server import Handler
from tracker.smoke import exercise
from tracker.store import Principal, Tracker, authenticate, load_principals


class TrackerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "tracker.sqlite"
        self.tracker = Tracker(self.path)
        self.contributor = Principal("demo", "Casey", "contributor")
        self.reviewer = Principal("demo", "Drew", "reviewer")
        self.evidence = {"id": FIXTURE_ID, "title": "Record", "note": "Synthetic"}

    def test_input_and_retry(self):
        item = self.tracker.run(self.contributor, "submit", self.evidence)
        recovered = Tracker(self.path)
        self.assertEqual(recovered.run(self.contributor, "submit", self.evidence), item)
        with self.assertRaises(ValueError):
            recovered.run(self.contributor, "submit", {**self.evidence, "title": "Different"})
        with self.assertRaises(ValueError):
            recovered.run(self.contributor, "submit", {**self.evidence, "workspace": "different"})
        record = recovered.run(self.reviewer, "export")
        self.assertEqual([entry["kind"] for entry in record["events"]], ["submitted", "exported"])

    def test_workspaces_and_contributor_views(self):
        item = self.tracker.run(self.contributor, "submit", self.evidence)
        for principal in [Principal("other", "Drew", "reviewer"), Principal("demo", "Pat", "contributor")]:
            self.assertEqual(self.tracker.run(principal, "list"), [])
        with self.assertRaises(KeyError):
            self.tracker.run(Principal("other", "Drew", "reviewer"), "review",
                             {"id": item["id"], "sha256": item["sha256"], "decision": "approve", "reason": "Reviewed"})
        self.assertEqual(self.tracker.run(Principal("other", "Drew", "reviewer"), "export")["records"], [])
        self.assertEqual(self.tracker.run(self.contributor, "list"), [item])

    def test_reject_and_review_retry(self):
        item = self.tracker.run(self.contributor, "submit", self.evidence)
        review = {"id": item["id"], "sha256": item["sha256"], "decision": "reject", "reason": "Missing detail"}
        result = self.tracker.run(self.reviewer, "review", review)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.tracker.run(self.reviewer, "review", review), result)
        with self.assertRaises(ValueError):
            self.tracker.run(self.reviewer, "review", {**review, "reason": "Different reasoning"})

    def test_credential_roles_cannot_overlap(self):
        path = self.path.with_suffix(".json")
        row = {"workspace": "demo", "name": "Casey", "role": "contributor", "token": "C" * 32}
        path.write_text(json.dumps([row, {**row, "role": "reviewer", "token": "R" * 32}]))
        with self.assertRaises(ValueError):
            load_principals(path)
        self.assertIsNone(authenticate({"C" * 32: self.contributor}, "Bearer 👎"))

    def test_http_workflow(self):
        accounts = {"C" * 32: self.contributor, "R" * 32: self.reviewer}
        handler = partial(Handler, tracker=self.tracker, accounts=accounts)
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}"
                baseline = exercise(url, accounts)
                self.assertTrue(baseline["passed"])
                self.assertTrue(exercise(url, accounts, baseline)["preserved_baseline"])
            finally:
                server.shutdown()
                worker.join()

    def test_go_no_go_and_assessment_retest(self):
        sbom = {"bomFormat": "CycloneDX", "components": [{"name": "fixture"}]}
        self.assertEqual(decision({"status": "pass"}, {"passed": True}, sbom)["outcome"], "eligible_for_review")
        self.assertEqual(decision({"status": "pass"}, {"passed": False}, sbom)["outcome"], "blocked")
        self.assertEqual(decision({"status": "fail"}, {"passed": True}, sbom)["outcome"], "blocked")
        self.assertEqual(decision({"status": "pass"}, {"passed": True}, {})["outcome"], "blocked")
        result = assess()
        self.assertTrue(all(row.get("passed", True) for row in result["objectives"]))
        finding = result["findings"][0]
        self.assertFalse(finding["baseline_passed"])
        self.assertTrue(finding["retest_passed"])
        self.assertTrue(finding["changed_candidate_blocked"])
