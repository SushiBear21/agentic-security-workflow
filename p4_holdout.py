"""Prospective holdout cases kept separate from the development comparison."""
from copy import deepcopy
from pathlib import Path

from p4_context import context_fixture, request_fixture

PROTOCOL = Path(__file__).parent / "docs/portfolio/prospective-evaluation.md"
ANSWERED = {"holdout-medium-exposed", "holdout-low-private"}


def cases():
    for name, asset, exposed, criticality in (
        ("holdout-medium-exposed", "SYN-HOLDOUT-101", True, "medium"),
        ("holdout-low-private", "SYN-HOLDOUT-102", False, "low"),
    ):
        document = context_fixture(text="Synthetic held-out inventory. Installed version unverified.")
        document["facts"].update(
            asset_id=asset, internet_exposed=exposed, business_criticality=criticality
        )
        request = request_fixture(asset_id=asset, documents=[document])
        yield name, request, {
            "status": "answered", "tool_calls": 1, "action": "propose_review",
            "applicability": "needs_review", "facts": deepcopy(document["facts"]),
            "citations": [document["id"]],
        }
        if not exposed:
            restricted = deepcopy(document)
            restricted["audiences"] = ["soc_analysts"]
            yield "holdout-private-restricted", request_fixture(
                asset_id=asset, documents=[restricted]
            ), {
                "status": "insufficient_evidence", "tool_calls": 0, "action": "none",
                "applicability": "unknown", "facts": {}, "citations": [],
            }
