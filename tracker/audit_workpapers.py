"""Reperform the tracker audit sample and export a synthetic reviewer packet."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from tracker.audit_bundle import REPOSITORY, require, verify_bundle


EVIDENCE = Path(__file__).resolve().parents[1] / "docs" / "portfolio" / "audit-evidence"
REQUESTS = (
    ("ER-01", "S2-01 / ISO-02", "Access owner", "Workspace access and review tests",
     "fulfilled", ("CI",), None),
    ("ER-02", "S2-01 / ISO-02", "Access owner", "Grant, revocation, and periodic access review records",
     "missing", (), "E-01"),
    ("ER-03", "S2-02 / ISO-02", "Release coordinator", "PR traceability, review, and promotion evidence",
     "insufficient", ("CI", "PRs", "inventory"), "E-02"),
    ("ER-04", "S2-03 / ISO-04", "Service operator", "Unhealthy candidate detection and baseline recovery receipts",
     "fulfilled", ("CI",), None),
    ("ER-05", "S2-03 / ISO-04", "Service operator", "Ongoing alert route, acknowledgement, and resolution",
     "missing", (), "E-03"),
    ("ER-06", "ISO-03", "Release coordinator", "Original release archive and negative verifier retest",
     "fulfilled", ("CI", "retention"), "ISO-F01"),
)
FINDINGS = {
    "E-01": {
        "impact": "A former contributor or reviewer could retain access if revocation is omitted.",
        "root_cause": "Probable design limitation. Demo credentials lack a documented lifecycle.",
        "owner": "Access owner",
        "corrective_action": "Document issuance, revocation, and periodic review and collect the resulting records.",
        "retest": "Pending. Verify an approved grant, a denied revoked credential, and a dated access review.",
    },
    "E-02": {
        "impact": "A technical green gate alone cannot establish independent authorization to promote.",
        "root_cause": "Observed lab scope stops at technical eligibility. A formal promotion record was absent.",
        "owner": "Release coordinator",
        "corrective_action": "Retain the approval and promotion receipt tied to the reviewed revision.",
        "retest": "Pending. Reconcile an actual lab promotion to its review and approved revision.",
    },
    "E-03": {
        "impact": "A tracker failure outside CI may go unnoticed.",
        "root_cause": "Probable design limitation. The observed monitoring path is tied to CI startup and smoke tests.",
        "owner": "Service operator",
        "corrective_action": "Exercise an alert route with an owner, acknowledgement, and recovery record.",
        "retest": "Pending. Follow a timestamped lab alert through acknowledgement and resolution.",
    },
    "ISO-F01": {
        "impact": "A reviewer could rely on altered or unreproducible release evidence.",
        "root_cause": "Preparer inference. Initial release procedure omitted archived evidence verification.",
        "owner": "Release coordinator",
        "corrective_action": "Retain the original archive and reperform the decisions with the digest-bound verifier.",
        "retest": "Passed in the lab. Original archives reperform and a deliberately altered copy is rejected.",
    },
}


def verify_samples(evidence, population):
    start = datetime.fromisoformat(population["period"]["start"])
    end = datetime.fromisoformat(population["period"]["end"])
    require(start.utcoffset() is not None and end.utcoffset() is not None and start < end,
            "Invalid observation window")
    samples = population["samples"]
    require(1 <= len(samples) <= 3, "Expected one to three tracker rehearsal samples")
    ids, runs, artifacts = set(), set(), set()
    observations = []
    for sample in samples:
        source = sample["source"]
        sample_id, run, artifact = sample["sample_id"], source["run_id"], source["artifact_id"]
        require(sample_id not in ids and run not in runs and artifact not in artifacts, "Duplicate sample evidence")
        ids.add(sample_id)
        runs.add(run)
        artifacts.add(artifact)
        created = datetime.fromisoformat(sample["run_created_at"])
        retained = datetime.fromisoformat(source["artifact_created_at"])
        require(start <= created <= retained < end, "Sample outside observation window")
        require(sample["run_event"] == "pull_request" and sample["run_conclusion"] == "success",
                "Expected a completed PR rehearsal")
        filename = sample["artifact"]
        require(Path(filename).name == filename and filename.endswith(".zip"), "Invalid local archive name")
        report = verify_bundle(evidence / filename, source)
        required_checks = {"authentication", "role isolation", "digest binding", "audit export"}
        require(required_checks <= set(report["baseline_checks_reported"]), "Access evidence incomplete")
        observations.append({"sample_id": sample_id, "run_created_at": sample["run_created_at"],
                             "run_attempt": sample["run_attempt"], "archive": filename,
                             "run_url": f"https://github.com/{source['repository']}/actions/runs/{run}",
                             "artifact_url": f"https://github.com/{source['repository']}/actions/runs/{run}/artifacts/{artifact}",
                             "observation": report})
    return observations


def build_packet(evidence=EVIDENCE):
    population = json.loads((evidence / "tracker-audit-population.json").read_bytes())
    require(not any(population[key] for key in ("observed_release_ids", "observed_deployment_ids", "observed_git_tags"))
            and not any(population["observed_pr_reviews"].values()),
            "Promotion or review history changed and needs new workpaper conclusions")
    samples = verify_samples(evidence, population)

    # Reuse the same verifier in the ISO negative retest, keeping the historical files intact.
    first = samples[0]
    with TemporaryDirectory(prefix="tracker-audit-") as directory:
        altered = Path(directory) / "altered.zip"
        altered.write_bytes((evidence / first["archive"]).read_bytes() + b"exercise alteration")
        try:
            verify_bundle(altered, first["observation"]["source"])
        except ValueError as error:
            require(str(error) == "Artifact digest mismatch", "Unexpected negative retest result")
        else:
            raise ValueError("Altered audit evidence was accepted")

    sources = {
        "CI": [sample["sample_id"] for sample in samples],
        "PRs": [f"https://github.com/{REPOSITORY}/pull/{pr}"
                for pr in sorted({sample['observation']['source']['pull_request'] for sample in samples})],
        "inventory": [population[key] for key in ("release_inventory_url", "deployment_inventory_url", "tag_inventory_url")],
        "retention": ["ISO-F01 retest"],
    }
    requests = [
        {"id": key, "workpaper": reference, "requested_evidence": description, "status": status,
         "period": population["period"], "owner": owner, "exercise_due_date": "2026-11-27",
         "sources": [item for source in evidence_types for item in sources[source]], "finding": finding}
        for key, reference, owner, description, status, evidence_types, finding in REQUESTS
    ]
    workpapers = [
        {"sample_id": sample["sample_id"], "source": sample["artifact_url"], "requests": {
            "ER-01": "Technical access checks verified",
            "ER-03": "Technical gates verified. Release authorization absent.",
            "ER-04": "Unhealthy candidate blocked. Recovery preserved the baseline as reported.",
            "ER-06": "Original archive and decisions verified",
        }, "related_exceptions": ["E-01", "E-02", "E-03"], "records_finding": "ISO-F01"}
        for sample in samples
    ]
    return {
        "scope": "Synthetic tracker readiness and internal-audit exercises",
        "period": population["period"],
        "population": {"ci_rehearsals": len(samples), "tagged_releases": 0, "deployments": 0,
                       "formal_reviews_on_sampled_prs": 0},
        "samples": samples, "evidence_requests": requests, "sample_workpapers": workpapers,
        "findings": {key: {**value, "closure": "pending"} for key, value in FINDINGS.items()},
        "reviewer_disposition": {"reviewer": None, "independence_confirmed": None, "date": None,
                                 "decision": "pending", "owner_acceptance": "pending"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        packet = build_packet()
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(packet, stream, indent=2)
            stream.write("\n")
    except (OSError, BadZipFile, TypeError, KeyError, ValueError) as error:
        parser.exit(1, f"Audit packet failed: {error}\n")


if __name__ == "__main__":
    main()
