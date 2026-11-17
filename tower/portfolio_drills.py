"""Generate offline evidence for AWS guardrails, FedRAMP indicators and AI operations."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.workflow import digest
from tower.llmops import CANDIDATE, STABLE, canary, evaluate_boundary

ROOT = Path(__file__).resolve().parents[1]
DEMO_TIME = datetime(2026, 11, 17, 20, tzinfo=timezone.utc)
EXPECTED = {"trail_logging": True, "archive_public_block": True, "archive_versioning": True}


def audit_guardrails(policy):
    """Exercise the explicit deny statements; this is a fixture, not IAM simulation."""
    denied = {
        action for rule in policy["Statement"] if rule["Effect"] == "Deny" and rule["Resource"] == "*"
        for action in rule["Action"]
    }
    action = "cloudtrail:StopLogging"
    healthy = dict(EXPECTED)
    drifted = {**healthy, "archive_versioning": False}
    restored = {**drifted, "archive_versioning": healthy["archive_versioning"]}
    return {
        "scope": "offline policy and configuration fixture",
        "account_layout": ["management", "security", "log archive", "workload"],
        "policy_sha256": digest(policy),
        "attempt": {"account": "workload member", "action": action, "explicit_deny": action in denied},
        "non_target_action_matched": "cloudtrail:DescribeTrails" in denied,
        "drift": {"expected": healthy, "observed": drifted, "changed_keys": [
            key for key, value in healthy.items() if drifted[key] != value
        ]},
        "restored": restored,
        "restored_matches_baseline": restored == healthy,
    }


def assess_ksi(observation, now):
    """Evaluate two narrow evidence checks without inferring full KSI coverage."""
    timestamp = datetime.fromisoformat(observation["observed_at"])
    if timestamp.utcoffset() is None:
        raise ValueError("Observation must include a timezone")
    age = now - timestamp
    fresh = timedelta() <= age <= timedelta(hours=24)
    values = observation["values"]
    checks = {
        "KSI-MLA-EVC": ("archive_public_block", "archive_versioning"),
        "KSI-MLA-LET": ("trail_logging", "event_inventory_present"),
    }
    rows = []
    for indicator, fields in checks.items():
        failed = [field for field in fields if values.get(field) is not True]
        rows.append({
            "indicator": indicator,
            "scope": "selected evidence check",
            "state": "pass" if fresh and not failed else "fail",
            "reasons": (["stale_or_future_observation"] if not fresh else []) + failed,
        })
    return {"observation_sha256": digest(observation), "assessed_at": now.isoformat(), "checks": rows}


def fedramp_drill(landing):
    def snapshot(values, observed_at):
        return {"mode": "synthetic_fixture", "observed_at": observed_at.isoformat(),
                "values": {**values, "event_inventory_present": True}}

    healthy = snapshot(EXPECTED, DEMO_TIME)
    drifted = snapshot(landing["drift"]["observed"], DEMO_TIME + timedelta(minutes=1))
    restored = snapshot(landing["restored"], DEMO_TIME + timedelta(hours=26))
    stages = [
        ("baseline", healthy, DEMO_TIME),
        ("drift", drifted, DEMO_TIME + timedelta(minutes=1)),
        ("expired", healthy, DEMO_TIME + timedelta(hours=25)),
        ("retest", restored, DEMO_TIME + timedelta(hours=26)),
    ]
    return {
        "record_type": "synthetic Security Decision Record",
        "boundary": "Example Bedrock application, organization trail and log archive",
        "responsibilities": {
            "provider": "Configure application access, evidence collection, monitoring and remediation.",
            "customer": "Approve intended use, classify inputs and review access assignments.",
            "inherited_service": "Confirm inherited controls against the applicable service documentation.",
        },
        "evidence": {name: {"observation": obs, "assessment": assess_ksi(obs, at)}
                     for name, obs, at in stages},
        "remediation": {"owner": "fixture cloud security lead", "action": "Restore archive versioning",
                        "retest_stage": "retest"},
        "decision": "review synthetic evidence only",
        "authorization_granted": False,
    }


def incident_drill():
    evaluation = evaluate_boundary()
    if evaluation["passed"] != evaluation["total"]:
        raise ValueError("Model change preflight failed")
    rollout = canary()
    rows = rollout["requests"]
    candidate = CANDIDATE["model_id"]
    stable = STABLE["model_id"]
    first_failure = next((row for row in rows if row["route"] == candidate and not row["accepted"]), None)
    if first_failure is None or not rollout["rollback"]:
        raise ValueError("Expected candidate failure was not detected")
    preceding = [row for row in rows if row["request"] < first_failure["request"]]
    recovery = [row for row in rows if row["request"] > first_failure["request"]]
    if not any(row["route"] == candidate and row["accepted"] for row in preceding) or not recovery:
        raise ValueError("Missing pre-incident and recovery observations")
    restored = all(row["route"] == stable and row["accepted"] for row in recovery)
    if not restored:
        raise ValueError("Stable route did not recover")
    events = []
    for kind, actor, details in [
        ("change_reviewed", "fixture release approver", {"preflight_sha256": digest(evaluation), "scope": "fixture canary"}),
        ("canary_started", "fixture release operator", {"candidate_percent": rollout["candidate_percent"]}),
        ("candidate_rejected", "output contract monitor", {"request": first_failure["request"], "candidate": candidate}),
        ("candidate_paused_and_rolled_back", "fixture release controller", {"active_model": stable}),
        ("stable_route_resume_approved", "fixture incident owner", {"verified_follow_up_requests": len(recovery)}),
    ]:
        entry = {"sequence": len(events), "kind": kind, "actor": actor, "details": details,
                 "previous_sha256": events[-1]["sha256"] if events else None}
        events.append({**entry, "sha256": digest(entry)})
    return {
        "scope": "offline synthetic change and incident exercise", "live_model_calls": 0,
        "inventory": {"stable": STABLE, "candidate": CANDIDATE, "prompt_sha256": rollout["prompt_sha256"]},
        "impact_assessment": "An invalid advisory draft could misdirect review. Output validation blocks execution requests.",
        "preflight": evaluation, "rollout": rollout, "events": events,
        "stable_route_verified": restored, "candidate_reenabled": False,
    }


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    policy = json.loads((ROOT / "infra/landing-zone/guardrails.json").read_text())
    landing = audit_guardrails(policy)
    reports = {
        "aws-landing-zone.json": landing,
        "fedramp-decision-record.json": fedramp_drill(landing),
        "ai-model-incident.json": incident_drill(),
    }
    for filename, evidence in reports.items():
        (output / filename).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New evidence directory")
    args = parser.parse_args()
    generate(args.output)
    print("Generated three exercise records in", args.output)


if __name__ == "__main__":
    main()
