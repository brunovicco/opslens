locals {
  deployment_artifacts_bucket_name = "opslens-dev-artifacts-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
}

resource "aws_s3_bucket" "deployment_artifacts" {
  # checkov:skip=CKV2_AWS_62: Deployment artifacts do not require event notifications.
  # checkov:skip=CKV_AWS_18: Server access logging is not justified for this low-volume dev deployment bucket.
  # checkov:skip=CKV_AWS_144: Cross-region replication is not justified for the single-region dev environment.
  # checkov:skip=CKV_AWS_145: SSE-S3 is sufficient for deployment packages; no customer-managed KMS requirement exists.

  bucket        = local.deployment_artifacts_bucket_name
  force_destroy = false

  tags = {
    Purpose = "deployment-artifacts"
  }
}

resource "aws_s3_bucket_versioning" "deployment_artifacts" {
  bucket = aws_s3_bucket.deployment_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "deployment_artifacts" {
  bucket = aws_s3_bucket.deployment_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "deployment_artifacts" {
  bucket = aws_s3_bucket.deployment_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "deployment_artifacts" {
  bucket = aws_s3_bucket.deployment_artifacts.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "deployment_artifacts" {
  bucket = aws_s3_bucket.deployment_artifacts.id

  depends_on = [
    aws_s3_bucket_versioning.deployment_artifacts,
  ]

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "cleanup-lambda-deployment-artifacts"
    status = "Enabled"

    filter {
      prefix = "lambda/"
    }

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

output "deployment_artifacts_bucket_name" {
  description = "Name of the OpsLens dev Lambda deployment artifacts bucket."
  value       = aws_s3_bucket.deployment_artifacts.id
}
