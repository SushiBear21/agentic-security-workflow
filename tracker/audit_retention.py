"""Reperform the retained archives and reconcile GitHub metadata before expiry."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from tracker.audit_workpapers import EVIDENCE, build_packet
from tracker.audit_bundle import REPOSITORY, require


def check_retention():
    now = datetime.now(timezone.utc)
    packet = build_packet()
    population = json.loads((EVIDENCE / "tracker-audit-population.json").read_bytes())
    rows = []
    for sample in population["samples"]:
        source = sample["source"]
        expires = datetime.fromisoformat(source["artifact_expires_at"])
        artifact_id = source["artifact_id"]
        status = "source_window_elapsed_using_captured_snapshot"
        if now < expires:
            request = Request(
                f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact_id}",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with urlopen(request, timeout=20) as response:
                artifact = json.load(response)
            run = artifact["workflow_run"]
            require(
                (artifact["id"], artifact["digest"], artifact["created_at"],
                 artifact["expires_at"], artifact["expired"], run["id"], run["head_sha"])
                == (artifact_id, source["artifact_sha256"], source["artifact_created_at"],
                    source["artifact_expires_at"], False, source["run_id"], source["head_sha"]),
                f"Live GitHub metadata mismatch for {sample['sample_id']}",
            )
            status = "live_metadata_matched"
        rows.append({
            "sample_id": sample["sample_id"], "artifact_id": artifact_id,
            "run_id": source["run_id"], "digest": source["artifact_sha256"],
            "expires_at": source["artifact_expires_at"], "source_status": status,
        })
    return {
        "checked_at_utc": now.isoformat(),
        "checkout_sha": os.getenv("GITHUB_SHA"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "event": os.getenv("GITHUB_EVENT_NAME"),
        "samples": rows,
        "archive_reperformance": packet,
        "independent_custody": "pending",
        "closure": "pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = check_retention()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
