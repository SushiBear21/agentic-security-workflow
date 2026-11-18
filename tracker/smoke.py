"""Exercise the tracker over HTTP and emit a machine-readable smoke result."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from tracker.store import load_principals
from tower.core import verify


def exercise(url, accounts, baseline=None):
    tokens = {principal.role: token for token, principal in accounts.items()}

    def request(path, role=None, body=None, expected=200):
        headers = {}
        if role:
            headers["Authorization"] = f"Bearer {tokens[role]}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(url + path, headers=headers, data=None if body is None else json.dumps(body).encode())
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise AssertionError(f"{path}: expected {expected}, got {response.status}")
            return json.load(response)

    if request("/health")["status"] != "ok":
        raise AssertionError("Health check failed")
    request("/api/evidence", expected=401)
    evidence = {"id": str(uuid4()), "title": "Synthetic evidence", "note": "Exercise record"}
    item = request("/api/evidence", "contributor", evidence)
    repeated = request("/api/evidence", "contributor", evidence)
    if item != repeated or item["status"] != "pending":
        raise AssertionError("Submission replay changed the record")
    review = {"id": item["id"], "sha256": item["sha256"], "decision": "approve",
              "reason": "Synthetic evidence inspected by reviewer"}
    request("/api/review", "contributor", review, expected=403)
    request("/api/export", "contributor", expected=403)
    request("/api/review", "reviewer", {**review, "sha256": "0" * 64}, expected=400)
    approved = request("/api/review", "reviewer", review)
    if approved["status"] != "approved":
        raise AssertionError("Review did not take effect")
    request("/api/review", "reviewer", {**review, "decision": "reject"}, expected=400)
    history = request("/api/export", "reviewer")
    verify({"events": history["events"], "proposals": {}})
    if not any(row == approved for row in history["records"]) or history["events"][-1]["kind"] != "exported":
        raise AssertionError("Export missing reviewed record or audit event")
    if baseline is not None and not any(
        row["id"] == baseline["record_id"] and row["sha256"] == baseline["record_sha256"]
        and row["status"] == "approved" for row in history["records"]
    ):
        raise AssertionError("The approved baseline record did not survive recovery")
    return {"passed": True, "record_id": item["id"], "record_sha256": item["sha256"],
            "preserved_baseline": True if baseline is not None else None, "checks": ["health", "authentication", "submit", "idempotent replay",
                                       "role isolation", "digest binding", "review",
                                       "one decision", "audit export"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8090")
    parser.add_argument("--credentials", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, help="Prior smoke receipt for a recovery test")
    args = parser.parse_args()
    try:
        baseline = json.loads(args.baseline.read_bytes()) if args.baseline else None
        result = exercise(args.url, load_principals(args.credentials), baseline)
    except (URLError, AssertionError, TimeoutError) as error:
        result = {"passed": False, "failure": type(error).__name__}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
