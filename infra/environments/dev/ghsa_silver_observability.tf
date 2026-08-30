resource "aws_cloudwatch_log_group" "ghsa_silver" {
  # checkov:skip=CKV_AWS_158: CloudWatch Logs encryption at rest is sufficient for this dev workload containing public GHSA data.
  # checkov:skip=CKV_AWS_338: A 14-day retention period is intentional for the low-volume dev environment.

  name              = local.ghsa_silver_lambda_log_group_name
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "ghsa-silver-observability"
  }
}
