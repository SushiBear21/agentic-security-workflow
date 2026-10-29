from app.workflow import (
    build_ticket,
    candidate_index,
    highest_candidate,
)


class ToolController:
    def __init__(self, snapshot, max_calls=8):
        self.snapshot = snapshot
        self.candidates = candidate_index(snapshot)
        self.target = highest_candidate(snapshot)
        self.max_calls = max_calls
        self.calls = 0
        self.read_candidates = set()
        self.trace = []

    def dispatch(self, name, arguments):
        self.calls += 1

        if self.calls > self.max_calls:
            raise ValueError("Tool-call budget exceeded.")

        allowed = {
            "list_candidates": set(),
            "get_candidate": {"candidate_id"},
            "propose_ticket": {"candidate_id", "justification"},
        }

        if name not in allowed:
            self.trace.append({
                "tool": "unknown",
                "decision": "denied",
            })
            raise ValueError("Tool is not permitted.")

        if (
            not isinstance(arguments, dict)
            or set(arguments) != allowed[name]
        ):
            self.trace.append({
                "tool": name,
                "decision": "denied_arguments",
            })
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

        self.trace.append({
            "tool": name,
            "decision": "allowed",
        })
        return result