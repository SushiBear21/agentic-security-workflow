"""Exercise tracker access, lab promotion, and incident response on loopback."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
from queue import Queue
from secrets import token_hex
from subprocess import check_output
from tempfile import TemporaryDirectory
from threading import Thread

from tracker.audit_bundle import require
from tracker.server import Handler
from tracker.smoke import exercise
from tracker.store import Tracker, load_principals


class LabHandler(Handler):
    def log_message(self, format, *args):
        pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def serve(db_path, principals, port=0):
    handler = partial(LabHandler, tracker=Tracker(db_path), accounts=principals)
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        worker.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            worker.join()


def get(port, path, token=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def record_access(port, token, expected, sample_id, records):
    status, session = get(port, "/api/session", token)
    require(status == expected, f"{sample_id}: expected HTTP {expected}, got {status}")
    records.append({"id": sample_id, "at": utc_now(), "http_status": status,
                    "session": session if status == 200 else None})


def promotion_allowed(candidate, approval):
    return (
        candidate["smoke_passed"] is True
        and approval is not None
        and approval["decision"] == "approve"
        and approval["candidate"] == candidate
        and approval["actor"] != candidate["prepared_by"]
    )


def run_lab(directory, revision):
    db = directory / "tracker.db"
    credentials = directory / "credentials.json"
    contributor = {"workspace": "Trackerauditlab", "name": "LabContributor",
                   "role": "contributor", "token": token_hex(32)}
    reviewer = {"workspace": contributor["workspace"], "name": "LabEvidenceReviewer",
                "role": "reviewer", "token": token_hex(32)}
    access = {"request": "ER-02", "finding": "E-01", "sample_population": 1,
              "grant": {"actor": "Simulated Access Owner", "at": utc_now(),
                        "decision": "approved", "principal": contributor["name"],
                        "workspace": contributor["workspace"], "role": contributor["role"]},
              "sessions": []}

    credentials.write_text(json.dumps([reviewer]), encoding="utf-8")
    with serve(db, load_principals(credentials)) as port:
        record_access(port, contributor["token"], 401, "LC-01-PRE-GRANT", access["sessions"])

    credentials.write_text(json.dumps([reviewer, contributor]), encoding="utf-8")
    granted = load_principals(credentials)
    with serve(db, granted) as port:
        record_access(port, contributor["token"], 200, "LC-01-GRANTED", access["sessions"])
        session = access["sessions"][-1]["session"]
        require(session == {key: contributor[key] for key in ("name", "role", "workspace")},
                "Granted session has the wrong identity or role")
        baseline = exercise(f"http://127.0.0.1:{port}", granted)

    access["revocation"] = {"actor": "Simulated Access Owner", "at": utc_now(),
                            "principal": contributor["name"], "action": "remove and restart"}
    replacement = {**contributor, "name": "LabReplacement", "token": token_hex(32)}
    credentials.write_text(json.dumps([reviewer, replacement]), encoding="utf-8")
    active = load_principals(credentials)
    with serve(db, active) as port:
        record_access(port, contributor["token"], 401, "LC-01-REVOKED", access["sessions"])
        record_access(port, reviewer["token"], 200, "LC-01-REVIEWER-CONTROL", access["sessions"])
        inventory = sorted((vars(principal) for principal in active.values()), key=lambda row: row["role"])
        expected = {(reviewer["name"], "reviewer"), (replacement["name"], "contributor")}
        require({(row["name"], row["role"]) for row in inventory} == expected
                and all(row["workspace"] == contributor["workspace"] for row in inventory),
                "Access review did not reconcile the active inventory")
        access["review"] = {"at": utc_now(), "actor": "Simulated Access Inventory Reviewer",
                            "inventory": inventory, "result": "pass"}
        staged = exercise(f"http://127.0.0.1:{port}", active, baseline)

    source_paths = ("server.py", "store.py", "index.html", "tracker.css", "tracker.js")
    source_hashes = {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                     for name in source_paths}
    candidate = {"sample": "PRM-01", "revision": revision, "source_sha256": source_hashes,
                 "target": "localhost demo slot", "prepared_by": "Simulated Release Coordinator",
                 "smoke_passed": staged["passed"], "staged_record_sha256": staged["record_sha256"]}
    approval = {"actor": "Simulated Release Approver", "decision": "approve", "at": utc_now(),
                "candidate": candidate, "scope": "fixture approval for local lab promotion"}
    wrong_approval = {**approval, "candidate": {**candidate, "revision": "0" * 40}}
    missing_allowed = promotion_allowed(candidate, None)
    wrong_allowed = promotion_allowed(candidate, wrong_approval)
    same_actor_allowed = promotion_allowed(candidate, {**approval, "actor": candidate["prepared_by"]})
    require(not any((missing_allowed, wrong_allowed, same_actor_allowed)),
            "Invalid approval authorized lab promotion")
    require(promotion_allowed(candidate, approval), "Matching fixture approval failed")

    events = []
    with serve(db, active) as port:
        deployed = utc_now()
        url = f"http://127.0.0.1:{port}"
        promoted = exercise(url, active, staged)
        status, health = get(port, "/health")
        require(status == 200 and health["status"] == "ok", "Initial monitoring probe failed")
        events.append({"kind": "healthy", "at": utc_now(), "http_status": status})

    events.append({"kind": "incident_injected", "at": utc_now(), "action": "stop loopback listener"})
    try:
        get(port, "/health")
    except (ConnectionRefusedError, TimeoutError) as error:
        events.append({"kind": "detected", "at": utc_now(), "probe": "GET /health",
                       "error": type(error).__name__})
    else:
        raise ValueError("Monitoring probe missed the stopped listener")

    notifications = Queue()
    owner = "Simulated Tracker Service Operator"
    message = {"incident": "INC-01", "destination": owner, "reason": "health probe could not connect"}
    notifications.put(message)
    events.append({"kind": "routed", "at": utc_now(), **message})
    received = notifications.get_nowait()
    require(received == message, "Operator did not receive the injected alert")
    events.append({"kind": "acknowledged", "at": utc_now(), "incident": received["incident"],
                   "actor": received["destination"]})
    with serve(db, active, port) as recovered_port:
        require(recovered_port == port, "Recovery used a different monitoring endpoint")
        status, health = get(recovered_port, "/health")
        require(status == 200 and health["status"] == "ok", "Health probe did not recover")
        events.append({"kind": "recovered", "at": utc_now(), "http_status": status})
        recovery = exercise(url, active, promoted)
        events.append({"kind": "resolved", "at": utc_now(), "actor": owner,
                       "preserved_promoted_record": recovery["preserved_baseline"]})

    return {
        "classification": "Verified loopback lab execution with fictional data, simulated roles and alert routing",
        "revision": revision,
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "population": {"credential_lifecycles": 1, "promotion_candidates": 1, "injected_incidents": 1},
        "access": access,
        "promotion": {"request": "ER-03", "finding": "E-02",
                      "gate_results": {"missing_approval": "blocked", "wrong_revision": "blocked",
                                       "same_actor": "blocked", "matching_fixture_approval": "pass"},
                      "approval": approval, "started_at": deployed, "http_status": 200,
                      "baseline_smoke": baseline, "candidate_smoke": staged, "promoted_smoke": promoted},
        "monitoring": {"request": "ER-05", "finding": "E-03", "route": "local in-process test queue",
                       "incident": "INC-01", "events": events, "recovery_smoke": recovery},
        "reviewer_disposition": "pending",
        "owner_closure": "pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    revision = check_output(["git", "rev-parse", "--verify", "HEAD"], cwd=root, text=True).strip()
    ci_revision = os.getenv("GITHUB_SHA")
    require(not ci_revision or revision == ci_revision, "Git HEAD differs from the CI checkout SHA")
    changes = check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True)
    require(not changes, "Tracked worktree changes would make the evidence revision ambiguous")
    with TemporaryDirectory(prefix="tracker-operating-evidence-") as directory:
        report = run_lab(Path(directory), revision)
    payload = (json.dumps(report, indent=2) + "\n").encode()
    with args.output.open("xb") as stream:
        stream.write(payload)
    access_codes = [row["http_status"] for row in report["access"]["sessions"]]
    events = [f"{row['kind']}@{row['at']}" for row in report["monitoring"]["events"]]
    print(f"E-01 session statuses {access_codes}; access review passed at {report['access']['review']['at']}")
    print("E-02 missing, wrong-revision and same-actor approvals blocked; "
          "matching fixture approval allowed localhost promotion; smoke and preservation passed")
    print(f"E-02 localhost slot started at {report['promotion']['started_at']}")
    detected = next(row for row in report["monitoring"]["events"] if row["kind"] == "detected")
    print(f"Health probe failure: {detected['error']}")
    print(f"E-03 {', '.join(events)}; recovery smoke and preservation passed")
    print(f"Checkout {report['revision']}; report SHA-256 {sha256(payload).hexdigest()}")


if __name__ == "__main__":
    main()
