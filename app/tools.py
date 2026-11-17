from time import monotonic
from uuid import uuid4

from app.workflow import (
    build_ticket,
    candidate_index,
    highest_candidate,
)


class ToolController:
    """Process-local capability held by the host, never serialized to the model."""

    def __init__(self, snapshot, max_calls=8, *, clock=monotonic):
        self.snapshot = snapshot
        self.candidates = candidate_index(snapshot)
        self.target = highest_candidate(snapshot)
        self.max_calls = max_calls
        self.calls = 0
        self.read_candidates = set()
        self.trace = []
        self.principal = "review-agent/" + uuid4().hex
        self.clock = clock
        self.expires = clock() + 180

    def dispatch(self, name, arguments):
        decision = "denied"
        known = name if isinstance(name, str) and name in {
            "list_candidates", "get_candidate", "propose_ticket"
        } else "unknown"
        try:
            result = self._dispatch(known, arguments)
            decision = "allowed"
            return result
        finally:
            self.trace.append({"principal": self.principal, "tool": known, "decision": decision})

    def _dispatch(self, name, arguments):
        if self.clock() >= self.expires:
            raise ValueError("Agent tool capability expired.")
        self.calls += 1

        if self.calls > self.max_calls:
            raise ValueError("Tool-call budget exceeded.")

        allowed = {
            "list_candidates": set(),
            "get_candidate": {"candidate_id"},
            "propose_ticket": {"candidate_id", "justification"},
        }

        if name not in allowed:
            raise ValueError("Tool is not permitted.")

        if (
            not isinstance(arguments, dict)
            or set(arguments) != allowed[name]
        ):
            raise ValueError("Unexpected tool arguments.")

        if name == "list_candidates":
            result = {
                "required_target": self.target,
                "candidates": [{
                    "candidate_id": identifier,
                    "review_score": candidate["review_score"],
                    "review_band": candidate["review_band"],
                } for identifier, candidate in sorted(
                    self.candidates.items(),
                    key=lambda item: (
                        -item[1]["review_score"],
                        item[0],
                    ),
                )],
            }

        else:
            identifier = arguments["candidate_id"]
            if not isinstance(identifier, str) or identifier not in (
                self.candidates
            ):
                raise ValueError("Unknown candidate.")

            if name == "get_candidate":
                self.read_candidates.add(identifier)
                result = self.candidates[identifier]

                # Bound tool-result size before returning it to the model.
                import json
                if len(json.dumps(result)) > 20000:
                    raise ValueError("Candidate evidence exceeds size limit.")

            else:
                if identifier not in self.read_candidates:
                    raise ValueError("Read candidate evidence before proposing.")

                result = build_ticket(
                    self.snapshot,
                    identifier,
                    arguments["justification"],
                )

        return result
