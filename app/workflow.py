import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def now_text():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("JSON file exceeds size limit.")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")

    try:
        temporary.write_text(
            json.dumps(value, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def candidate_index(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("synthetic") is not True:
        raise ValueError("Synthetic snapshot required.")

    candidates = snapshot.get("candidates")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 10:
        raise ValueError("Expected 1–10 candidates.")

    if digest(candidates) != snapshot.get("candidates_sha256"):
        raise ValueError("Candidate fingerprint mismatch.")

    result = {}

    for candidate in candidates:
        identifier = candidate.get("candidate_id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("Missing candidate identifier.")
        if identifier in result:
            raise ValueError("Duplicate candidate identifier.")

        score = candidate.get("review_score")
        if type(score) not in (int, float) or not 0 <= score <= 100:
            raise ValueError("Invalid review score.")

        if candidate["assessment"].get("applicability") != "needs_review":
            raise ValueError("Expected needs_review applicability.")

        result[identifier] = candidate

    return result


def highest_candidate(snapshot):
    candidates = candidate_index(snapshot)
    return sorted(
        candidates,
        key=lambda identifier: (
            -candidates[identifier]["review_score"],
            identifier,
        ),
    )[0]


def build_ticket(snapshot, candidate_id, justification):
    candidates = candidate_index(snapshot)

    if candidate_id not in candidates:
        raise ValueError("Unknown candidate.")

    if candidate_id != highest_candidate(snapshot):
        raise ValueError("Proposal must use the highest-ranked candidate.")

    if (
        not isinstance(justification, str)
        or not justification.strip()
        or len(justification) > 1500
    ):
        raise ValueError("Invalid draft justification.")

    candidate = candidates[candidate_id]
    assessment = candidate["assessment"]
    finding = candidate["finding"]

    return {
        "action": "create_local_review_ticket",
        "synthetic": True,
        "candidate_id": candidate_id,
        "title": (
            f"[SYNTHETIC REVIEW] {finding['cve_id']} / "
            f"{assessment['asset_id']}"
        ),
        "cve_id": finding["cve_id"],
        "asset_id": assessment["asset_id"],
        "component_id": assessment["component_id"],
        "owner": assessment["owner"],
        "review_score": candidate["review_score"],
        "review_band": candidate["review_band"],
        "applicability": "needs_review",
        "required_next_step": (
            "Verify installed component, affected version, configuration, "
            "and patch status before deciding remediation."
        ),
        "draft_justification": justification.strip(),
        "commentary_status": "unverified_model_draft",
        "evidence_snapshot_sha256": digest(snapshot),
    }


def run_path(run_id):
    if not isinstance(run_id, str) or not re.fullmatch(
        r"[0-9a-f]{32}", run_id
    ):
        raise ValueError("Invalid run identifier.")
    return ROOT / "agent_runs" / run_id / "run.json"


def add_event(record, event):
    record["audit"].append({
        "time": now_text(),
        "event": event,
        "proposal_sha256": record["proposal_sha256"],
    })


def create_run(snapshot, payload, tool_trace):
    expected = build_ticket(
        snapshot,
        payload["candidate_id"],
        payload["draft_justification"],
    )
    if payload != expected:
        raise ValueError("Proposal does not match the ticket template.")

    run_id = uuid4().hex
    record = {
        "run_id": run_id,
        "created_at": now_text(),
        "state": "PENDING",
        "snapshot": snapshot,
        "snapshot_sha256": digest(snapshot),
        "payload": payload,
        "proposal_sha256": digest(payload),
        "tool_trace": tool_trace,
        "approval": None,
        "audit": [],
    }
    add_event(record, "proposal_created")
    write_json(run_path(run_id), record)
    return run_id


def load_run(run_id):
    record = read_json(run_path(run_id))

    if record.get("run_id") != run_id:
        raise ValueError("Run identifier mismatch.")

    snapshot = record["snapshot"]
    if digest(snapshot) != record["snapshot_sha256"]:
        raise ValueError("Evidence snapshot changed.")

    expected = build_ticket(
        snapshot,
        record["payload"]["candidate_id"],
        record["payload"]["draft_justification"],
    )

    if record["payload"] != expected:
        raise ValueError("Ticket payload changed.")

    if digest(record["payload"]) != record["proposal_sha256"]:
        raise ValueError("Proposal fingerprint mismatch.")

    return record


def approve_run(run_id, expected_digest):
    record = load_run(run_id)

    if record["state"] != "PENDING":
        raise ValueError("Only pending proposals can be approved.")

    if expected_digest != record["proposal_sha256"]:
        raise ValueError("Proposal changed after display.")

    record["state"] = "APPROVED"
    record["approval"] = {
        "decision": "approved",
        "approved_at": now_text(),
        "proposal_sha256": expected_digest,
        "method": "local_operator_explicit_confirmation",
    }
    add_event(record, "approved")
    write_json(run_path(run_id), record)


def reject_run(run_id):
    record = load_run(run_id)

    if record["state"] != "PENDING":
        raise ValueError("Only pending proposals can be rejected.")

    record["state"] = "REJECTED"
    add_event(record, "rejected")
    write_json(run_path(run_id), record)


def execute_run(run_id):
    record = load_run(run_id)

    if record["state"] not in {"APPROVED", "EXECUTED"}:
        raise ValueError("Execution requires approval.")

    approval = record.get("approval") or {}
    if (
        approval.get("decision") != "approved"
        or approval.get("proposal_sha256") != record["proposal_sha256"]
    ):
        raise ValueError("Approval does not match the proposal.")

    approved_at = datetime.fromisoformat(approval["approved_at"])
    age = datetime.now(timezone.utc) - approved_at

    if age < timedelta(0) or age > timedelta(hours=24):
        raise ValueError("Approval is expired or invalid.")

    ticket = {
        "run_id": run_id,
        "proposal_sha256": record["proposal_sha256"],
        "payload": record["payload"],
    }
    destination = ROOT / "review_tickets" / f"{run_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(ticket, stream, indent=2, allow_nan=False)
    except FileExistsError:
        if read_json(destination) != ticket:
            raise ValueError("Existing ticket differs from approved payload.")

    # Repeated execution reconciles the same ticket rather than creating another.
    if record["state"] != "EXECUTED":
        record["state"] = "EXECUTED"
        add_event(record, "ticket_created")
        write_json(run_path(run_id), record)

    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["inspect", "approve", "reject", "execute"]
    )
    parser.add_argument("--run", required=True)
    args = parser.parse_args()

    try:
        if args.command == "inspect":
            record = load_run(args.run)
            print(json.dumps({
                "run_id": record["run_id"],
                "state": record["state"],
                "proposal_sha256": record["proposal_sha256"],
                "payload": record["payload"],
                "audit": record["audit"],
            }, indent=2))

        elif args.command == "approve":
            record = load_run(args.run)
            print(json.dumps(record["payload"], indent=2))
            expected = record["proposal_sha256"]
            phrase = "APPROVE " + expected[:12]

            print(f"\nTo approve this exact payload, type: {phrase}")
            if input("> ").strip() != phrase:
                raise ValueError("Approval not granted.")

            approve_run(args.run, expected)
            print("APPROVED. No ticket has been created yet.")

        elif args.command == "reject":
            reject_run(args.run)
            print("REJECTED.")

        else:
            path = execute_run(args.run)
            print(f"Ticket available at: {path}")

    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Workflow stopped: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())