mock_provider "aws" {}
mock_provider "aws" {
  alias = "archive"
}
mock_provider "aws" {
  alias = "security"
}

variables {
  region                      = "us-east-1"
  management_account_id       = "111111111111"
  log_archive_account_id      = "222222222222"
  security_account_id         = "333333333333"
  workload_ou_id              = "ou-abcd-12345678"
  organization_id             = "o-abcdefghij"
  archive_bucket_name         = "portfolio-fixture-security-logs"
  management_profile          = "fixture-management"
  archive_profile             = "fixture-archive"
  security_profile            = "fixture-security"
  config_aggregation_role_arn = "arn:aws:iam::333333333333:role/fixture-config-aggregation"
}

run "plan_organization_guardrails" {
  command = plan

  assert {
    condition     = aws_cloudtrail.organization.is_organization_trail && aws_cloudtrail.organization.is_multi_region_trail && aws_cloudtrail.organization.enable_log_file_validation
    error_message = "Expected a multiregion organization trail with log file validation."
  }

  assert {
    condition     = aws_organizations_policy_attachment.workload.target_id == var.workload_ou_id
    error_message = "The audit policy must attach to the workload OU."
  }

  assert {
    condition     = aws_s3_bucket_public_access_block.archive.block_public_policy && aws_s3_bucket_versioning.archive.versioning_configuration[0].status == "Enabled"
    error_message = "The archive must block public policies and keep object versions."
  }

  assert {
    condition     = aws_config_configuration_aggregator.organization.organization_aggregation_source[0].all_regions
    error_message = "AWS Config aggregation must cover all regions."
  }
}

run "reject_reused_account" {
  command = plan

  variables {
    security_account_id = "222222222222"
  }

  expect_failures = [aws_s3_bucket.archive]
}
