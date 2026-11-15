"""Calculate adoption from explicit cohorts and observations, never invented usage."""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path

def moment(value):
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None: raise ValueError("Timezone required")
    return t

def measure(data):
    if data.get("schema_version") != 1 or type(data.get("synthetic")) is not bool:
        raise ValueError("Version and explicit synthetic flag required")
    start, end = moment(data["window_start"]), moment(data["window_end"])
    if start >= end: raise ValueError("Invalid observation window")
    cohort, prior = data["eligible_users"], data["prior_active_users"]
    for users in (cohort, prior):
        if not isinstance(users, list) or any(not isinstance(u, str) or not u.strip() for u in users) or len(users) != len(set(users)):
            raise ValueError("Unique pseudonymous user IDs required")
    if not set(prior) <= set(cohort): raise ValueError("Prior cohort outside eligible population")
    events = data["events"]
    if not isinstance(events, list): raise ValueError("Events must be a list")
    seen, active = set(), set()
    counts = dict(workflow_completed=0, workflow_failed=0, draft_accepted=0, draft_rejected=0)
    for event in events:
        if set(event) != {"id", "user_id", "at", "kind"} or not isinstance(event["id"], str) or not event["id"] or event["id"] in seen:
            raise ValueError("Invalid or duplicate event")
        seen.add(event["id"])
        if event["user_id"] not in cohort or not start <= moment(event["at"]) < end or event["kind"] not in counts:
            raise ValueError("Event outside cohort/window or unknown kind")
        counts[event["kind"]] += 1
        if event["kind"] == "workflow_completed": active.add(event["user_id"])
    pairs = data.get("timing_pairs", [])
    if not isinstance(pairs, list): raise ValueError("Timing pairs must be a list")
    ids, savings = set(), []
    for row in pairs:
        if set(row) != {"task_id", "manual_seconds", "assisted_seconds"} or not isinstance(row["task_id"], str) or not row["task_id"] or row["task_id"] in ids:
            raise ValueError("Invalid or duplicate paired task")
        ids.add(row["task_id"])
        for key in ("manual_seconds", "assisted_seconds"):
            v = row[key]
            if type(v) not in (int, float) or not math.isfinite(v) or v < 0: raise ValueError("Invalid duration")
        savings.append(row["manual_seconds"] - row["assisted_seconds"])
    ratio = lambda n, d: n / d if d else None
    attempts = counts["workflow_completed"] + counts["workflow_failed"]
    reviews = counts["draft_accepted"] + counts["draft_rejected"]
    return {"schema_version": 1, "synthetic": data["synthetic"], "eligible_users": len(cohort),
            "active_users": len(active), "activation_rate": ratio(len(active), len(cohort)),
            "prior_active_users": len(prior), "retained_users": len(active & set(prior)),
            "retention_rate": ratio(len(active & set(prior)), len(prior)),
            "workflow_attempts": attempts, "completion_rate": ratio(counts["workflow_completed"], attempts),
            "reviewed_drafts": reviews, "draft_acceptance_rate": ratio(counts["draft_accepted"], reviews),
            "paired_tasks": len(savings), "mean_seconds_saved": ratio(sum(savings), len(savings)),
            "counts": counts, "limitations": "Observed cohort/window only; paired timings are self-reported, not causal productivity proof."}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input"); p.add_argument("--output", required=True)
    a = p.parse_args()
    result = measure(json.loads(Path(a.input).read_text(encoding="utf-8")))
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__": main()
