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
