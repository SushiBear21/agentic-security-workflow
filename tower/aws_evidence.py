"""Read configuration metadata for an existing, explicitly scoped AWS environment."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

S3_CHECKS = {
    "public_access_block": "get_public_access_block",
    "encryption": "get_bucket_encryption",
    "versioning": "get_bucket_versioning",
    "logging": "get_bucket_logging",
}
OBSERVATION_NAMES = frozenset(S3_CHECKS) | {"location", "table_encryption"}


def collect(session, expected_account, region, table, bucket):
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    sdk = Config(connect_timeout=5, read_timeout=20, retries={"total_max_attempts": 1})
    identity = session.client("sts", region_name=region, config=sdk).get_caller_identity()
    if identity["Account"] != expected_account:
        raise ValueError("Wrong AWS account")
    partition = identity.get("Arn", "arn:aws:").split(":")[1]

    ddb = session.client("dynamodb", region_name=region, config=sdk)
    response = ddb.describe_table(TableName=table)["Table"]
    expected_arn = f"arn:{partition}:dynamodb:{region}:{expected_account}:table/{table}"
    if response["TableArn"] != expected_arn:
        raise ValueError("DynamoDB resource boundary mismatch")

    s3 = session.client("s3", region_name=region, config=sdk)
    bucket_scope = {"Bucket": bucket, "ExpectedBucketOwner": expected_account}
    location = s3.get_bucket_location(**bucket_scope)
    constraint = location.get("LocationConstraint")
    bucket_region = "us-east-1" if constraint is None else constraint
    if bucket_region == "EU":
        bucket_region = "eu-west-1"
    if bucket_region != region:
        raise ValueError("S3 bucket region boundary mismatch")

    sse = response.get("SSEDescription")
    observations = {
        "location": {"status": "collected", "value": {"LocationConstraint": constraint}},
        "table_encryption": {"status": "collected" if sse else "unverified"},
    }
    for name, method in S3_CHECKS.items():
        try:
            value = getattr(s3, method)(**bucket_scope)
        except (ClientError, BotoCoreError, PermissionError) as exc:
            observations[name] = {"status": "unverified", "error_type": type(exc).__name__}
        else:
            observations[name] = {
                "status": "collected",
                "value": {key: item for key, item in value.items() if key != "ResponseMetadata"},
            }

    return {
        "schema_version": 1,
        "mode": "live_read_only",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "expected_account": expected_account,
        "region": region,
        "table": {"arn": response["TableArn"], "status": response["TableStatus"], "sse": sse},
        "bucket": bucket,
        "observations": observations,
        "assessment": "Configuration observations only; no compliance conclusion",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("expected-account", "region", "table", "bucket", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--profile")
    args = parser.parse_args()

    import boto3

    result = collect(
        boto3.Session(profile_name=args.profile), args.expected_account,
        args.region, args.table, args.bucket,
    )
    with Path(args.output).open("x", encoding="utf-8") as output:
        output.write(json.dumps(result, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
