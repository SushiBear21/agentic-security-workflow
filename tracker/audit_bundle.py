"""Reperform release checks from a retained tracker CI artifact without executing it."""
import argparse
import hashlib
import json
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from tower.image_scan import evaluate
from tracker.release import ISSUES, decision

LIMIT = 2_000_000
REPOSITORY = "SushiBear21/agentic-security-workflow"
INPUT_FILES = {
    "scan": "tracker-scan.json", "sbom": "tracker-sbom.json", "browser": "browser.json",
    "baseline": "baseline.json", "candidate": "candidate.json", "recovery": "recovery.json",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_bundle(path, source):
    """Check a bundle against metadata obtained separately from GitHub Actions."""
    require(source["repository"] == REPOSITORY, "Unexpected repository")
    reference_time = datetime.fromisoformat(source["artifact_created_at"])
    require(reference_time.utcoffset() is not None, "Artifact timestamp requires a timezone")
    expected = source["artifact_sha256"]
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", expected), "Invalid artifact digest")
    with Path(path).open("rb") as artifact:
        data = artifact.read(LIMIT + 1)
    require(len(data) <= LIMIT, "Artifact exceeds rehearsal size limit")
    require("sha256:" + sha(data) == expected, "Artifact digest mismatch")

    with ZipFile(BytesIO(data)) as archive:
        names = [*INPUT_FILES.values(), "tracker-release.json"]
        require(all(archive.namelist().count(name) == 1 for name in names), "Missing or duplicate evidence file")
        require(all(archive.getinfo(name).file_size <= LIMIT for name in names), "Evidence file too large")
        raw = {key: archive.read(name) for key, name in INPUT_FILES.items()}
        receipt = json.loads(archive.read("tracker-release.json"))

    require(receipt["repository"] == REPOSITORY, "Receipt repository mismatch")
    require(receipt["commit"] == source["checkout_sha"], "Checkout revision mismatch")
    require(receipt["pull_request"] == source["pull_request"], "Pull request mismatch")
    require(receipt["issues"] == ISSUES, "Backlog traceability mismatch")
    require(receipt["inputs_sha256"] == {key: sha(value) for key, value in raw.items()}, "Input digest mismatch")

    observed = {key: json.loads(value) for key, value in raw.items()}
    image = receipt["image_id"]
    scan = evaluate(raw["scan"], image, reference_time, require_language=False)
    require(scan["status"] == "pass" and scan == receipt["scan"], "Historical image scan did not reperform")
    browser = observed["browser"]
    require(browser.get("passed") is True and set(browser.get("checks", [])) == {"submit", "review", "download"},
            "Browser workflow evidence is incomplete")
    require(observed["baseline"].get("passed") is True, "Baseline smoke evidence is missing")
    require(observed["candidate"].get("passed") is False, "Candidate did not fail its smoke test")
    require(observed["recovery"].get("passed") is True and observed["recovery"].get("preserved_baseline") is True,
            "Recovery did not preserve the baseline")
    phases = {stage: decision(scan, observed[stage], observed["sbom"])
              for stage in ("baseline", "candidate", "recovery")}
    require([phase["outcome"] for phase in phases.values()] ==
            ["eligible_for_review", "blocked", "eligible_for_review"], "Unexpected technical decisions")
    require(phases == receipt["phases"] and receipt.get("browser_acceptance") is True
            and receipt.get("rehearsal_passed") is True, "Recorded rehearsal decisions differ")
    require(receipt.get("promotion_authorized") is False, "Unexpected release promotion claim")

    return {
        "scope": "Historical CI release rehearsal using synthetic data",
        "source": source,
        "image_id": image,
        "input_digests_verified": sorted(raw),
        "browser_workflows_verified": browser["checks"],
        "baseline_checks_reported": observed["baseline"]["checks"],
        "phase_outcomes": {name: phase["outcome"] for name, phase in phases.items()},
        "recovery_preserved_baseline_reported": True,
        "historical_scan": scan,
        "promotion_authorized": False,
        "independent_review": "pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify_bundle(args.artifact, json.loads(args.source.read_bytes()))
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
    except (OSError, BadZipFile, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Evidence verification failed: {error}\n")


if __name__ == "__main__":
    main()
