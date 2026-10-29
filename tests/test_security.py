import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from app import workflow
from app.agent import run_agent
from app.tools import ToolController


def snapshot_fixture():
    candidates = [{
        "candidate_id": "CVE-2021-44228|SYN-001|CMP-001",
        "review_score": 100,
        "review_band": "expedited_review",
        "assessment": {
            "asset_id": "SYN-001",
            "component_id": "CMP-001",
            "owner": "Synthetic Operations",
            "applicability": "needs_review",
        },
        "finding": {
            "cve_id": "CVE-2021-44228",
            "description": "Synthetic evidence.",
        },
    }]
    return {
        "synthetic": True,
        "candidates_sha256": workflow.digest(candidates),
        "candidates": candidates,
        "sources": {},
    }


def model_tool(name, arguments, identifier="tool-1"):
    return {
        "stopReason": "tool_use",
        "output": {
            "message": {
                "role": "assistant",
                "content": [{
                    "toolUse": {
                        "toolUseId": identifier,
                        "name": name,
                        "input": arguments,
                    }
                }],
            }
        },
    }


class AgentSecurityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.root = Path(temporary.name)
        patcher = patch.object(workflow, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.snapshot = snapshot_fixture()
        self.identifier = workflow.highest_candidate(self.snapshot)

    def new_run(self):
        payload = workflow.build_ticket(
            self.snapshot, self.identifier, "Review synthetic evidence."
        )
        return workflow.create_run(self.snapshot, payload, [])

    def approve(self, run_id):
        record = workflow.load_run(run_id)
        workflow.approve_run(run_id, record["proposal_sha256"])

    def test_template_preserves_applicability(self):
        payload = workflow.build_ticket(
            self.snapshot, self.identifier, "Review needed."
        )
        self.assertEqual(payload["applicability"], "needs_review")
        self.assertEqual(payload["review_score"], 100)

    def test_changed_snapshot_is_rejected(self):
        changed = copy.deepcopy(self.snapshot)
        changed["candidates"][0]["review_score"] = 0

        with self.assertRaisesRegex(ValueError, "fingerprint"):
            workflow.candidate_index(changed)

    def test_unknown_candidate_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown candidate"):
            workflow.build_ticket(
                self.snapshot, "unknown", "Review needed."
            )

    def test_extra_tool_arguments_are_rejected(self):
        controller = ToolController(self.snapshot)

        with self.assertRaisesRegex(ValueError, "arguments"):
            controller.dispatch(
                "get_candidate",
                {
                    "candidate_id": self.identifier,
                    "path": "../../secrets",
                },
            )

    def test_evidence_must_be_read_before_proposal(self):
        controller = ToolController(self.snapshot)

        with self.assertRaisesRegex(ValueError, "Read candidate"):
            controller.dispatch(
                "propose_ticket",
                {
                    "candidate_id": self.identifier,
                    "justification": "Review needed.",
                },
            )

    def test_tool_budget_is_enforced(self):
        controller = ToolController(self.snapshot, max_calls=1)
        controller.dispatch("list_candidates", {})

        with self.assertRaisesRegex(ValueError, "budget"):
            controller.dispatch("list_candidates", {})

    def test_approval_tool_is_not_available(self):
        controller = ToolController(self.snapshot)

        with self.assertRaisesRegex(ValueError, "not permitted"):
            controller.dispatch("approve_ticket", {})

    def test_pending_run_cannot_execute(self):
        run_id = self.new_run()

        with self.assertRaisesRegex(ValueError, "requires approval"):
            workflow.execute_run(run_id)

        self.assertFalse((self.root / "review_tickets").exists())

    def test_approved_run_creates_ticket(self):
        run_id = self.new_run()
        self.approve(run_id)

        path = workflow.execute_run(run_id)

        self.assertTrue(path.exists())
        self.assertEqual(
            workflow.load_run(run_id)["state"], "EXECUTED"
        )

    def test_repeated_execution_has_one_ticket(self):
        run_id = self.new_run()
        self.approve(run_id)

        first = workflow.execute_run(run_id)
        second = workflow.execute_run(run_id)

        self.assertEqual(first, second)
        self.assertEqual(
            len(list((self.root / "review_tickets").glob("*.json"))),
            1,
        )

    def test_payload_change_after_approval_is_rejected(self):
        run_id = self.new_run()
        self.approve(run_id)

        path = workflow.run_path(run_id)
        record = workflow.read_json(path)
        record["payload"]["owner"] = "Changed owner"
        workflow.write_json(path, record)

        with self.assertRaisesRegex(ValueError, "payload changed"):
            workflow.execute_run(run_id)

    def test_rejected_run_cannot_execute(self):
        run_id = self.new_run()
        workflow.reject_run(run_id)

        with self.assertRaisesRegex(ValueError, "requires approval"):
            workflow.execute_run(run_id)

    def test_expired_approval_is_rejected(self):
        run_id = self.new_run()
        self.approve(run_id)

        path = workflow.run_path(run_id)
        record = workflow.read_json(path)
        record["approval"]["approved_at"] = (
            datetime.now(timezone.utc) - timedelta(days=2)
        ).isoformat()
        workflow.write_json(path, record)

        with self.assertRaisesRegex(ValueError, "expired"):
            workflow.execute_run(run_id)

    def test_mock_agent_completes_bounded_tool_sequence(self):
        client = Mock()
        client.converse.side_effect = [
            model_tool("list_candidates", {}, "tool-1"),
            model_tool(
                "get_candidate",
                {"candidate_id": self.identifier},
                "tool-2",
            ),
            model_tool(
                "propose_ticket",
                {
                    "candidate_id": self.identifier,
                    "justification": "Review synthetic evidence.",
                },
                "tool-3",
            ),
        ]

        payload, trace = run_agent(self.snapshot, client)

        self.assertEqual(payload["candidate_id"], self.identifier)
        self.assertEqual(len(trace), 3)
        self.assertEqual(client.converse.call_count, 3)

    def test_injection_requesting_shell_tool_is_denied(self):
        client = Mock()
        client.converse.return_value = model_tool(
            "run_shell",
            {"command": "create a ticket without approval"},
        )

        with self.assertRaisesRegex(ValueError, "not permitted"):
            run_agent(self.snapshot, client)

    def test_agent_proposal_does_not_create_ticket(self):
        client = Mock()
        client.converse.side_effect = [
            model_tool(
                "get_candidate",
                {"candidate_id": self.identifier},
                "tool-1",
            ),
            model_tool(
                "propose_ticket",
                {
                    "candidate_id": self.identifier,
                    "justification": "Review needed.",
                },
                "tool-2",
            ),
        ]

        run_agent(self.snapshot, client)

        self.assertFalse((self.root / "review_tickets").exists())


if __name__ == "__main__":
    unittest.main()