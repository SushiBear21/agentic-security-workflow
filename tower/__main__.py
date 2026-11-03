import argparse
import getpass
import json
import sys
from pathlib import Path
from app.workflow import read_json
from tower.ai import draft
from tower.store import LocalStore, DynamoStore
from tower.report import export, verify_package
from tower.adapters import import_evidence


def main():
    p = argparse.ArgumentParser(description="Synthetic AI Security Program Control Tower")
    p.add_argument("--db", default="tower-data/program.sqlite")
    p.add_argument("--table", help="Opt in to AWS DynamoDB storage")
    p.add_argument("--profile")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--expected-account", help="Required for any AWS operation")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest").add_argument("file")
    bridge = sub.add_parser("import-evidence")
    bridge.add_argument("source", choices=["agentic", "aws-lab"])
    bridge.add_argument("record"); bridge.add_argument("metadata")
    proposal = sub.add_parser("propose"); proposal.add_argument("id"); proposal.add_argument("--model-id")
    for command in ("approve", "reject"):
        decision = sub.add_parser(command); decision.add_argument("id"); decision.add_argument("--effort-seconds", type=float, required=True)
    sub.add_parser("execute").add_argument("id")
    status = sub.add_parser("status"); status.add_argument("id"); status.add_argument("status", choices=["IN_PROGRESS", "BLOCKED", "DONE"]); status.add_argument("--evidence", default="")
    sub.add_parser("inspect")
    out = sub.add_parser("export"); out.add_argument("directory"); out.add_argument("--bucket")
    sub.add_parser("verify").add_argument("package")
    args = p.parse_args()
    if args.command == "verify":
        print(verify_package(args.package)); return
    session = None
    actor = "local:" + getpass.getuser()
    if args.table or getattr(args, "model_id", None) or getattr(args, "bucket", None):
        if not args.expected_account:
            p.error("AWS use requires --expected-account after account/cost approval")
        import boto3
        from botocore.config import Config
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        config = Config(connect_timeout=5, read_timeout=30, retries={"total_max_attempts": 1})
        identity = session.client("sts", config=config).get_caller_identity()
        if identity["Account"] != args.expected_account:
            raise ValueError("Wrong AWS account")
        actor = identity["Arn"]
    store = DynamoStore(session.client("dynamodb", config=config), args.table) if args.table else LocalStore(args.db)
    if args.command == "inspect":
        print(json.dumps(store.read(), indent=2)); return
    if args.command == "export":
        dashboard = export(store.read(), args.directory)
        if args.bucket:
            package = dashboard.parent / "evidence.zip"
            import hashlib
            key = "evidence/" + hashlib.sha256(package.read_bytes()).hexdigest() + ".zip"
            session.client("s3", config=config).put_object(Bucket=args.bucket, Key=key, Body=package.read_bytes(), ServerSideEncryption="AES256", IfNoneMatch="*")
            print("Private evidence uploaded: " + key)
        print(dashboard); return
    data = vars(args).copy()
    if args.command == "import-evidence":
        finding = import_evidence(args.source, read_json(args.record), read_json(args.metadata))
        print(json.dumps(store.run("ingest", {"findings": [finding]}, actor)))
        return
    if args.command == "ingest":
        data = {"findings": read_json(args.file)}
    elif args.command == "propose":
        finding = store.read()["findings"][args.id]
        provider, proposal = draft(finding, session.client("bedrock-runtime", config=config) if args.model_id else None, args.model_id)
        data = {"id": args.id, "provider": provider, "draft": proposal}
    elif args.command in {"approve", "reject"}:
        proposal = store.read()["proposals"][args.id]
        print(json.dumps(proposal["payload"], indent=2))
        phrase = args.command.upper() + " " + proposal["sha256"]
        if input("Type the exact decision to confirm:\n" + phrase + "\n> ") != phrase:
            raise ValueError("Decision not confirmed")
        data = {"id": args.id, "sha256": proposal["sha256"], "effort_seconds": args.effort_seconds}
    print(json.dumps(store.run(args.command, data, actor)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Stopped: {type(exc).__name__}: {exc}. For AWS transport/conflict errors, inspect state before retrying.", file=sys.stderr)
        sys.exit(1)
