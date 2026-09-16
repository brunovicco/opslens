# The request path and the projection build are two workloads with two legitimate scan
# budgets, and one number cannot serve both.
#
# `opslens-dev` exists to bound what an anonymous caller can spend. Its cutoff is
# 10 MiB, which is Athena's own minimum rather than a chosen value, and that is
# correct for anything reachable from a request.
#
# Building the correlation projection is the opposite workload by design: it scans the
# whole corpus once per schedule, because a projection keyed by package cannot be built
# from a subset. Measured on 2026-09-16, the Silver tables it reads hold 738.5 MiB of
# GHSA and 62.6 MiB of NVD, so a full column scan stays under 800 MiB. At Athena's
# per-terabyte rate that is under a cent per run.
#
#     request budget != projection budget
#
# So this is a second bounded workgroup, not a relaxation of the first. 2 GiB leaves
# headroom for corpus growth and remains a hard ceiling that a runaway query hits.
# Nothing reachable from the public request path may use it.
resource "aws_athena_workgroup" "opslens_projection" {
  name = "opslens-dev-projection"

  description = "OpsLens projection workgroup, bounded above the request path by design."

  state         = "ENABLED"
  force_destroy = false

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    requester_pays_enabled             = false

    bytes_scanned_cutoff_per_query = 2147483648

    engine_version {
      selected_engine_version = "AUTO"
    }

    result_configuration {
      output_location = (
        "s3://${aws_s3_bucket.data.id}/athena-results-projection/"
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
    Purpose = "projection-analytics"
  }
}

output "projection_workgroup_name" {
  description = "Name of the bounded workgroup used to build projections and take measurements."
  value       = aws_athena_workgroup.opslens_projection.name
}
