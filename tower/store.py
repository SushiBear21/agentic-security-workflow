"""One versioned program document; bounded portfolio scale, fail-closed CAS."""
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from tower.core import empty, transition, event, verify


def encode(state):
    raw = json.dumps(state, allow_nan=False, separators=(",", ":"))
    if len(raw.encode()) > 300_000:
        raise ValueError("Program reached 300 KB portfolio limit; export and archive before extending")
    return raw


def apply(state, command, args, actor, now=None):
    now = time.time() if now is None else now
    verify(state)
    try:
        updated, result = transition(state, command, args, actor, now)
        error = None
    except (ValueError, KeyError, TypeError) as exc:
        updated, result, error = state, None, str(exc)
        event(updated, "denied", actor, {"command": command, "error": error}, now)
    updated["attempts"].append({"command": command, "at": now, "success": error is None})
    return updated, result, error


class LocalStore:
    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        try:
            with db:
                yield db
        finally:
            db.close()

    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS program (id INTEGER PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO program VALUES (1, ?)", (encode(empty()),))

    def read(self):
        with self.connect() as db:
            state = json.loads(db.execute("SELECT body FROM program WHERE id=1").fetchone()[0])
        verify(state)
        return state

    def run(self, command, args, actor, now=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = json.loads(db.execute("SELECT body FROM program WHERE id=1").fetchone()[0])
            state, result, error = apply(state, command, args, actor, now)
            db.execute("UPDATE program SET body=? WHERE id=1", (encode(state),))
        if error:
            raise ValueError(error)
        return result


class DynamoStore:
    def __init__(self, client, table):
        self.client, self.table = client, table

    def load(self):
        item = self.client.get_item(TableName=self.table, Key={"pk": {"S": "PROGRAM"}}, ConsistentRead=True).get("Item")
        if not item:
            return empty(), None
        state = json.loads(item["body"]["S"])
        verify(state)
        return state, int(item["version"]["N"])

    def read(self):
        return self.load()[0]

    def run(self, command, args, actor, now=None):
        state, version = self.load()
        state, result, error = apply(state, command, args, actor, now)
        request = {"TableName": self.table,
                   "Item": {"pk": {"S": "PROGRAM"}, "version": {"N": str(0 if version is None else version + 1)}, "body": {"S": encode(state)}}}
        if version is None:
            request["ConditionExpression"] = "attribute_not_exists(pk)"
        else:
            request.update(ConditionExpression="#v = :v", ExpressionAttributeNames={"#v": "version"}, ExpressionAttributeValues={":v": {"N": str(version)}})
        # No retry after conflict/transport error. Inspect state before deciding to retry.
        self.client.put_item(**request)
        if error:
            raise ValueError(error)
        return result
