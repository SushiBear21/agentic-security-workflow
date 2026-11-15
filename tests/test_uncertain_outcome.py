"""A committed write with a lost acknowledgement must be reconciled before retry."""
import json
import unittest
from pathlib import Path
from tower.core import empty
from tower.store import DynamoStore

class LostAcknowledgement:
    def __init__(self): self.item = None; self.fail_after_commit = False; self.writes = 0
    def get_item(self, **kwargs): return {"Item": self.item} if self.item else {}
    def put_item(self, **kwargs):
        self.writes += 1
        self.item = kwargs["Item"]
        if self.fail_after_commit:
            self.fail_after_commit = False
            raise TimeoutError("synthetic acknowledgement lost after commit")

class UncertainOutcomeTests(unittest.TestCase):
    def test_reconcile_committed_execution_without_duplicate(self):
        client = LostAcknowledgement()
        store = DynamoStore(client, "synthetic")
        fixtures = json.loads((Path(__file__).resolve().parents[1] / "tower/fixtures.json").read_text())
        store.run("ingest", {"findings": fixtures}, "operator", 100)
        key = store.run("propose", {"id": "SEC-001", "draft": "Review", "provider": "reference_fixture"}, "operator", 101)
        store.run("approve", {"id": key, "sha256": key, "effort_seconds": 1}, "human", 102)
        client.fail_after_commit = True
        before = client.writes
        with self.assertRaises(TimeoutError): store.run("execute", {"id": key}, "operator", 103)
        self.assertEqual(client.writes, before + 1)
        self.assertEqual(store.read()["proposals"][key]["state"], "EXECUTED")
        self.assertEqual(store.run("execute", {"id": key}, "operator", 104), "already_executed")
        self.assertEqual(len(store.read()["tickets"]), 1)
