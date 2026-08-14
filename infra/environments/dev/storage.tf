data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  data_bucket_name = "opslens-dev-data-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
}

resource "aws_s3_bucket" "data" {
  # checkov:skip=CKV2_AWS_62: Event notifications will be introduced only when a concrete event-driven consumer requires them.
  # checkov:skip=CKV_AWS_18: S3 server access logging is not justified for this low-volume dev data lake; application and AWS audit observability will be introduced incrementally.
  # checkov:skip=CKV_AWS_144: Cross-region replication is not justified for the single-region dev environment.
  # checkov:skip=CKV_AWS_145: SSE-S3 is sufficient for the current public threat-intelligence dataset; no customer-managed KMS key requirement exists.

  bucket        = local.data_bucket_name
  force_destroy = false

  tags = {
    Purpose = "data-lake"
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  depends_on = [
    aws_s3_bucket_versioning.data,
  ]

  rule {
    id     = "cleanup-storage-artifacts"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

output "data_bucket_name" {
  description = "Name of the OpsLens dev data lake bucket."
  value       = aws_s3_bucket.data.id
}
