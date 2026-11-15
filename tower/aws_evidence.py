"""Read-only configuration snapshots; no content reads or AWS mutations."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

def collect(session, expected_account, region, table, bucket):
    from botocore.config import Config
    sdk = Config(connect_timeout=5, read_timeout=20, retries={"total_max_attempts": 1})
    identity = session.client("sts", region_name=region, config=sdk).get_caller_identity()
    if identity["Account"] != expected_account: raise ValueError("Wrong AWS account")
    ddb = session.client("dynamodb", region_name=region, config=sdk)
    s3 = session.client("s3", region_name=region, config=sdk)
    response = ddb.describe_table(TableName=table)["Table"]
    if not response["TableArn"].startswith(f"arn:aws:dynamodb:{region}:{expected_account}:table/"):
        raise ValueError("DynamoDB resource boundary mismatch")
    result = {"schema_version":1, "mode":"live_read_only", "collected_at":datetime.now(timezone.utc).isoformat(),
              "expected_account":expected_account, "region":region,
              "table":{"arn":response["TableArn"], "status":response["TableStatus"], "sse":response.get("SSEDescription")},
              "bucket":bucket, "observations":{}}
    for name, method in (("public_access_block","get_public_access_block"),("encryption","get_bucket_encryption"),
                         ("versioning","get_bucket_versioning"),("logging","get_bucket_logging"),
                         ("location","get_bucket_location")):
        try:
            value = getattr(s3,method)(Bucket=bucket, ExpectedBucketOwner=expected_account)
            value.pop("ResponseMetadata",None)
            result["observations"][name]={"status":"collected","value":value}
        except Exception as exc:
            # Missing policy/access-denied is evidence of an unverified observation.
            result["observations"][name]={"status":"unverified","error_type":type(exc).__name__}
    result["assessment"]="Configuration observations only; no compliance conclusion"
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("expected-account","region","table","bucket","output"): p.add_argument("--"+name,required=True)
    p.add_argument("--profile")
    a=p.parse_args()
    import boto3
    result=collect(boto3.Session(profile_name=a.profile),a.expected_account,a.region,a.table,a.bucket)
    Path(a.output).write_text(json.dumps(result,indent=2,default=str)+"\n",encoding="utf-8")

if __name__=="__main__": main()
