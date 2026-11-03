"""Offline evidence bridges; original approvals never authorize tower actions."""
import json
from copy import deepcopy
from app.workflow import build_ticket, digest
from tower.core import validate_finding


def import_evidence(source, record, metadata):
    finding = deepcopy(metadata)
    if source == "agentic":
        payload = record["payload"]
        if digest(record["snapshot"]) != record["snapshot_sha256"] or digest(payload) != record["proposal_sha256"]:
            raise ValueError("Agentic evidence fingerprint mismatch")
        expected = build_ticket(record["snapshot"], payload["candidate_id"], payload["draft_justification"])
        if payload != expected:
            raise ValueError("Agentic payload template mismatch")
        summary = {"source": "agentic-security-workflow", "record_sha256": digest(record), "candidate_id": payload["candidate_id"], "title": payload["title"]}
    elif source == "aws-lab":
        if record.get("schema_version") != "1" or record.get("sample_status") != "confirmed_sample" or record.get("source") != "guardduty" or record.get("response_state") != "no_response_requested":
            raise ValueError("Only confirmed GuardDuty samples from the lab normalizer are accepted")
        summary = {"source": "aws-security-response-lab", "record_sha256": digest(record), "finding_id": record["finding_id"], "title": record["title"]}
    else:
        raise ValueError("Unknown source")
    finding["evidence"] = json.dumps(summary, ensure_ascii=False)
    validate_finding(finding)
    return finding
