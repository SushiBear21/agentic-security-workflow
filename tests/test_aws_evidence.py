import unittest
from unittest.mock import Mock
from tower.aws_evidence import collect
class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.session=Mock(); self.sts=Mock(); self.ddb=Mock(); self.s3=Mock()
        self.session.client.side_effect=lambda name,**kwargs:{"sts":self.sts,"dynamodb":self.ddb,"s3":self.s3}[name]
        self.sts.get_caller_identity.return_value={"Account":"123456789012"}
        self.ddb.describe_table.return_value={"Table":{"TableArn":"arn:aws:dynamodb:us-east-1:123456789012:table/lab","TableStatus":"ACTIVE"}}
        for method in ("get_public_access_block","get_bucket_encryption","get_bucket_versioning","get_bucket_logging","get_bucket_location"):
            getattr(self.s3,method).return_value={}
    def test_read_only_scope_and_unknown(self):
        self.s3.get_bucket_logging.side_effect=PermissionError()
        r=collect(self.session,"123456789012","us-east-1","lab","bucket")
        self.assertEqual(r["observations"]["logging"]["status"],"unverified")
        self.assertEqual(self.s3.get_bucket_encryption.call_args.kwargs["ExpectedBucketOwner"],"123456789012")
        self.assertEqual({call[0] for call in self.ddb.mock_calls},{"describe_table"})
    def test_wrong_account_stops_before_collection(self):
        with self.assertRaises(ValueError): collect(self.session,"000000000000","us-east-1","lab","bucket")
        self.ddb.describe_table.assert_not_called()

    def test_wrong_table_stops_before_bucket_collection(self):
        self.ddb.describe_table.return_value["Table"]["TableArn"] += "-other"
        with self.assertRaisesRegex(ValueError, "DynamoDB resource boundary"):
            collect(self.session, "123456789012", "us-east-1", "lab", "bucket")
        self.s3.get_bucket_location.assert_not_called()

    def test_wrong_bucket_region_stops_before_configuration_reads(self):
        self.s3.get_bucket_location.return_value = {"LocationConstraint": "us-west-2"}
        with self.assertRaisesRegex(ValueError, "S3 bucket region boundary"):
            collect(self.session, "123456789012", "us-east-1", "lab", "bucket")
        self.s3.get_bucket_location.assert_called_once_with(
            Bucket="bucket", ExpectedBucketOwner="123456789012"
        )
        self.s3.get_bucket_encryption.assert_not_called()

    def test_sdk_requests_are_read_only_and_scoped(self):
        import boto3
        from contextlib import ExitStack
        from botocore.stub import Stubber

        account = "123456789012"
        region = "us-east-1"
        arn = f"arn:aws:dynamodb:{region}:{account}:table/lab"
        sdk = boto3.Session(
            aws_access_key_id="fixture", aws_secret_access_key="fixture", region_name=region
        )
        clients = {service: sdk.client(service) for service in ("sts", "dynamodb", "s3")}
        stubs = {service: Stubber(client) for service, client in clients.items()}
        self.session.client.side_effect = lambda service, **kwargs: clients[service]

        stubs["sts"].add_response("get_caller_identity", {
            "Account": account, "UserId": "synthetic", "Arn": f"arn:aws:iam::{account}:user/fixture",
        }, {})
        stubs["dynamodb"].add_response("describe_table", {
            "Table": {"TableArn": arn, "TableStatus": "ACTIVE", "SSEDescription": {"Status": "ENABLED"}},
        }, {"TableName": "lab"})
        scoped = {"Bucket": "bucket", "ExpectedBucketOwner": account}
        s3 = stubs["s3"]
        s3.add_response("get_bucket_location", {}, scoped)
        s3.add_response("get_public_access_block", {
            "PublicAccessBlockConfiguration": {"BlockPublicAcls": True},
        }, scoped)
        s3.add_response("get_bucket_encryption", {
            "ServerSideEncryptionConfiguration": {"Rules": [
                {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}},
            ]},
        }, scoped)
        s3.add_response("get_bucket_versioning", {"Status": "Enabled"}, scoped)
        s3.add_client_error("get_bucket_logging", "AccessDenied", http_status_code=403, expected_params=scoped)
        with ExitStack() as stack:
            for stub in stubs.values():
                stack.enter_context(stub)
            snapshot = collect(self.session, account, region, "lab", "bucket")
            for stub in stubs.values():
                stub.assert_no_pending_responses()

        self.assertEqual(snapshot["observations"]["table_encryption"]["status"], "collected")
        self.assertEqual(snapshot["observations"]["logging"]["status"], "unverified")
