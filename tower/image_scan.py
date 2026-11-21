"""Validate a fresh Trivy report against the image inspected by the CI job."""
import json
import re
from datetime import datetime, timedelta, timezone

DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
MAX_AGE = timedelta(hours=24)


def evaluate(raw, image_id, now, *, require_language=True):
    try:
        report = json.loads(raw)
        scanned_at = datetime.fromisoformat(report["CreatedAt"])
        results = report["Results"]
        if not DIGEST.fullmatch(image_id) or report["Metadata"]["ImageID"] != image_id:
            raise ValueError("Scan image ID does not match the inspected image")
        if report["ArtifactType"] != "container_image":
            raise ValueError("A container image report is required")
        age = now - scanned_at.astimezone(timezone.utc)
        if scanned_at.utcoffset() is None or not timedelta(0) <= age <= MAX_AGE:
            raise ValueError("Scan timestamp is outside the accepted window")
        if not isinstance(results, list) or not any(row["Class"] == "os-pkgs" for row in results):
            raise ValueError("OS package coverage is required")
        if require_language and not any(row["Class"] == "lang-pkgs" for row in results):
            raise ValueError("Language package coverage is required")
        findings = [
            item for row in results for item in row.get("Vulnerabilities", [])
            if item["Severity"] in {"HIGH", "CRITICAL"}
        ]
        return {"status": "fail" if findings else "pass", "image_id": image_id,
                "scanned_at": scanned_at.isoformat(), "blocking_findings": len(findings)}
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        return {"status": "fail", "image_id": image_id, "reason": str(error)}
