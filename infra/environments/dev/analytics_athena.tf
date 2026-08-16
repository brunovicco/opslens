resource "aws_athena_workgroup" "opslens" {
  name        = "opslens-dev"
  description = "OpsLens development workgroup for deterministic structured analytics."

  state         = "ENABLED"
  force_destroy = false

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    requester_pays_enabled             = false

    # Athena/Terraform minimum: 10 MiB.
    # This bounds accidental scans while remaining above the current
    # EPSS Silver Parquet object size.
    bytes_scanned_cutoff_per_query = 10485760

    engine_version {
      selected_engine_version = "AUTO"
    }

    result_configuration {
      output_location = (
        "s3://${aws_s3_bucket.data.id}/athena-results/"
      )

      expected_bucket_owner = (
        data.aws_caller_identity.current.account_id
      )

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = {
    Purpose = "structured-analytics"
  }
}
