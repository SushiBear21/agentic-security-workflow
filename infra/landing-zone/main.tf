terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "region" { type = string }
variable "management_account_id" { type = string }
variable "log_archive_account_id" { type = string }
variable "security_account_id" { type = string }
variable "workload_ou_id" { type = string }
variable "organization_id" { type = string }
variable "archive_bucket_name" { type = string }
variable "management_profile" { type = string }
variable "archive_profile" { type = string }
variable "security_profile" { type = string }
variable "config_aggregation_role_arn" { type = string }

provider "aws" {
  region              = var.region
  profile             = var.management_profile
  allowed_account_ids = [var.management_account_id]
}

provider "aws" {
  alias               = "archive"
  region              = var.region
  profile             = var.archive_profile
  allowed_account_ids = [var.log_archive_account_id]
}

provider "aws" {
  alias               = "security"
  region              = var.region
  profile             = var.security_profile
  allowed_account_ids = [var.security_account_id]
}

locals {
  trail_name  = "portfolio-organization-audit"
  trail_arn   = "arn:aws:cloudtrail:${var.region}:${var.management_account_id}:trail/${local.trail_name}"
  archive_arn = "arn:aws:s3:::${var.archive_bucket_name}"
}

resource "aws_s3_bucket" "archive" {
  provider = aws.archive
  bucket   = var.archive_bucket_name
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = length(toset([var.management_account_id, var.log_archive_account_id, var.security_account_id])) == 3
      error_message = "Management, security and log archive accounts must be distinct."
    }
  }
}

resource "aws_s3_bucket_public_access_block" "archive" {
  provider                = aws.archive
  bucket                  = aws_s3_bucket.archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "archive" {
  provider = aws.archive
  bucket   = aws_s3_bucket.archive.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "archive" {
  provider = aws.archive
  bucket   = aws_s3_bucket.archive.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "archive" {
  provider = aws.archive
  bucket   = aws_s3_bucket.archive.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "RequireTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [local.archive_arn, "${local.archive_arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "AllowTrailAclCheck"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = local.archive_arn
        Condition = { StringEquals = { "aws:SourceArn" = local.trail_arn } }
      },
      {
        Sid       = "AllowTrailWrite"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = ["${local.archive_arn}/AWSLogs/${var.management_account_id}/*", "${local.archive_arn}/AWSLogs/${var.organization_id}/*"]
        Condition = { StringEquals = {
          "aws:SourceArn" = local.trail_arn
          "s3:x-amz-acl"  = "bucket-owner-full-control"
        } }
      }
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.archive]
}

resource "aws_cloudtrail" "organization" {
  name                          = local.trail_name
  s3_bucket_name                = aws_s3_bucket.archive.id
  is_organization_trail         = true
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_logging                = true
  enable_log_file_validation    = true
  depends_on                    = [aws_s3_bucket_policy.archive, aws_s3_bucket_versioning.archive, aws_s3_bucket_server_side_encryption_configuration.archive]
}

resource "aws_organizations_policy" "workload" {
  name    = "portfolio-protect-workload-audit"
  type    = "SERVICE_CONTROL_POLICY"
  content = file("${path.module}/guardrails.json")
}

resource "aws_organizations_policy_attachment" "workload" {
  policy_id = aws_organizations_policy.workload.id
  target_id = var.workload_ou_id
}

resource "aws_config_configuration_aggregator" "organization" {
  provider = aws.security
  name     = "portfolio-organization-config"
  organization_aggregation_source {
    all_regions = true
    role_arn    = var.config_aggregation_role_arn
  }
}
