data "aws_caller_identity" "current" {}

locals {
  state_bucket_name = "opslens-dev-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}

resource "aws_s3_bucket" "terraform_state" {
  # checkov:skip=CKV2_AWS_62: Terraform state changes do not require event-driven notifications; no consumer exists for these events.
  # checkov:skip=CKV_AWS_18: Server access logging would require additional logging infrastructure; access auditing will be evaluated when a concrete audit requirement is introduced.
  # checkov:skip=CKV_AWS_144: Cross-region replication is not required for the single-region dev environment; S3 Versioning is the current recovery control.
  # checkov:skip=CKV_AWS_145: SSE-S3 is the accepted Phase 0 encryption decision; there is no current customer-managed KMS key requirement.

  bucket = local.state_bucket_name

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Purpose = "terraform-state"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  depends_on = [
    aws_s3_bucket_versioning.terraform_state,
  ]

  rule {
    id     = "expire-old-state-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
