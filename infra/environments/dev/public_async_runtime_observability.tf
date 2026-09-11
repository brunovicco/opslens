resource "aws_cloudwatch_log_group" "public_async_api" {
  count = local.public_async_runtime_count

  # checkov:skip=CKV_AWS_158: CloudWatch Logs service encryption is sufficient for the disabled dev control path; no sensitive payload logging is admitted.
  # checkov:skip=CKV_AWS_338: Fourteen-day retention is the intentional bounded dev troubleshooting window.

  name              = local.public_async_api_log_group_name
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "public-analysis-api-observability"
    Gate    = "19.4"
  }
}

resource "aws_cloudwatch_log_group" "public_async_worker" {
  count = local.public_async_runtime_count

  # checkov:skip=CKV_AWS_158: CloudWatch Logs service encryption is sufficient for the disabled dev worker; content-minimized telemetry contains no repository contents or prompts.
  # checkov:skip=CKV_AWS_338: Fourteen-day retention is the intentional bounded dev troubleshooting window.

  name              = local.public_async_worker_log_group_name
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "public-analysis-worker-observability"
    Gate    = "19.4"
  }
}

resource "aws_cloudwatch_log_group" "public_async_access" {
  count = local.public_async_runtime_count

  # checkov:skip=CKV_AWS_158: CloudWatch Logs service encryption is sufficient for bounded API transport metadata in the disabled dev topology.
  # checkov:skip=CKV_AWS_338: Fourteen-day retention is the intentional bounded dev troubleshooting window.

  name              = local.public_async_access_log_group_name
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "public-analysis-api-access-observability"
    Gate    = "19.4"
  }
}
